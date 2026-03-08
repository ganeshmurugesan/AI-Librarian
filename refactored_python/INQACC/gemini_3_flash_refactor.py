from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from typing import Optional, Protocol, Any
import logging

# Setup logging for abend-style reporting
logger = logging.getLogger("INQACC")

@dataclass
class AccountRecord:
    """Represents the ACCOUNT datastore structure (DB2/VSAM)."""
    eye_catcher: str = ""
    cust_no: str = ""
    sort_code: str = ""
    account_number: str = ""
    account_type: str = ""
    interest_rate: Decimal = Decimal("0.00")
    opened_date: Optional[datetime] = None
    overdraft_limit: int = 0
    last_stmt_date: Optional[datetime] = None
    next_stmt_date: Optional[datetime] = None
    available_balance: Decimal = Decimal("0.00")
    actual_balance: Decimal = Decimal("0.00")

@dataclass
class InqAccCommarea:
    """Represents the INQACC COMMAREA for input/output."""
    sort_code: str = ""
    acc_no: str = ""
    success: str = "N"
    # Output fields
    eye: str = ""
    cust_no: str = ""
    scode: str = ""
    acc_type: str = ""
    int_rate: Decimal = Decimal("0.00")
    opened: str = ""
    overdraft: int = 0
    last_stmt_dt: str = ""
    next_stmt_dt: str = ""
    avail_bal: Decimal = Decimal("0.00")
    actual_bal: Decimal = Decimal("0.00")
    # Meta
    return_code: int = 0  # Codes 1-8

class DatabaseConnection(Protocol):
    """Protocol for DB2/VSAM abstraction."""
    def execute(self, query: str, params: dict[str, Any]) -> Optional[dict[str, Any]]: ...
    def fetch_one(self, query: str, params: dict[str, Any]) -> Optional[dict[str, Any]]: ...
    def rollback(self) -> None: ...

class AccountService:
    """
    Senior Migration Engineer implementation of INQACC.
    Handles account inquiries via DB2 and simulates VSAM RLS locking logic.
    """

    # Error Code Mapping
    RC_SUCCESS = 1
    RC_NOT_FOUND = 2
    RC_SQL_ERROR = 3
    RC_STORM_DRAIN = 4
    RC_DEADLOCK = 5
    RC_VSAM_RLS_FAIL = 6
    RC_ROLLBACK_FAIL = 7
    RC_SYSTEM_ABEND = 8

    def __init__(self, db_conn: DatabaseConnection):
        self.db = db_conn

    def process_inquiry(self, commarea: InqAccCommarea) -> InqAccCommarea:
        """
        Main entry point equivalent to PROCEDURE DIVISION USING DFHCOMMAREA.
        
        :param commarea: The input communication area.
        :return: Updated commarea with record data and return codes.
        """
        try:
            record: Optional[AccountRecord] = None

            # Logic: If account number is 99999999, get the last record
            if commarea.acc_no == "99999999":
                record = self._read_account_last(commarea.sort_code)
            else:
                # Maintain VSAM READ UPDATE logic (Exclusive Lock simulation)
                record = self._read_account_db2(commarea.sort_code, commarea.acc_no)

            if not record or not record.account_type.strip():
                commarea.success = "N"
                commarea.return_code = self.RC_NOT_FOUND
            else:
                self._map_record_to_commarea(record, commarea)
                commarea.success = "Y"
                commarea.return_code = self.RC_SUCCESS

        except Exception as e:
            commarea.success = "N"
            commarea.return_code = self._handle_abends(e)
            
        return commarea

    def _read_account_db2(self, sort_code: str, acc_no: str) -> Optional[AccountRecord]:
        """
        Executes SELECT for specific account. 
        Note: Incorporates VSAM READ UPDATE locking logic via FOR UPDATE.
        """
        query = """
            SELECT * FROM ACCOUNT 
            WHERE ACCOUNT_SORTCODE = :sort_code 
            AND ACCOUNT_NUMBER = :acc_no
            FOR UPDATE OF ACTUAL_BALANCE
        """
        params = {"sort_code": sort_code, "acc_no": acc_no}
        
        try:
            row = self.db.fetch_one(query, params)
            if not row:
                return None
            return self._parse_row(row)
        except Exception as e:
            # Re-raise to trigger the specific abend handler
            raise e

    def _read_account_last(self, sort_code: str) -> Optional[AccountRecord]:
        """Equivalent to READ-ACCOUNT-LAST / GET-LAST-ACCOUNT-DB2."""
        query = """
            SELECT * FROM ACCOUNT 
            WHERE ACCOUNT_SORTCODE = :sort_code 
            ORDER BY ACCOUNT_NUMBER DESC 
            FETCH FIRST 1 ROWS ONLY
        """
        params = {"sort_code": sort_code}
        row = self.db.fetch_one(query, params)
        return self._parse_row(row) if row else None

    def _parse_row(self, row: dict[str, Any]) -> AccountRecord:
        """Maps DB2 result set to AccountRecord with COBOL date reformatting."""
        return AccountRecord(
            eye_catcher=row.get("ACCOUNT_EYECATCHER", ""),
            cust_no=row.get("ACCOUNT_CUSTOMER_NUMBER", ""),
            sort_code=row.get("ACCOUNT_SORTCODE", ""),
            account_number=row.get("ACCOUNT_NUMBER", ""),
            account_type=row.get("ACCOUNT_TYPE", ""),
            interest_rate=Decimal(str(row.get("ACCOUNT_INTEREST_RATE", 0))),
            opened_date=self._reformat_date(row.get("ACCOUNT_OPENED")),
            overdraft_limit=int(row.get("ACCOUNT_OVERDRAFT_LIMIT", 0)),
            last_stmt_date=self._reformat_date(row.get("ACCOUNT_LAST_STATEMENT")),
            next_stmt_date=self._reformat_date(row.get("ACCOUNT_NEXT_STATEMENT")),
            available_balance=Decimal(str(row.get("ACCOUNT_AVAILABLE_BALANCE", 0))),
            actual_balance=Decimal(str(row.get("ACCOUNT_ACTUAL_BALANCE", 0)))
        )

    def _reformat_date(self, date_val: Any) -> Optional[datetime]:
        """Handles COBOL DB2-DATE-REFORMAT logic (YYYY-MM-DD)."""
        if isinstance(date_val, datetime):
            return date_val
        if isinstance(date_val, str):
            try:
                return datetime.strptime(date_val, "%Y-%m-%d")
            except ValueError:
                return None
        return None

    def _map_record_to_commarea(self, record: AccountRecord, commarea: InqAccCommarea) -> None:
        """Maps internal record to the output COMMAREA."""
        commarea.eye = record.eye_catcher
        commarea.cust_no = record.cust_no
        commarea.scode = record.sort_code
        commarea.acc_no = record.account_number
        commarea.acc_type = record.account_type
        commarea.int_rate = record.interest_rate
        commarea.opened = record.opened_date.strftime("%d%m%Y") if record.opened_date else ""
        commarea.overdraft = record.overdraft_limit
        commarea.last_stmt_dt = record.last_stmt_date.strftime("%d%m%Y") if record.last_stmt_date else ""
        commarea.next_stmt_dt = record.next_stmt_date.strftime("%d%m%Y") if record.next_stmt_date else ""
        commarea.avail_bal = record.available_balance
        commarea.actual_bal = record.actual_balance

    def _handle_abends(self, error: Exception) -> int:
        """
        Implements ABEND-HANDLING logic including AD2Z and VSAM RLS codes.
        Returns mapped Return Codes (1-8).
        """
        err_msg = str(error).upper()
        
        # SQLCODE 923 -> Storm Drain
        if "923" in err_msg or "CONNECTION_LOST" in err_msg:
            logger.error("STORM DRAIN: DB2 Connection Lost.")
            return self.RC_STORM_DRAIN

        # AD2Z -> Deadlock
        if "AD2Z" in err_msg or "DEADLOCK" in err_msg:
            logger.error("DB2 DEADLOCK DETECTED (AD2Z)")
            return self.RC_DEADLOCK

        # VSAM RLS Errors: AFCR, AFCS, AFCT
        if any(code in err_msg for code in ["AFCR", "AFCS", "AFCT"]):
            logger.warning("Storm Drain condition met: VSAM RLS Abend.")
            try:
                self.db.rollback()
                return self.RC_VSAM_RLS_FAIL
            except Exception:
                logger.critical("Unable to perform Rollback after VSAM RLS error.")
                return self.RC_ROLLBACK_FAIL

        # General SQL Error
        if "SQLCODE" in err_msg or "DB_ERROR" in err_msg:
            logger.error(f"SQL Failure: {err_msg}")
            return self.RC_SQL_ERROR

        # Default System Abend
        logger.critical(f"Critical System Error: {err_msg}")
        return self.RC_SYSTEM_ABEND