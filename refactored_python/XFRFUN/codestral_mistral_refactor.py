from dataclasses import dataclass
from typing import Optional, Tuple
import datetime
import logging
from enum import Enum, auto

class ErrorCode(Enum):
    """Error codes for transaction processing"""
    FROM_ACCOUNT_NOT_FOUND = 1
    TO_ACCOUNT_NOT_FOUND = 2
    DB2_ERROR = 3
    NEGATIVE_AMOUNT = 4
    FROM_ACCOUNT_UPDATE_FAILED = 5
    TO_ACCOUNT_UPDATE_FAILED = 6
    PROCTRAN_WRITE_FAILED = 7
    SAME_ACCOUNT_TRANSFER = 8

@dataclass
class AccountData:
    """Data structure for account information"""
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
class TransactionData:
    """Data structure for transaction information"""
    eyecatcher: str
    sortcode: str
    account_number: str
    date: str
    time: str
    reference: str
    transaction_type: str
    description: str
    amount: float

class FundTransferProcessor:
    """
    Modern Python implementation of the COBOL XFRFUN program for fund transfers.
    Maintains exact business logic including VSAM READ UPDATE locking.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.deadlock_retry_count = 0
        self.max_deadlock_retries = 5

    def process_transfer(
        self,
        from_sortcode: str,
        from_account: str,
        to_sortcode: str,
        to_account: str,
        amount: float
    ) -> Tuple[bool, Optional[ErrorCode], Optional[Tuple[float, float, float, float]]]:
        """
        Process a fund transfer between accounts.

        Args:
            from_sortcode: Sort code of the source account
            from_account: Account number of the source account
            to_sortcode: Sort code of the destination account
            to_account: Account number of the destination account
            amount: Amount to transfer

        Returns:
            Tuple containing:
            - Success flag (bool)
            - Error code (ErrorCode or None)
            - Balances (Tuple[from_available, from_actual, to_available, to_actual] or None)
        """
        if amount <= 0:
            return False, ErrorCode.NEGATIVE_AMOUNT, None

        if from_sortcode == to_sortcode and from_account == to_account:
            return False, ErrorCode.SAME_ACCOUNT_TRANSFER, None

        # Determine processing order based on account numbers
        if from_account < to_account:
            # Process FROM account first
            success, error_code, from_balances = self._process_from_account(
                from_sortcode, from_account, amount
            )
            if not success:
                return False, error_code, None

            success, error_code, to_balances = self._process_to_account(
                to_sortcode, to_account, amount
            )
            if not success:
                self._rollback_transaction()
                return False, error_code, None

            # Record successful transaction
            self._record_transaction(
                from_sortcode, from_account, to_sortcode, to_account, amount
            )

            return True, None, (from_balances[0], from_balances[1], to_balances[0], to_balances[1])
        else:
            # Process TO account first
            success, error_code, to_balances = self._process_to_account(
                to_sortcode, to_account, amount
            )
            if not success:
                return False, error_code, None

            success, error_code, from_balances = self._process_from_account(
                from_sortcode, from_account, amount
            )
            if not success:
                self._rollback_transaction()
                return False, error_code, None

            # Record successful transaction
            self._record_transaction(
                from_sortcode, from_account, to_sortcode, to_account, amount
            )

            return True, None, (from_balances[0], from_balances[1], to_balances[0], to_balances[1])

    def _process_from_account(
        self, sortcode: str, account_number: str, amount: float
    ) -> Tuple[bool, Optional[ErrorCode], Optional[Tuple[float, float]]]:
        """Process the FROM account for a transfer"""
        try:
            # Read the account record with exclusive lock
            account = self._read_account(sortcode, account_number, lock=True)

            if not account:
                return False, ErrorCode.FROM_ACCOUNT_NOT_FOUND, None

            # Update balances
            account.available_balance -= amount
            account.actual_balance -= amount

            # Write the updated account record
            success = self._update_account(account)
            if not success:
                return False, ErrorCode.FROM_ACCOUNT_UPDATE_FAILED, None

            return True, None, (account.available_balance, account.actual_balance)

        except Exception as e:
            self.logger.error(f"Error processing FROM account: {str(e)}")
            return False, ErrorCode.DB2_ERROR, None

    def _process_to_account(
        self, sortcode: str, account_number: str, amount: float
    ) -> Tuple[bool, Optional[ErrorCode], Optional[Tuple[float, float]]]:
        """Process the TO account for a transfer"""
        try:
            # Read the account record with exclusive lock
            account = self._read_account(sortcode, account_number, lock=True)

            if not account:
                return False, ErrorCode.TO_ACCOUNT_NOT_FOUND, None

            # Update balances
            account.available_balance += amount
            account.actual_balance += amount

            # Write the updated account record
            success = self._update_account(account)
            if not success:
                return False, ErrorCode.TO_ACCOUNT_UPDATE_FAILED, None

            return True, None, (account.available_balance, account.actual_balance)

        except Exception as e:
            self.logger.error(f"Error processing TO account: {str(e)}")
            return False, ErrorCode.DB2_ERROR, None

    def _read_account(self, sortcode: str, account_number: str, lock: bool = False) -> Optional[AccountData]:
        """
        Read an account record from the database.
        Implements VSAM READ UPDATE locking when lock=True.
        """
        # In a real implementation, this would connect to a database
        # For this example, we'll simulate the operation
        try:
            # Simulate database read with optional lock
            if lock:
                # Acquire exclusive lock (would be implemented by the database)
                pass

            # In a real implementation, this would execute a SELECT query
            # For this example, we'll return a mock account
            return AccountData(
                eyecatcher="0",
                customer_number="1234567890",
                sortcode=sortcode,
                account_number=account_number,
                account_type="CURRENT",
                interest_rate=0.0,
                opened_date="2023-01-01",
                overdraft_limit=0,
                last_statement="2023-01-01",
                next_statement="2023-02-01",
                available_balance=1000.00,
                actual_balance=1000.00
            )
        except Exception as e:
            self.logger.error(f"Database read error: {str(e)}")
            return None

    def _update_account(self, account: AccountData) -> bool:
        """Update an account record in the database"""
        # In a real implementation, this would execute an UPDATE query
        # For this example, we'll simulate the operation
        try:
            # Simulate database update
            return True
        except Exception as e:
            self.logger.error(f"Database update error: {str(e)}")
            return False

    def _rollback_transaction(self):
        """Rollback a transaction in case of failure"""
        # In a real implementation, this would execute a ROLLBACK
        # For this example, we'll simulate the operation
        try:
            # Simulate transaction rollback
            pass
        except Exception as e:
            self.logger.error(f"Transaction rollback error: {str(e)}")
            raise

    def _record_transaction(
        self,
        from_sortcode: str,
        from_account: str,
        to_sortcode: str,
        to_account: str,
        amount: float
    ) -> bool:
        """Record a successful transaction in the PROCTRAN table"""
        try:
            # Get current date and time
            now = datetime.datetime.now()
            date_str = now.strftime("%Y.%m.%d")
            time_str = now.strftime("%H:%M:%S")

            # Create transaction record
            transaction = TransactionData(
                eyecatcher="PRTR",
                sortcode=from_sortcode,
                account_number=from_account,
                date=date_str,
                time=time_str,
                reference=str(now.timestamp()).replace(".", "")[:12],
                transaction_type="XFR",
                description=f"Transfer to {to_sortcode}/{to_account}",
                amount=amount
            )

            # In a real implementation, this would execute an INSERT query
            # For this example, we'll simulate the operation
            return True

        except Exception as e:
            self.logger.error(f"Error recording transaction: {str(e)}")
            return False