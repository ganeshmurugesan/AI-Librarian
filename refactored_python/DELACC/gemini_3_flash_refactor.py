from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
import logging

# Configure logging to mimic the COBOL DISPLAY and Abend Handler outputs
logger = logging.getLogger("DELACC")

class CicsAbend(Exception):
    """Custom exception to simulate CICS ABEND behavior."""
    def __init__(self, abcode: str, message: str):
        self.abcode = abcode
        self.message = message
        super().__init__(f"ABEND {abcode}: {message}")

@dataclass
class AccountData:
    """Represents the ACCOUNT datastore record and COMMAREA structure."""
    eyecatcher: str = "ACCT"
    cust_no: str = ""
    sort_code: str = ""
    acc_no: str = ""
    acc_type: str = ""
    int_rate: Decimal = Decimal("0.00")
    opened_date: str = ""  # YYYY-MM-DD
    overdraft_limit: int = 0
    last_stmt_date: str = ""
    next_stmt_date: str = ""
    avail_bal: Decimal = Decimal("0.00")
    actual_bal: Decimal = Decimal("0.00")
    
    # Status Flags (COMMAREA)
    del_success: str = " "
    del_fail_cd: str = " "  # Standardized 1-8 return codes

class DeleteAccountProcessor:
    """
    Migration of COBOL DELACC program.
    Handles account retrieval, deletion, and transaction logging.
    """

    def __init__(self, db_connection: Any):
        self.db = db_connection

    def process_request(self, sort_code: str, acc_no: str) -> AccountData:
        """
        Main execution logic for deleting an account.
        
        :param sort_code: The account sort code.
        :param acc_no: The account number.
        :return: Updated AccountData object containing result flags.
        """
        account = AccountData(sort_code=sort_code, acc_no=acc_no)

        # 1. READ-ACCOUNT-DB2
        # Logic: Attempt to find the record and lock it for update (VSAM READ UPDATE simulation)
        account_found = self._read_account_for_update(account)

        if not account_found:
            account.del_success = "N"
            account.del_fail_cd = "1"  # Error Code 1: Record Not Found
            return account

        # 2. DEL-ACCOUNT-DB2
        # Logic: If successfully retrieved and locked, proceed to delete
        try:
            success = self._delete_account(account)
            if success:
                account.del_success = "Y"
                account.del_fail_cd = " "
                
                # 3. WRITE-PROCTRAN
                self._write_proctran(account)
            else:
                account.del_success = "N"
                account.del_fail_cd = "3"  # Error Code 3: Delete Operation Failed
        except Exception as e:
            # Catch-all for other error codes 2, 4-8 based on specific infrastructure failures
            account.del_success = "N"
            account.del_fail_cd = "8"  # Error Code 8: General System/DB Error
            logger.error(f"Unexpected failure in deletion: {str(e)}")

        return account

    def _read_account_for_update(self, account: AccountData) -> bool:
        """
        Executes SELECT ... FOR UPDATE to maintain VSAM-style locking logic.
        """
        sql = """
            SELECT 
                ACCOUNT_EYECATCHER, ACCOUNT_CUSTOMER_NUMBER, ACCOUNT_TYPE,
                ACCOUNT_INTEREST_RATE, ACCOUNT_OPENED, ACCOUNT_OVERDRAFT_LIMIT,
                ACCOUNT_LAST_STATEMENT, ACCOUNT_NEXT_STATEMENT,
                ACCOUNT_AVAILABLE_BALANCE, ACCOUNT_ACTUAL_BALANCE
            FROM ACCOUNT
            WHERE ACCOUNT_NUMBER = %s AND ACCOUNT_SORTCODE = %s
            FOR UPDATE
        """
        try:
            cursor = self.db.cursor()
            cursor.execute(sql, (account.acc_no, account.sort_code))
            row = cursor.fetchone()

            if not row:
                return False

            # Map DB columns to object attributes
            account.eyecatcher = row[0]
            account.cust_no = row[1]
            account.acc_type = row[2]
            account.int_rate = Decimal(str(row[3]))
            account.opened_date = str(row[4])
            account.overdraft_limit = int(row[5])
            account.last_stmt_date = str(row[6])
            account.next_stmt_date = str(row[7])
            account.avail_bal = Decimal(str(row[8]))
            account.actual_bal = Decimal(str(row[9]))
            
            return True

        except Exception as e:
            # Equivalent to COBOL SQLCODE checking and HRAC ABEND
            logger.error(f"Issue with ACCOUNT row select. SQLCODE Error. For Account {account.acc_no}")
            raise CicsAbend(abcode="HRAC", message=str(e))

    def _delete_account(self, account: AccountData) -> bool:
        """
        Executes the DELETE SQL.
        """
        sql = "DELETE FROM ACCOUNT WHERE ACCOUNT_SORTCODE = %s AND ACCOUNT_NUMBER = %s"
        try:
            cursor = self.db.cursor()
            cursor.execute(sql, (account.sort_code, account.acc_no))
            return cursor.rowcount > 0
        except Exception:
            return False

    def _write_proctran(self, account: AccountData) -> None:
        """
        Logs the deletion to the PROCTRAN audit table.
        """
        now = datetime.now()
        # Simulation of EIBTASKN and CICS formatting
        ref_id = f"{now.strftime('%H%M%S')}" 
        
        # Build description string as per COBOL PROCTRAN-AREA logic
        desc = f"DEL {account.cust_no} {account.acc_type} {account.last_stmt_date}"[:40]

        sql = """
            INSERT INTO PROCTRAN (
                PROCTRAN_EYECATCHER, PROCTRAN_SORTCODE, PROCTRAN_NUMBER,
                PROCTRAN_DATE, PROCTRAN_TIME, PROCTRAN_REF,
                PROCTRAN_TYPE, PROCTRAN_DESC, PROCTRAN_AMOUNT
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            "PRTR",
            account.sort_code,
            account.acc_no,
            now.strftime("%d.%m.%Y"),
            now.strftime("%H%M%S"),
            ref_id,
            "DAB", # PROC-TY-BRANCH-DELETE-ACCOUNT
            desc,
            account.actual_bal
        )

        try:
            cursor = self.db.cursor()
            cursor.execute(sql, params)
        except Exception as e:
            # Equivalent to HWPT ABEND
            logger.error(f"WPD010 - Unable to WRITE to PROCTRAN row. Data: {params}")
            raise CicsAbend(abcode="HWPT", message=str(e))