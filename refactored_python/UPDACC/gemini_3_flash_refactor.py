from typing import Optional, Any
from dataclasses import dataclass, field
from decimal import Decimal
import datetime
import logging

@dataclass
class AccountCommarea:
    """
    Represents the UPDACC COMMAREA (Data Structure) for Account updates.
    """
    eyecatcher: str = "ACCT"
    cust_no: str = ""
    sort_code: str = ""
    acc_no: str = ""
    acc_type: str = ""
    int_rate: Decimal = Decimal("0.00")
    opened_year: int = 0
    opened_month: int = 0
    opened_day: int = 0
    overdraft_limit: int = 0
    last_stmt_year: int = 0
    last_stmt_month: int = 0
    last_stmt_day: int = 0
    next_stmt_year: int = 0
    next_stmt_month: int = 0
    next_stmt_day: int = 0
    avail_bal: Decimal = Decimal("0.00")
    actual_bal: Decimal = Decimal("0.00")
    success: str = "N"

class AccountUpdateService:
    """
    Service for migrating UPDACC COBOL logic. 
    Handles DB2/VSAM style record updates with row-level locking.
    """

    # Error Code Mapping
    SUCCESS = 0
    ERR_NOT_FOUND = 1
    ERR_INVALID_ACC_TYPE = 2
    ERR_UPDATE_FAILED = 3
    ERR_CONNECTION_ERROR = 4
    ERR_DEADLOCK = 5
    ERR_LOCK_TIMEOUT = 6
    ERR_DATA_INTEGRITY = 7
    ERR_UNKNOWN = 8

    def __init__(self, db_connection: Any):
        """
        :param db_connection: A PEP 249 compliant database connection object.
        """
        self.db = db_connection
        self.logger = logging.getLogger(__name__)

    def update_account(self, commarea: AccountCommarea) -> tuple[int, AccountCommarea]:
        """
        Updates the account details based on COBOL UPDACC logic.
        
        Logic maintained:
        1. Select for Update (mimicking VSAM READ UPDATE locking).
        2. Validation of Account Type.
        3. Restricted field updates (Type, Rate, Overdraft).
        4. Return full record state.
        
        :return: Tuple of (Return Code 0-8, Updated Commarea)
        """
        cursor = self.db.cursor()
        
        try:
            # 1. READ WITH LOCK (SELECT ... FOR UPDATE)
            # This maintains the exact business logic of obtaining a lock before update.
            select_sql = """
                SELECT 
                    ACCOUNT_EYECATCHER, ACCOUNT_CUSTOMER_NUMBER, ACCOUNT_SORTCODE, 
                    ACCOUNT_NUMBER, ACCOUNT_TYPE, ACCOUNT_INTEREST_RATE, 
                    ACCOUNT_OPENED, ACCOUNT_OVERDRAFT_LIMIT, ACCOUNT_LAST_STATEMENT, 
                    ACCOUNT_NEXT_STATEMENT, ACCOUNT_AVAILABLE_BALANCE, ACCOUNT_ACTUAL_BALANCE
                FROM ACCOUNT
                WHERE ACCOUNT_SORTCODE = %s AND ACCOUNT_NUMBER = %s
                FOR UPDATE
            """
            cursor.execute(select_sql, (commarea.sort_code, commarea.acc_no))
            row = cursor.fetchone()

            if not row:
                commarea.success = "N"
                self.logger.error(f"Account not found: {commarea.sort_code}-{commarea.acc_no}")
                return self.ERR_NOT_FOUND, commarea

            # Map DB row to local host variables (HV-ACCOUNT-*)
            hv_eye = row[0]
            hv_cust_no = row[1]
            hv_opened = row[6]  # Expected format YYYY-MM-DD or date object
            hv_last_stmt = row[8]
            hv_next_stmt = row[9]
            hv_avail_bal = row[10]
            hv_actual_bal = row[11]

            # 2. VALIDATION (COBOL: IF COMM-ACC-TYPE = SPACES OR COMM-ACC-TYPE(1:1) = ' ')
            if not commarea.acc_type or commarea.acc_type.isspace() or commarea.acc_type.startswith(' '):
                commarea.success = "N"
                self.logger.error("Validation error: Invalid account-type")
                return self.ERR_INVALID_ACC_TYPE, commarea

            # 3. UPDATE RECORD
            # Only Type, Interest Rate, and Overdraft are permissible for change.
            update_sql = """
                UPDATE ACCOUNT
                SET ACCOUNT_TYPE = %s,
                    ACCOUNT_INTEREST_RATE = %s,
                    ACCOUNT_OVERDRAFT_LIMIT = %s
                WHERE ACCOUNT_SORTCODE = %s AND ACCOUNT_NUMBER = %s
            """
            cursor.execute(update_sql, (
                commarea.acc_type,
                commarea.int_rate,
                commarea.overdraft_limit,
                commarea.sort_code,
                commarea.acc_no
            ))

            if cursor.rowcount == 0:
                commarea.success = "N"
                return self.ERR_UPDATE_FAILED, commarea

            # 4. POPULATE RETURNING COMMAREA
            commarea.eyecatcher = hv_eye
            commarea.cust_no = hv_cust_no
            
            # Reformat Dates (Mimicking DB2-DATE-REFORMAT)
            commarea.opened_year, commarea.opened_month, commarea.opened_day = self._split_date(hv_opened)
            commarea.last_stmt_year, commarea.last_stmt_month, commarea.last_stmt_day = self._split_date(hv_last_stmt)
            commarea.next_stmt_year, commarea.next_stmt_month, commarea.next_stmt_day = self._split_date(hv_next_stmt)
            
            commarea.avail_bal = Decimal(str(hv_avail_bal))
            commarea.actual_bal = Decimal(str(hv_actual_bal))
            commarea.success = "Y"

            self.db.commit()
            return self.SUCCESS, commarea

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Database Exception: {str(e)}")
            # Mapping specific database exceptions to 1-8 codes
            if "deadlock" in str(e).lower():
                return self.ERR_DEADLOCK, commarea
            if "timeout" in str(e).lower():
                return self.ERR_LOCK_TIMEOUT, commarea
            return self.ERR_UNKNOWN, commarea
        finally:
            cursor.close()

    def _split_date(self, date_val: Any) -> tuple[int, int, int]:
        """
        Splits date/string into YYYY, MM, DD components.
        Mimics COBOL DB2-DATE-REFORMAT structure.
        """
        if isinstance(date_val, (datetime.date, datetime.datetime)):
            return date_val.year, date_val.month, date_val.day
        if isinstance(date_val, str) and len(date_val) >= 10:
            # Assumes ISO format YYYY-MM-DD
            try:
                parts = date_val.split('-')
                return int(parts[0]), int(parts[1]), int(parts[2])
            except (ValueError, IndexError):
                return 0, 0, 0
        return 0, 0, 0