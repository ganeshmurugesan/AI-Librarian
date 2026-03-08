from decimal import Decimal
from datetime import datetime
from typing import TypedDict, Optional, Any
import logging

# Configure logging to mimic CICS DISPLAY/SYSOUT
logger = logging.getLogger(__name__)

class AccountCommArea(TypedDict):
    """Represents the DFHCOMMAREA structure."""
    sort_code: str
    acc_no: str
    amount: Decimal
    facility_type: int  # 496 = PAYMENT/NONE
    origin: str
    success: str        # 'Y' or 'N'
    fail_code: str      # '0' through '8'
    avail_bal: Decimal
    actual_bal: Decimal

class DatabaseError(Exception):
    """Custom exception for DB2/SQL related issues."""
    def __init__(self, message: str, sql_code: int):
        super().__init__(message)
        self.sql_code = sql_code

class AccountManager:
    """
    Legacy Migration: Modernized DBCRFUN logic.
    Handles bank account deposits/withdrawals and transaction logging.
    """

    # Constants mapping to COBOL logic
    FACILITY_TYPE_PAYMENT = 496
    RESTRICTED_ACCOUNT_TYPES = ("MORTGAGE", "LOAN")

    def __init__(self, db_connection: Any):
        """
        :param db_connection: A database connection object supporting PEP 249 (DB-API 2.0)
                              with transaction support.
        """
        self.db = db_connection

    def process_transaction(self, data: AccountCommArea) -> AccountCommArea:
        """
        Main entry point equivalent to PROCEDURE DIVISION.
        Maintains business logic for debit/credit and VSAM-style record locking.
        """
        # Default initialization (A010)
        data["success"] = "N"
        data["fail_code"] = "0"
        
        cursor = self.db.cursor()

        try:
            # 1. Retrieve Account with Lock (Equivalent to SELECT FOR UPDATE)
            # Implements the logic from UPDATE-ACCOUNT-DB2
            account = self._get_account_for_update(cursor, data["sort_code"], data["acc_no"])
            
            if not account:
                data["fail_code"] = "1"  # SQLCODE +100
                return data

            # 2. Business Validation (UAD010 logic)
            acc_type = account["type"].strip()
            is_payment = data["facility_type"] == self.FACILITY_TYPE_PAYMENT

            # Check for Mortgage/Loan restrictions
            if acc_type in self.RESTRICTED_ACCOUNT_TYPES and is_payment:
                data["fail_code"] = "4"
                return data

            # Debit check (Insufficient funds)
            if data["amount"] < 0:
                new_difference = account["avail_bal"] + data["amount"]
                if new_difference < 0 and is_payment:
                    data["fail_code"] = "3"
                    return data

            # 3. Calculate and Update Balances
            new_avail = account["avail_bal"] + data["amount"]
            new_actual = account["actual_bal"] + data["amount"]

            self._update_account(cursor, data, new_avail, new_actual)

            # Update COMMAREA for return
            data["avail_bal"] = new_avail
            data["actual_bal"] = new_actual

            # 4. Write to PROCTRAN (Transaction Log)
            # Note: In Python/SQL, we perform this within the same transaction.
            # If this fails, the whole transaction will rollback.
            self._write_to_proctran(cursor, data, acc_type)

            # If we reached here, commit changes
            self.db.commit()
            data["success"] = "Y"
            data["fail_code"] = "0"

        except DatabaseError as de:
            self.db.rollback()
            self._check_storm_drain(de.sql_code)
            data["fail_code"] = "2"
        except Exception as e:
            self.db.rollback()
            logger.error(f"System Error: {str(e)}")
            data["fail_code"] = "2"
        finally:
            cursor.close()

        return data

    def _get_account_for_update(self, cursor: Any, sort_code: str, acc_no: str) -> Optional[dict]:
        """SQL implementation of SELECT ... WHERE ... FOR UPDATE."""
        sql = """
            SELECT ACCOUNT_TYPE, ACCOUNT_AVAILABLE_BALANCE, ACCOUNT_ACTUAL_BALANCE,
                   ACCOUNT_EYECATCHER, ACCOUNT_CUSTOMER_NUMBER, ACCOUNT_OPENED,
                   ACCOUNT_OVERDRAFT_LIMIT, ACCOUNT_LAST_STATEMENT, ACCOUNT_NEXT_STATEMENT
            FROM ACCOUNT 
            WHERE ACCOUNT_SORTCODE = %s AND ACCOUNT_NUMBER = %s
            FOR UPDATE
        """
        # Note: FOR UPDATE ensures the VSAM-style READ UPDATE lock is held
        cursor.execute(sql, (sort_code, acc_no))
        row = cursor.fetchone()
        
        if not row:
            return None
            
        return {
            "type": row[0],
            "avail_bal": Decimal(str(row[1])),
            "actual_bal": Decimal(str(row[2])),
            "eyecatcher": row[3],
            "cust_no": row[4],
            "opened": row[5],
            "overdraft_lim": row[6],
            "last_stmt": row[7],
            "next_stmt": row[8]
        }

    def _update_account(self, cursor: Any, data: AccountCommArea, 
                        new_avail: Decimal, new_actual: Decimal) -> None:
        """Persists the calculated balance updates."""
        sql = """
            UPDATE ACCOUNT
            SET ACCOUNT_AVAILABLE_BALANCE = %s,
                ACCOUNT_ACTUAL_BALANCE = %s
            WHERE ACCOUNT_SORTCODE = %s AND ACCOUNT_NUMBER = %s
        """
        try:
            cursor.execute(sql, (new_avail, new_actual, data["sort_code"], data["acc_no"]))
        except Exception:
            raise DatabaseError("Update failed", -1)

    def _write_to_proctran(self, cursor: Any, data: AccountCommArea, acc_type: str) -> None:
        """Equivalent to WRITE-TO-PROCTRAN-DB2 logic."""
        now = datetime.now()
        
        # Determine transaction type and description (WTPD010 logic)
        is_payment = data["facility_type"] == self.FACILITY_TYPE_PAYMENT
        
        if data["amount"] < 0:
            tran_type = "PDR" if is_payment else "DEB"
            description = data["origin"][:14] if is_payment else "COUNTER WTHDRW"
        else:
            tran_type = "PCR" if is_payment else "CRE"
            description = data["origin"][:14] if is_payment else "COUNTER RECVED"

        sql = """
            INSERT INTO PROCTRAN (
                PROCTRAN_EYECATCHER, PROCTRAN_SORTCODE, PROCTRAN_NUMBER,
                PROCTRAN_DATE, PROCTRAN_TIME, PROCTRAN_REF,
                PROCTRAN_TYPE, PROCTRAN_DESC, PROCTRAN_AMOUNT
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            "PRTR",
            data["sort_code"],
            data["acc_no"],
            now.strftime("%d.%m.%Y"),
            now.strftime("%H%M%S"),
            "REF-" + now.strftime("%y%m%d%H%M"), # Simplified task reference
            tran_type,
            description,
            data["amount"]
        )

        try:
            cursor.execute(sql, params)
        except Exception:
            # If insert fails, COBOL triggers a SYNCPOINT ROLLBACK (WTPD010)
            raise DatabaseError("Failed to write to transaction log", -2)

    def _check_storm_drain(self, sql_code: int) -> None:
        """Equivalent to CHECK-FOR-STORM-DRAIN-DB2 logic."""
        if sql_code == 923:
            logger.error(f"DBCRFUN: Storm Drain condition (DB2 Connection lost) met. SQLCODE: {sql_code}")
        elif sql_code == -1: # Representing Deadlock / AD2Z
            logger.error("DB2 DEADLOCK DETECTED IN DBCRFUN")