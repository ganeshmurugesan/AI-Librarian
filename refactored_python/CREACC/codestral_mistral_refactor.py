import datetime
from dataclasses import dataclass
from typing import Optional, Tuple
import logging
from enum import Enum

class ErrorCode(Enum):
    CUSTOMER_NOT_FOUND = 1
    ACCOUNT_TYPE_INVALID = 2
    ENQUEUE_FAILED = 3
    DECREMENT_FAILED = 4
    DEQUEUE_FAILED = 5
    ACCOUNT_COUNT_FAILED = 6
    DB2_INSERT_FAILED = 7
    TOO_MANY_ACCOUNTS = 8

@dataclass
class Account:
    eyecatcher: str
    customer_number: str
    sortcode: str
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
class Proctran:
    eyecatcher: str
    sortcode: str
    account_number: str
    date: str
    time: str
    reference: str
    transaction_type: str
    description: str
    amount: float

class AccountCreator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sortcode = "123456"  # Example sortcode, should be configured properly

    def create_account(self, customer_number: str, account_type: str,
                       interest_rate: float, overdraft_limit: int,
                       available_balance: float, actual_balance: float) -> Tuple[bool, Optional[ErrorCode], Optional[Account]]:
        """
        Creates a new account with the given parameters.

        Args:
            customer_number: The customer number
            account_type: Type of account (ISA, MORTGAGE, etc.)
            interest_rate: Interest rate for the account
            overdraft_limit: Overdraft limit
            available_balance: Available balance
            actual_balance: Actual balance

        Returns:
            Tuple of (success: bool, error_code: Optional[ErrorCode], account: Optional[Account])
        """
        try:
            # Validate customer exists (simplified for example)
            if not self._validate_customer(customer_number):
                return False, ErrorCode.CUSTOMER_NOT_FOUND, None

            # Validate account type
            if not self._validate_account_type(account_type):
                return False, ErrorCode.ACCOUNT_TYPE_INVALID, None

            # Get next account number with locking
            account_number = self._get_next_account_number()
            if not account_number:
                return False, ErrorCode.ACCOUNT_COUNT_FAILED, None

            # Calculate dates
            opened_date, last_stmt_date, next_stmt_date = self._calculate_dates()

            # Create account record
            account = Account(
                eyecatcher="ACCT",
                customer_number=customer_number,
                sortcode=self.sortcode,
                account_number=account_number,
                account_type=account_type,
                interest_rate=interest_rate,
                opened=opened_date,
                overdraft_limit=overdraft_limit,
                last_statement=last_stmt_date,
                next_statement=next_stmt_date,
                available_balance=available_balance,
                actual_balance=actual_balance
            )

            # Write to database
            if not self._write_account_to_db(account):
                self._rollback_account_number()
                return False, ErrorCode.DB2_INSERT_FAILED, None

            # Write to proctran
            if not self._write_proctran(account):
                self._rollback_account_number()
                return False, ErrorCode.DB2_INSERT_FAILED, None

            return True, None, account

        except Exception as e:
            self.logger.error(f"Error creating account: {str(e)}")
            return False, ErrorCode.DB2_INSERT_FAILED, None

    def _validate_customer(self, customer_number: str) -> bool:
        """Validate that the customer exists (simplified for example)"""
        # In a real implementation, this would query the database
        return True

    def _validate_account_type(self, account_type: str) -> bool:
        """Validate the account type"""
        valid_types = {"ISA", "MORTGAGE", "SAVING", "CURRENT", "LOAN"}
        return account_type.upper() in valid_types

    def _get_next_account_number(self) -> Optional[str]:
        """
        Get the next account number with proper locking.
        Implements the equivalent of VSAM READ UPDATE locking.
        """
        try:
            # In a real implementation, this would use database transactions
            # with proper locking to ensure atomicity
            last_account_number = self._get_last_account_number()
            if last_account_number is None:
                return None

            new_account_number = str(int(last_account_number) + 1).zfill(8)
            self._update_last_account_number(new_account_number)
            return new_account_number
        except Exception as e:
            self.logger.error(f"Error getting next account number: {str(e)}")
            return None

    def _get_last_account_number(self) -> Optional[str]:
        """Get the last account number from the control table"""
        # Simplified - in a real implementation this would query the database
        return "00000001"

    def _update_last_account_number(self, new_number: str) -> bool:
        """Update the last account number in the control table"""
        # Simplified - in a real implementation this would update the database
        return True

    def _rollback_account_number(self) -> None:
        """Rollback the account number counter"""
        # Simplified - in a real implementation this would decrement the counter
        pass

    def _calculate_dates(self) -> Tuple[str, str, str]:
        """Calculate the account dates"""
        today = datetime.date.today()
        opened_date = today.strftime("%d.%m.%Y")

        # Last statement date is today
        last_stmt_date = opened_date

        # Next statement date is today + 30 days
        next_stmt_date = (today + datetime.timedelta(days=30)).strftime("%d.%m.%Y")

        return opened_date, last_stmt_date, next_stmt_date

    def _write_account_to_db(self, account: Account) -> bool:
        """Write the account to the database"""
        # Simplified - in a real implementation this would use proper database access
        try:
            # Example DB2 insert (simplified)
            # EXEC SQL INSERT INTO ACCOUNT (...) VALUES (...)
            return True
        except Exception as e:
            self.logger.error(f"Error writing account to DB: {str(e)}")
            return False

    def _write_proctran(self, account: Account) -> bool:
        """Write the transaction to the proctran table"""
        # Simplified - in a real implementation this would use proper database access
        try:
            # Example DB2 insert (simplified)
            # EXEC SQL INSERT INTO PROCTRAN (...) VALUES (...)
            return True
        except Exception as e:
            self.logger.error(f"Error writing to proctran: {str(e)}")
            return False