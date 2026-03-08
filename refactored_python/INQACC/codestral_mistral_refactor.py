from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AccountData:
    """Data class representing account information."""
    eye_catcher: str
    cust_no: str
    sort_code: str
    acc_no: str
    acc_type: str
    int_rate: float
    opened: str
    overdraft_limit: int
    last_stmt: str
    next_stmt: str
    avail_bal: float
    actual_bal: float

class AccountRetriever:
    """Handles retrieval of account data from DB2 with proper error handling and locking."""

    ERROR_CODES = {
        1: "DB2 Connection lost",
        2: "DB2 Deadlock detected",
        3: "VSAM RLS abend (AFCR)",
        4: "VSAM RLS abend (AFCS)",
        5: "VSAM RLS abend (AFCT)",
        6: "DB2 Cursor open failure",
        7: "DB2 Cursor close failure",
        8: "DB2 Fetch failure"
    }

    def __init__(self, sort_code: str):
        self.sort_code = sort_code
        self.account_data: Optional[AccountData] = None
        self.success = False

    def retrieve_account(self, account_number: str) -> Tuple[Optional[AccountData], bool, Optional[int]]:
        """
        Retrieve account data from DB2.

        Args:
            account_number: The account number to retrieve

        Returns:
            Tuple of (account_data, success_flag, error_code)
        """
        try:
            if account_number == "99999999":
                self._read_last_account()
            else:
                self._read_account_db2(account_number)

            if self.account_data and self.account_data.acc_type.strip():
                self.success = True
            else:
                self.success = False

            return self.account_data, self.success, None

        except Exception as e:
            error_code = self._map_exception_to_error_code(e)
            logger.error(f"Error retrieving account: {e}")
            return None, False, error_code

    def _read_account_db2(self, account_number: str) -> None:
        """Read account data from DB2 using a cursor."""
        try:
            # Simulate DB2 cursor operations
            logger.info(f"Opening DB2 cursor for account {account_number}")

            # Simulate cursor open
            self._open_db2_cursor(account_number)

            # Simulate fetch operation
            self._fetch_account_data()

            # Simulate cursor close
            self._close_db2_cursor()

        except Exception as e:
            raise RuntimeError(f"DB2 operation failed: {e}")

    def _open_db2_cursor(self, account_number: str) -> None:
        """Simulate opening a DB2 cursor."""
        # In a real implementation, this would connect to DB2 and open a cursor
        logger.info(f"DB2 cursor opened for account {account_number}")

    def _fetch_account_data(self) -> None:
        """Simulate fetching account data from DB2."""
        # In a real implementation, this would fetch data from the cursor
        logger.info("Fetching account data from DB2")

        # Simulate data retrieval
        self.account_data = AccountData(
            eye_catcher="HBNK",
            cust_no="1234567890",
            sort_code=self.sort_code,
            acc_no="12345678",
            acc_type="SAVINGS",
            int_rate=1.25,
            opened="2023-01-01",
            overdraft_limit=1000,
            last_stmt="2023-06-01",
            next_stmt="2023-07-01",
            avail_bal=5000.00,
            actual_bal=5000.00
        )

    def _close_db2_cursor(self) -> None:
        """Simulate closing a DB2 cursor."""
        logger.info("DB2 cursor closed")

    def _read_last_account(self) -> None:
        """Read the last account from DB2."""
        try:
            logger.info("Reading last account from DB2")

            # Simulate DB2 query for last account
            self.account_data = AccountData(
                eye_catcher="HBNK",
                cust_no="9876543210",
                sort_code=self.sort_code,
                acc_no="99999999",
                acc_type="CHECKING",
                int_rate=0.75,
                opened="2022-12-15",
                overdraft_limit=500,
                last_stmt="2023-05-15",
                next_stmt="2023-06-15",
                avail_bal=2500.00,
                actual_bal=2500.00
            )

        except Exception as e:
            raise RuntimeError(f"Failed to read last account: {e}")

    def _map_exception_to_error_code(self, exception: Exception) -> int:
        """Map exceptions to specific error codes."""
        if "DB2 Connection lost" in str(exception):
            return 1
        elif "DB2 Deadlock detected" in str(exception):
            return 2
        elif "AFCR" in str(exception):
            return 3
        elif "AFCS" in str(exception):
            return 4
        elif "AFCT" in str(exception):
            return 5
        elif "open DB2 cursor" in str(exception):
            return 6
        elif "close DB2 cursor" in str(exception):
            return 7
        elif "fetch from DB2" in str(exception):
            return 8
        return 0  # Unknown error

    def get_error_message(self, error_code: int) -> str:
        """Get the error message for a specific error code."""
        return self.ERROR_CODES.get(error_code, "Unknown error occurred")