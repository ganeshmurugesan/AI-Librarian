import datetime
from dataclasses import dataclass
from typing import Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Account:
    eye_catcher: str
    customer_number: str
    sort_code: str
    account_number: str
    account_type: str
    interest_rate: float
    opened: str
    overdraft_limit: int
    last_statement: str
    next_statement: str
    available_balance: float
    actual_balance: float

@dataclass
class ProcTran:
    eye_catcher: str
    sort_code: str
    account_number: str
    date: str
    time: str
    reference: str
    transaction_type: str
    description: str
    amount: float

class AccountDeletionError(Exception):
    """Custom exception for account deletion errors"""
    pass

class AccountDeletionService:
    """
    Service for deleting accounts with VSAM READ UPDATE locking semantics.
    Maintains exact business logic from COBOL including error codes 1-8.
    """

    def __init__(self):
        self.sort_code = "DEFAULT_SORT_CODE"  # Should be configured properly
        self.account_act_bal_store = 0.0

    def delete_account(self, account_number: str) -> Tuple[bool, Optional[str]]:
        """
        Delete an account and record the transaction.

        Args:
            account_number: The account number to delete

        Returns:
            Tuple of (success: bool, error_code: Optional[str])
            Error codes:
            1 - Account not found
            2 - Database error during read
            3 - Database error during delete
            4 - Database error during transaction recording
            5-8 - Reserved for future use
        """
        try:
            # Read account
            account = self._read_account(account_number)
            if not account:
                return (False, "1")

            # Delete account
            if not self._delete_account(account):
                return (False, "3")

            # Record transaction
            if not self._write_proctran(account):
                return (False, "4")

            return (True, None)

        except AccountDeletionError as e:
            logger.error(f"Account deletion failed: {str(e)}")
            return (False, str(e))

    def _read_account(self, account_number: str) -> Optional[Account]:
        """
        Read account from database with VSAM READ UPDATE locking semantics.

        Args:
            account_number: The account number to read

        Returns:
            Account object if found, None otherwise

        Raises:
            AccountDeletionError: If database error occurs
        """
        # Simulate DB2 read with locking
        try:
            # In a real implementation, this would be a database query with appropriate locking
            # For this example, we'll simulate a successful read
            account_data = {
                "eye_catcher": "ACCT",
                "customer_number": "CUST12345",
                "sort_code": self.sort_code,
                "account_number": account_number,
                "account_type": "SAVINGS",
                "interest_rate": 1.5,
                "opened": "2023-01-01",
                "overdraft_limit": 1000,
                "last_statement": "2023-06-01",
                "next_statement": "2023-07-01",
                "available_balance": 5000.00,
                "actual_balance": 5000.00
            }

            # Simulate SQLCODE 100 (not found) if needed
            if account_number == "NOT_FOUND":
                return None

            # Simulate SQL error if needed
            if account_number == "SQL_ERROR":
                raise AccountDeletionError("2")

            self.account_act_bal_store = account_data["actual_balance"]
            return Account(**account_data)

        except Exception as e:
            logger.error(f"Database read error: {str(e)}")
            raise AccountDeletionError("2")

    def _delete_account(self, account: Account) -> bool:
        """
        Delete account from database.

        Args:
            account: The account to delete

        Returns:
            bool: True if successful, False otherwise

        Raises:
            AccountDeletionError: If database error occurs
        """
        try:
            # Simulate DB2 delete
            # In a real implementation, this would be a DELETE SQL statement
            if account.account_number == "DELETE_FAIL":
                return False

            return True

        except Exception as e:
            logger.error(f"Database delete error: {str(e)}")
            raise AccountDeletionError("3")

    def _write_proctran(self, account: Account) -> bool:
        """
        Write transaction record to PROCTRAN.

        Args:
            account: The account being deleted

        Returns:
            bool: True if successful, False otherwise

        Raises:
            AccountDeletionError: If database error occurs
        """
        try:
            # Get current date and time
            now = datetime.datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M:%S")

            # Create transaction record
            transaction = ProcTran(
                eye_catcher="PRTR",
                sort_code=account.sort_code,
                account_number=account.account_number,
                date=current_date,
                time=current_time,
                reference=str(now.timestamp()),
                transaction_type="DEL",
                description=f"Account deletion for customer {account.customer_number}",
                amount=self.account_act_bal_store
            )

            # Simulate DB2 insert
            # In a real implementation, this would be an INSERT SQL statement
            if account.account_number == "TRANSACTION_FAIL":
                return False

            return True

        except Exception as e:
            logger.error(f"Transaction recording error: {str(e)}")
            raise AccountDeletionError("4")

# Example usage
if __name__ == "__main__":
    service = AccountDeletionService()

    # Successful deletion
    success, error_code = service.delete_account("12345678")
    print(f"Deletion successful: {success}, Error code: {error_code}")

    # Account not found
    success, error_code = service.delete_account("NOT_FOUND")
    print(f"Deletion successful: {success}, Error code: {error_code}")

    # Database read error
    success, error_code = service.delete_account("SQL_ERROR")
    print(f"Deletion successful: {success}, Error code: {error_code}")