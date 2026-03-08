from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Final, TypedDict
import datetime
import logging

# Simulation of legacy system responses and DB2/VSAM states
SQL_SUCCESS: Final[int] = 0
SQL_NOT_FOUND: Final[int] = 100
SQL_CONNECTION_LOST: Final[int] = 923

@dataclass
class AccountRecord:
    """Represents the mapped ACCOUNT record from the datastore."""
    eye_catcher: str = ""
    customer_number: str = ""
    sort_code: str = ""
    account_number: str = ""
    account_type: str = ""
    interest_rate: Decimal = Decimal("0.00")
    opened_date: str = ""  # Format: DDMMYYYY
    overdraft_limit: int = 0
    last_stmt_date: str = ""  # Format: DDMMYYYY
    next_stmt_date: str = ""  # Format: DDMMYYYY
    available_balance: Decimal = Decimal("0.00")
    actual_balance: Decimal = Decimal("0.00")

class InquiryResponse(TypedDict):
    """COMMAREA equivalent for the program output."""
    success: str  # 'Y' or 'N'
    fail_code: str  # '0' through '8'
    customer_found: str  # 'Y' or 'N'
    accounts: list[AccountRecord]
    number_of_accounts: int

class DatabaseError(Exception):
    """Custom exception to simulate SQLCODE failures."""
    def __init__(self, sql_code: int, message: str):
        self.sql_code = sql_code
        super().__init__(message)

class StormDrainException(Exception):
    """Triggered by specific VSAM or DB2 conditions (Storm Drain logic)."""
    def __init__(self, code: str):
        self.code = code

class AccountInquiryService:
    """
    Rewrite of INQACCCU: Legacy Account Inquiry Service.
    Handles customer validation via external link and retrieves up to 20 account
    records using cursor-based logic with strict transactional integrity.
    """

    MAX_ACCOUNTS: Final[int] = 20

    def __init__(self, db_connection, external_services_client):
        self.db = db_connection
        self.external_services = external_services_client
        self.logger = logging.getLogger(__name__)

    def inquire_customer_accounts(self, customer_number: str, sort_code: str) -> InquiryResponse:
        """
        Main entry point (A010) to determine account associations for a customer.
        
        Args:
            customer_number: 10-digit customer identifier.
            sort_code: 6-digit bank sort code.

        Returns:
            InquiryResponse containing success flags and account data.
        """
        response: InquiryResponse = {
            "success": "N",
            "fail_code": "0",
            "customer_found": "N",
            "accounts": [],
            "number_of_accounts": 0
        }

        try:
            # CC010 - CUSTOMER-CHECK
            if not self._check_customer_exists(customer_number):
                response["fail_code"] = "1"
                return response
            
            response["customer_found"] = "Y"

            # RAD010 - READ-ACCOUNT-DB2
            self._fetch_accounts(customer_number, sort_code, response)
            
            response["success"] = "Y"
            
        except StormDrainException as sde:
            # Handles VSAM AFCR, AFCS, AFCT or DB2 923 logic
            self.logger.error(f"Storm Drain condition met: {sde.code}")
            self._perform_rollback()
            response["success"] = "N"
            response["fail_code"] = "7"  # Code for Storm Drain / RLS issues
        except DatabaseError as de:
            # Mapping SQL failures to fail codes 2, 3, 4
            self._perform_rollback()
            response["success"] = "N"
            # fail_code is set within the specific DB operation
        except Exception as e:
            self.logger.critical(f"Unexpected System Abend: {str(e)}")
            self._perform_rollback()
            response["fail_code"] = "8" # General system failure

        return response

    def _check_customer_exists(self, customer_number: str) -> bool:
        """
        Equivalent to LINK PROGRAM 'INQCUST'.
        Validates customer status.
        """
        if not customer_number or customer_number == "0000000000" or customer_number == "9999999999":
            return False
            
        # Simulate EXEC CICS LINK
        result = self.external_services.link_inq_cust(customer_number)
        return result.get("success") == "Y"

    def _fetch_accounts(self, cust_no: str, sort_code: str, response: InquiryResponse) -> None:
        """
        Simulates DB2 Cursor OPEN, FETCH loop, and CLOSE (RAD010/FD010).
        Maintains exact mapping and reformatting logic.
        """
        cursor = None
        try:
            # RAD010: OPEN CURSOR
            try:
                cursor = self.db.cursor()
                # 'FOR FETCH ONLY' equivalent in modern DB context
                cursor.execute(
                    "SELECT ACCOUNT_EYECATCHER, ACCOUNT_CUSTOMER_NUMBER, ACCOUNT_SORTCODE, "
                    "ACCOUNT_NUMBER, ACCOUNT_TYPE, ACCOUNT_INTEREST_RATE, ACCOUNT_OPENED, "
                    "ACCOUNT_OVERDRAFT_LIMIT, ACCOUNT_LAST_STATEMENT, ACCOUNT_NEXT_STATEMENT, "
                    "ACCOUNT_AVAILABLE_BALANCE, ACCOUNT_ACTUAL_BALANCE "
                    "FROM ACCOUNT WHERE ACCOUNT_CUSTOMER_NUMBER = ? AND ACCOUNT_SORTCODE = ?",
                    (cust_no, sort_code)
                )
            except Exception as e:
                response["fail_code"] = "2"
                self._check_storm_drain_db2(getattr(e, 'sql_code', 0))
                raise DatabaseError(2, "Cursor Open Failure")

            # FD010: FETCH loop
            account_count = 0
            while account_count < self.MAX_ACCOUNTS:
                row = cursor.fetchone()
                
                if not row: # SQLCODE 100
                    break
                
                account_count += 1
                
                # Map and Reformat Dates (YYYY-MM-DD -> DDMMYYYY)
                record = AccountRecord(
                    eye_catcher=row[0],
                    customer_number=row[1],
                    sort_code=row[2],
                    account_number=row[3],
                    account_type=row[4],
                    interest_rate=Decimal(str(row[5])),
                    opened_date=self._reformat_date(row[6]),
                    overdraft_limit=int(row[7]),
                    last_stmt_date=self._reformat_date(row[8]),
                    next_stmt_date=self._reformat_date(row[9]),
                    available_balance=Decimal(str(row[10])),
                    actual_balance=Decimal(str(row[11]))
                )
                response["accounts"].append(record)

            response["number_of_accounts"] = account_count

        except DatabaseError:
            raise
        except Exception as e:
            # SQLCODE failure during FETCH
            response["fail_code"] = "3"
            response["number_of_accounts"] = 0
            raise DatabaseError(3, f"Fetch failure: {str(e)}")
        finally:
            # RAD010: CLOSE CURSOR
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    # If we haven't already failed with code 2 or 3
                    if response["fail_code"] == "0":
                        response["fail_code"] = "4"
                        raise DatabaseError(4, "Cursor Close Failure")

    def _reformat_date(self, db2_date: Optional[str]) -> str:
        """
        Converts DB2 YYYY-MM-DD to COBOL reformat layout DDMMYYYY.
        """
        if not db2_date or len(db2_date) < 10:
            return "00000000"
        # Extract YYYY (0:4), MM (5:7), DD (8:10) assuming ISO format
        yr = db2_date[0:4]
        mn = db2_date[5:7]
        dy = db2_date[8:10]
        return f"{dy}{mn}{yr}"

    def _check_storm_drain_db2(self, sql_code: int) -> None:
        """Check for DB2 connection loss (SQLCODE 923)."""
        if sql_code == SQL_CONNECTION_LOST:
            raise StormDrainException("DB2 Connection Lost")

    def _perform_rollback(self) -> None:
        """Equivalent to EXEC CICS SYNCPOINT ROLLBACK."""
        try:
            self.db.rollback()
            self.logger.info("Syncpoint Rollback performed successfully.")
        except Exception as e:
            # AH010 / RAD010 Abend Handling for failed rollback
            self.logger.critical(f"Integrity Issue: Rollback failed: {str(e)}")
            # In CICS this would Link to ABNDPROC and then EXEC CICS ABEND
            raise SystemExit("HROL - Integrity failure on rollback")

    def handle_vsam_rls_abend(self, abend_code: str) -> None:
        """
        Maintains business logic for VSAM RLS specific abends (AFCR, AFCS, AFCT).
        """
        if abend_code in ['AFCR', 'AFCS', 'AFCT']:
            self.logger.warning(f"VSAM RLS Storm Drain triggered: {abend_code}")
            self._perform_rollback()
            raise StormDrainException(abend_code)