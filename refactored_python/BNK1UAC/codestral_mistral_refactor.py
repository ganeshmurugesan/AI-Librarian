from dataclasses import dataclass
from typing import Optional, Union, Tuple
from enum import Enum, auto
import logging
from datetime import datetime

class CICSResponse(Enum):
    NORMAL = auto()
    ERROR = auto()

class SendFlag(Enum):
    ERASE = 1
    DATAONLY = 2
    DATAONLY_ALARM = 3

class AccountUpdateError(Exception):
    """Base class for account update errors"""
    pass

class AccountUpdateErrorCode(Enum):
    INVALID_ACCOUNT_NUMBER = 1
    INVALID_ACCOUNT_TYPE = 2
    INVALID_INTEREST_RATE = 3
    INVALID_OVERDRAFT = 4
    INVALID_DATE_FORMAT = 5
    INVALID_DATE_VALUE = 6
    UPDATE_FAILED = 7
    SYSTEM_ERROR = 8

@dataclass
class AccountData:
    account_number: int
    customer_number: str
    sort_code: str
    account_type: str
    interest_rate: float
    opened_date: int
    overdraft: int
    last_statement_date: int
    next_statement_date: int
    available_balance: float
    actual_balance: float
    success: bool = False

class AccountUpdater:
    """
    Modern Python implementation of the COBOL BNK1UAC program.
    Handles account data updates with proper error handling and VSAM-like locking.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.valid_data = True
        self.send_flag = SendFlag.DATAONLY
        self.account_data: Optional[AccountData] = None
        self.error_code: Optional[AccountUpdateErrorCode] = None

    def process_map(self, input_data: dict) -> Tuple[dict, Optional[AccountUpdateErrorCode]]:
        """
        Process the input map data and perform appropriate actions based on the input.

        Args:
            input_data: Dictionary containing the input data from the map

        Returns:
            Tuple containing the output data and error code (if any)
        """
        self.valid_data = True
        output_data = {}

        if input_data.get('action') == 'enter':
            self._edit_data(input_data)
            if self.valid_data:
                self._inq_acc_data(input_data['account_number'])
                output_data = self._prepare_output_data()

        elif input_data.get('action') == 'pf5':
            self._validate_data(input_data)
            if self.valid_data:
                self._upd_acc_data(input_data)
                output_data = self._prepare_output_data()

        return output_data, self.error_code

    def _edit_data(self, input_data: dict) -> None:
        """Basic validation of input data"""
        if not str(input_data.get('account_number', '')).isdigit():
            self.valid_data = False
            self.error_code = AccountUpdateErrorCode.INVALID_ACCOUNT_NUMBER

    def _validate_data(self, input_data: dict) -> None:
        """Comprehensive validation of input data"""
        valid_account_types = {'CURRENT', 'SAVING', 'LOAN', 'MORTGAGE', 'ISA'}

        if input_data.get('account_type') not in valid_account_types:
            self.valid_data = False
            self.error_code = AccountUpdateErrorCode.INVALID_ACCOUNT_TYPE
            return

        interest_rate = input_data.get('interest_rate', '')
        if not interest_rate:
            self.valid_data = False
            self.error_code = AccountUpdateErrorCode.INVALID_INTEREST_RATE
            return

        # Validate interest rate format
        try:
            rate = float(interest_rate)
            if rate < 0 or rate > 9999.99:
                self.valid_data = False
                self.error_code = AccountUpdateErrorCode.INVALID_INTEREST_RATE
                return
        except ValueError:
            self.valid_data = False
            self.error_code = AccountUpdateErrorCode.INVALID_INTEREST_RATE
            return

        # Validate overdraft
        overdraft = input_data.get('overdraft', '')
        if not overdraft.isdigit():
            self.valid_data = False
            self.error_code = AccountUpdateErrorCode.INVALID_OVERDRAFT
            return

        # Validate dates
        date_fields = [
            ('last_statement_dd', 'last_statement_mm', 'last_statement_yy'),
            ('next_statement_dd', 'next_statement_mm', 'next_statement_yy')
        ]

        for dd_field, mm_field, yy_field in date_fields:
            dd = input_data.get(dd_field, '')
            mm = input_data.get(mm_field, '')
            yy = input_data.get(yy_field, '')

            if not (dd.isdigit() and mm.isdigit() and yy.isdigit()):
                self.valid_data = False
                self.error_code = AccountUpdateErrorCode.INVALID_DATE_FORMAT
                return

            try:
                day = int(dd)
                month = int(mm)
                year = int(yy)

                if month < 1 or month > 12 or day < 1 or day > 31:
                    self.valid_data = False
                    self.error_code = AccountUpdateErrorCode.INVALID_DATE_VALUE
                    return

                # Additional date validation for months with 30 days
                if month in [4, 6, 9, 11] and day > 30:
                    self.valid_data = False
                    self.error_code = AccountUpdateErrorCode.INVALID_DATE_VALUE
                    return

                # February validation
                if month == 2:
                    if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                        if day > 29:
                            self.valid_data = False
                            self.error_code = AccountUpdateErrorCode.INVALID_DATE_VALUE
                            return
                    else:
                        if day > 28:
                            self.valid_data = False
                            self.error_code = AccountUpdateErrorCode.INVALID_DATE_VALUE
                            return

            except ValueError:
                self.valid_data = False
                self.error_code = AccountUpdateErrorCode.INVALID_DATE_VALUE
                return

    def _inq_acc_data(self, account_number: int) -> None:
        """
        Simulate querying account data from VSAM.
        In a real implementation, this would interact with a database.
        """
        try:
            # Simulate VSAM READ UPDATE with locking
            with self._acquire_vsam_lock(account_number):
                # In a real implementation, this would query the database
                # For this example, we'll use mock data
                self.account_data = AccountData(
                    account_number=account_number,
                    customer_number="CUST123456",
                    sort_code="12-34-56",
                    account_type="CURRENT",
                    interest_rate=1.5,
                    opened_date=20200101,
                    overdraft=1000,
                    last_statement_date=20230601,
                    next_statement_date=20230701,
                    available_balance=5000.00,
                    actual_balance=5000.00
                )
        except Exception as e:
            self.logger.error(f"Error querying account data: {str(e)}")
            self.valid_data = False
            self.error_code = AccountUpdateErrorCode.SYSTEM_ERROR

    def _upd_acc_data(self, input_data: dict) -> None:
        """
        Simulate updating account data in VSAM.
        In a real implementation, this would interact with a database.
        """
        try:
            # Convert screen formats to proper numeric values
            available_balance = self._convert_screen_balance(input_data.get('available_balance', ''))
            actual_balance = self._convert_screen_balance(input_data.get('actual_balance', ''))

            # Simulate VSAM READ UPDATE with locking
            with self._acquire_vsam_lock(input_data['account_number']):
                # In a real implementation, this would update the database
                # For this example, we'll just update our mock data
                self.account_data = AccountData(
                    account_number=input_data['account_number'],
                    customer_number=input_data.get('customer_number', ''),
                    sort_code=input_data.get('sort_code', ''),
                    account_type=input_data.get('account_type', ''),
                    interest_rate=float(input_data.get('interest_rate', 0)),
                    opened_date=int(input_data.get('opened_date', 0)),
                    overdraft=int(input_data.get('overdraft', 0)),
                    last_statement_date=int(input_data.get('last_statement_date', 0)),
                    next_statement_date=int(input_data.get('next_statement_date', 0)),
                    available_balance=available_balance,
                    actual_balance=actual_balance,
                    success=True
                )
        except Exception as e:
            self.logger.error(f"Error updating account data: {str(e)}")
            self.valid_data = False
            self.error_code = AccountUpdateErrorCode.UPDATE_FAILED

    def _convert_screen_balance(self, balance_str: str) -> float:
        """Convert screen balance format to proper numeric value"""
        if not balance_str:
            return 0.0

        # Remove any non-numeric characters except for the decimal point and sign
        cleaned = ''.join(c for c in balance_str if c.isdigit() or c in ['.', '-'])

        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _prepare_output_data(self) -> dict:
        """Prepare the output data for display"""
        if not self.account_data:
            return {}

        # Convert dates to display format
        opened_date = str(self.account_data.opened_date)
        last_stmt_date = str(self.account_data.last_statement_date)
        next_stmt_date = str(self.account_data.next_statement_date)

        return {
            'account_number': self.account_data.account_number,
            'customer_number': self.account_data.customer_number,
            'sort_code': self.account_data.sort_code,
            'account_type': self.account_data.account_type,
            'interest_rate': f"{self.account_data.interest_rate:.2f}",
            'opened_date': opened_date,
            'overdraft': self.account_data.overdraft,
            'last_statement_date': last_stmt_date,
            'next_statement_date': next_stmt_date,
            'available_balance': f"{self.account_data.available_balance:.2f}",
            'actual_balance': f"{self.account_data.actual_balance:.2f}",
            'success': self.account_data.success
        }

    def _acquire_vsam_lock(self, account_number: int) -> 'VSAMLockContext':
        """
        Simulate acquiring a VSAM lock for the account.
        In a real implementation, this would use proper database locking mechanisms.
        """
        return VSAMLockContext(account_number)

class VSAMLockContext:
    """Context manager for simulating VSAM record locking"""

    def __init__(self, account_number: int):
        self.account_number = account_number
        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        self.logger.debug(f"Acquired VSAM lock for account {self.account_number}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.debug(f"Released VSAM lock for account {self.account_number}")
        if exc_type is not None:
            self.logger.error(f"Error during VSAM operation: {exc_val}")
            raise AccountUpdateError(f"VSAM operation failed: {exc_val}") from exc_val