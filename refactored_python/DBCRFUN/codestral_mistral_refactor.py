from dataclasses import dataclass
from typing import Optional, Tuple
import datetime
import logging

# Constants for error codes
ERROR_CODES = {
    1: "Account not found",
    2: "Database error",
    3: "Insufficient funds",
    4: "Invalid account type for transaction",
    5: "VSAM record lock error",
    6: "VSAM record not found",
    7: "VSAM update error",
    8: "Transaction log error"
}

@dataclass
class Account:
    """Represents an account record from the database."""
    eyecatcher: str
    customer_number: str
    sortcode: str
    account_number: str
    account_type: str
    interest_rate: float
    opened_date: str
    overdraft_limit: int
    last_statement: str
    next_statement: str
    available_balance: float
    actual_balance: float

@dataclass
class Transaction:
    """Represents a transaction record for the database."""
    eyecatcher: str
    sortcode: str
    account_number: str
    date: str
    time: str
    reference: str
    transaction_type: str
    description: str
    amount: float

class AccountProcessor:
    """Handles account updates and transactions."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process_transaction(
        self,
        account_number: str,
        sortcode: str,
        amount: float,
        facility_type: int = 496,
        origin: str = ""
    ) -> Tuple[bool, str, Optional[float], Optional[float]]:
        """
        Process a transaction against an account.

        Args:
            account_number: The account number to process
            sortcode: The sort code for the account
            amount: The transaction amount (positive for credit, negative for debit)
            facility_type: The facility type (default 496 for payment)
            origin: Origin information for the transaction

        Returns:
            Tuple of (success_flag, error_code, available_balance, actual_balance)
        """
        success = False
        error_code = "0"
        available_balance = None
        actual_balance = None

        try:
            # Retrieve account information with VSAM READ UPDATE locking
            account = self._get_account_with_lock(sortcode, account_number)
            if not account:
                error_code = "1"
                return (False, error_code, None, None)

            # Validate transaction
            validation_result = self._validate_transaction(account, amount, facility_type)
            if validation_result != "0":
                error_code = validation_result
                return (False, error_code, None, None)

            # Update account balances
            new_available = account.available_balance + amount
            new_actual = account.actual_balance + amount

            # Update account in database
            if not self._update_account(account, new_available, new_actual):
                error_code = "2"
                return (False, error_code, None, None)

            # Log transaction
            if not self._log_transaction(account, amount, facility_type, origin):
                error_code = "8"
                # Rollback account update if transaction logging fails
                self._update_account(account, account.available_balance, account.actual_balance)
                return (False, error_code, None, None)

            success = True
            available_balance = new_available
            actual_balance = new_actual

        except Exception as e:
            self.logger.error(f"Transaction processing failed: {str(e)}")
            error_code = "2"
            # Attempt to rollback any changes
            try:
                if account:
                    self._update_account(account, account.available_balance, account.actual_balance)
            except:
                pass

        return (success, error_code, available_balance, actual_balance)

    def _get_account_with_lock(self, sortcode: str, account_number: str) -> Optional[Account]:
        """
        Retrieve account with VSAM READ UPDATE locking.

        Args:
            sortcode: The sort code for the account
            account_number: The account number

        Returns:
            Account object if found, None otherwise
        """
        # In a real implementation, this would use VSAM APIs with appropriate locking
        # For this example, we'll simulate the behavior
        try:
            # Simulate VSAM READ UPDATE - would actually lock the record in a real system
            # This would be implemented with VSAM APIs or equivalent storage system APIs
            account_data = self._query_account_from_db(sortcode, account_number)
            if not account_data:
                return None

            return Account(
                eyecatcher=account_data["eyecatcher"],
                customer_number=account_data["customer_number"],
                sortcode=account_data["sortcode"],
                account_number=account_data["account_number"],
                account_type=account_data["account_type"],
                interest_rate=account_data["interest_rate"],
                opened_date=account_data["opened_date"],
                overdraft_limit=account_data["overdraft_limit"],
                last_statement=account_data["last_statement"],
                next_statement=account_data["next_statement"],
                available_balance=account_data["available_balance"],
                actual_balance=account_data["actual_balance"]
            )
        except Exception as e:
            self.logger.error(f"Error retrieving account: {str(e)}")
            return None

    def _validate_transaction(self, account: Account, amount: float, facility_type: int) -> str:
        """
        Validate the transaction against account rules.

        Args:
            account: The account to validate against
            amount: The transaction amount
            facility_type: The facility type

        Returns:
            Error code if validation fails, "0" if successful
        """
        # Check for mortgage/loan accounts with payment facility type
        if account.account_type in ("MORTGAGE", "LOAN") and facility_type == 496:
            return "4"

        # Check for sufficient funds for debits
        if amount < 0:
            difference = account.available_balance + amount
            if difference < 0 and facility_type == 496:
                return "3"

        return "0"

    def _update_account(self, account: Account, new_available: float, new_actual: float) -> bool:
        """
        Update account balances in the database.

        Args:
            account: The account to update
            new_available: New available balance
            new_actual: New actual balance

        Returns:
            True if update was successful, False otherwise
        """
        try:
            # In a real implementation, this would execute an SQL UPDATE with appropriate locking
            # For this example, we'll simulate the behavior
            update_data = {
                "eyecatcher": account.eyecatcher,
                "customer_number": account.customer_number,
                "sortcode": account.sortcode,
                "account_number": account.account_number,
                "account_type": account.account_type,
                "interest_rate": account.interest_rate,
                "opened_date": account.opened_date,
                "overdraft_limit": account.overdraft_limit,
                "last_statement": account.last_statement,
                "next_statement": account.next_statement,
                "available_balance": new_available,
                "actual_balance": new_actual
            }

            # Simulate database update
            success = self._execute_account_update(update_data)
            return success
        except Exception as e:
            self.logger.error(f"Error updating account: {str(e)}")
            return False

    def _log_transaction(
        self,
        account: Account,
        amount: float,
        facility_type: int,
        origin: str
    ) -> bool:
        """
        Log a transaction to the transaction database.

        Args:
            account: The account for the transaction
            amount: The transaction amount
            facility_type: The facility type
            origin: Origin information for the transaction

        Returns:
            True if logging was successful, False otherwise
        """
        try:
            # Get current date and time
            now = datetime.datetime.now()
            date_str = now.strftime("%d.%m.%Y")
            time_str = now.strftime("%H%M%S")

            # Determine transaction type and description
            if amount < 0:
                trans_type = "PDR" if facility_type == 496 else "DEB"
                description = origin[:14] if facility_type == 496 else "COUNTER WTHDRW"
            else:
                trans_type = "PCR" if facility_type == 496 else "CRE"
                description = origin[:14] if facility_type == 496 else "COUNTER RECVED"

            transaction = Transaction(
                eyecatcher="PRTR",
                sortcode=account.sortcode,
                account_number=account.account_number,
                date=date_str,
                time=time_str,
                reference=str(now.timestamp()).replace(".", "")[:12],
                transaction_type=trans_type,
                description=description,
                amount=amount
            )

            # Simulate database insert
            success = self._execute_transaction_insert(transaction)
            return success
        except Exception as e:
            self.logger.error(f"Error logging transaction: {str(e)}")
            return False

    # These would be implemented with actual database connectivity in a real system
    def _query_account_from_db(self, sortcode: str, account_number: str) -> Optional[dict]:
        """Simulate querying an account from the database."""
        # In a real implementation, this would execute a SELECT with appropriate locking
        pass

    def _execute_account_update(self, update_data: dict) -> bool:
        """Simulate executing an account update."""
        # In a real implementation, this would execute an SQL UPDATE
        pass

    def _execute_transaction_insert(self, transaction: Transaction) -> bool:
        """Simulate inserting a transaction record."""
        # In a real implementation, this would execute an SQL INSERT
        pass