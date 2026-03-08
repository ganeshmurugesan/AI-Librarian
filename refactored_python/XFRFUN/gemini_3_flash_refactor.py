import datetime
import logging
from dataclasses import dataclass, field
from typing import Optional, Final

# Return Codes as per legacy specification
RC_FROM_NOT_FOUND: Final[str] = "1"
RC_TO_NOT_FOUND: Final[str] = "2"
RC_DB_ERROR: Final[str] = "3"
RC_INVALID_AMOUNT: Final[str] = "4"
RC_SAME_ACCOUNT: Final[str] = "5"      # Mapped from legacy ABEND 'SAME'
RC_SYNCPOINT_FAIL: Final[str] = "6"    # Mapped from legacy ABEND 'HROL'
RC_DEADLOCK_EXHAUSTED: Final[str] = "7" # Mapped from retry limit
RC_INTERNAL_ERROR: Final[str] = "8"

@dataclass
class AccountRecord:
    """Represents the DB2 ACCDB2 copybook structure."""
    eyecatcher: str = "0"
    customer_no: str = ""
    sort_code: str = ""
    account_no: str = ""
    account_type: str = ""
    interest_rate: float = 0.0
    opened_date: str = ""
    overdraft_limit: int = 0
    last_stmt: str = ""
    next_stmt: str = ""
    available_balance: float = 0.0
    actual_balance: float = 0.0

@dataclass
class ProcTranRecord:
    """Represents the DB2 PROCDB2 copybook structure."""
    eyecatcher: str = "PRTR"
    sort_code: str = ""
    account_no: str = ""
    date: str = ""
    time: str = ""
    ref: str = ""
    type: str = "XFR"
    description: str = ""
    amount: float = 0.0

class FundTransferService:
    """
    Migration of COBOL XFRFUN program.
    Maintains exact business logic for transaction ordering and deadlock handling.
    """

    def __init__(self, db_connection):
        self.db = db_connection
        self.deadlock_retry_limit: int = 5
        self.logger = logging.getLogger(__name__)

    def transfer_funds(self, 
                       from_acc: str, from_sort: str, 
                       to_acc: str, to_sort: str, 
                       amount: float) -> dict:
        """
        Executes fund transfer with legacy business rules and locking order.
        
        :param from_acc: Source account number
        :param from_sort: Source sort code
        :param to_acc: Destination account number
        :param to_sort: Destination sort code
        :param amount: Amount to transfer
        :return: Commarea-style dictionary with success flags and balances
        """
        response = {
            "COMM-SUCCESS": "N",
            "COMM-FAIL-CODE": "0",
            "COMM-FAVBAL": 0.0,
            "COMM-FACTBAL": 0.0,
            "COMM-TAVBAL": 0.0,
            "COMM-TACTBAL": 0.0
        }

        # Validate Amount (A010)
        if amount <= 0:
            response["COMM-FAIL-CODE"] = RC_INVALID_AMOUNT
            return response

        # Prevent same-account transfer (UAD010)
        if from_acc == to_acc and from_sort == to_sort:
            self.logger.error("Cannot transfer to the same account")
            response["COMM-FAIL-CODE"] = RC_SAME_ACCOUNT
            # Equivalent to EXEC CICS ABEND ABCODE('SAME')
            raise RuntimeError("ABEND SAME: Same account transfer prohibited")

        # Business Logic: Lock records in ascending order of account number 
        # to prevent deadlocks (Legacy VSAM/DB2 strategy)
        retry_count = 0
        while retry_count <= self.deadlock_retry_limit:
            try:
                self._execute_transfer_logic(from_acc, from_sort, to_acc, to_sort, amount, response)
                return response
            except Exception as e:
                if "DEADLOCK" in str(e).upper():
                    retry_count += 1
                    if retry_count > self.deadlock_retry_limit:
                        response["COMM-FAIL-CODE"] = RC_DEADLOCK_EXHAUSTED
                        return response
                    self.db.rollback()
                    continue
                else:
                    self.db.rollback()
                    raise

    def _execute_transfer_logic(self, f_acc: str, f_sort: str, t_acc: str, t_sort: str, 
                                amount: float, response: dict) -> None:
        """Internal logic maintaining specific legacy update sequence."""
        
        # Determine sequence to avoid deadlocks (UAD010 logic)
        if f_acc < t_acc:
            # Update From first
            self._update_account(f_acc, f_sort, -amount, response, is_from=True)
            if response["COMM-SUCCESS"] == "Y":
                self._update_account(t_acc, t_sort, amount, response, is_from=False)
        else:
            # Update To first
            self._update_account(t_acc, t_sort, amount, response, is_from=False)
            if response["COMM-SUCCESS"] == "Y":
                self._update_account(f_acc, f_sort, -amount, response, is_from=True)

        # Rollback logic if either failed
        if response["COMM-SUCCESS"] == "N":
            self.db.rollback()
            return

        # Record Transaction (WTPD010)
        self._write_proctran(f_acc, f_sort, t_acc, t_sort, amount)
        
        self.db.commit()
        response["COMM-SUCCESS"] = "Y"

    def _update_account(self, acc_no: str, sort_code: str, delta: float, 
                        response: dict, is_from: bool) -> None:
        """
        Performs SELECT FOR UPDATE and UPDATE (SQL logic from UADF010/UADT010).
        """
        try:
            # SELECT logic
            row = self.db.execute(
                "SELECT * FROM ACCOUNT WHERE ACCOUNT_NUMBER = ? AND ACCOUNT_SORTCODE = ? FOR UPDATE",
                (acc_no, sort_code)
            ).fetchone()

            if not row:
                response["COMM-SUCCESS"] = "N"
                response["COMM-FAIL-CODE"] = RC_FROM_NOT_FOUND if is_from else RC_TO_NOT_FOUND
                return

            # Map to record
            acc = AccountRecord(**row)
            
            # Compute new balances
            acc.available_balance += delta
            acc.actual_balance += delta

            # UPDATE logic
            self.db.execute(
                """UPDATE ACCOUNT SET 
                   ACCOUNT_AVAILABLE_BALANCE = ?, 
                   ACCOUNT_ACTUAL_BALANCE = ? 
                   WHERE ACCOUNT_NUMBER = ? AND ACCOUNT_SORTCODE = ?""",
                (acc.available_balance, acc.actual_balance, acc_no, sort_code)
            )

            # Update Commarea return values
            if is_from:
                response["COMM-FAVBAL"] = acc.available_balance
                response["COMM-FACTBAL"] = acc.actual_balance
            else:
                response["COMM-TAVBAL"] = acc.available_balance
                response["COMM-TACTBAL"] = acc.actual_balance
            
            response["COMM-SUCCESS"] = "Y"

        except Exception as e:
            response["COMM-SUCCESS"] = "N"
            response["COMM-FAIL-CODE"] = RC_DB_ERROR
            self.logger.error(f"DB Error updating account {acc_no}: {e}")
            # Check for Storm Drain conditions (CFSDD010)
            if "Connection lost" in str(e):
                self.logger.critical("STORM DRAIN: DB2 Connection lost")
            raise e

    def _write_proctran(self, f_acc: str, f_sort: str, t_acc: str, t_sort: str, amount: float) -> None:
        """Legacy logic for successful transaction logging (WTPD010)."""
        now = datetime.datetime.now()
        
        tran = ProcTranRecord(
            sort_code=f_sort,
            account_no=f_acc,
            date=now.strftime("%d.%m.%Y"),
            time=now.strftime("%H%M%S"),
            ref=str(now.timestamp()).replace(".", "")[:12], # Simulation of EIBTASKN
            amount=amount,
            description=f"XFR TO {t_sort} {t_acc}"
        )

        try:
            self.db.execute(
                """INSERT INTO PROCTRAN (
                    PROCTRAN_EYECATCHER, PROCTRAN_SORTCODE, PROCTRAN_NUMBER,
                    PROCTRAN_DATE, PROCTRAN_TIME, PROCTRAN_REF,
                    PROCTRAN_TYPE, PROCTRAN_DESC, PROCTRAN_AMOUNT
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tran.eyecatcher, tran.sort_code, tran.account_no,
                 tran.date, tran.time, tran.ref,
                 tran.type, tran.description, tran.amount)
            )
        except Exception as e:
            self.logger.error("Data Inconsistency: Account updated but PROCTRAN failed")
            # Legacy ABCODE 'WPCD'
            raise RuntimeError(f"ABEND WPCD: PROCTRAN Insert Failure - {e}")