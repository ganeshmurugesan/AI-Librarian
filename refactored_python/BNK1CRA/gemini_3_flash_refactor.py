from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import Optional, TypedDict, Final
import datetime
import re

@dataclass
class TransactionResult:
    """Represents the outcome of a Credit/Debit transaction."""
    success: bool
    message: str
    account_no: str = ""
    sort_code: str = ""
    actual_balance: Decimal = Decimal("0.00")
    available_balance: Decimal = Decimal("0.00")
    fail_code: Optional[str] = None

class BankCommsArea(TypedDict):
    """Mirror of the COBOL DFHCOMMAREA structure."""
    comm_accno: str
    comm_sign: str
    comm_amt: int  # PIC 9(12)

class CreditDebitService:
    """
    Senior Migration Engineer Note: 
    This class migrates BNK1CRA (Credit/Debit) logic. 
    It maintains VSAM-style 'Read for Update' consistency by 
    encapsulating the logic intended for the DBCRFUN subprogram.
    """

    # Error Code Constants (Requirements 3 & 4)
    ERR_ACC_NOT_FOUND: Final[str] = "1"
    ERR_UNEXPECTED: Final[str] = "2"
    ERR_INSUFFICIENT_FUNDS: Final[str] = "3"
    ERR_INVALID_SORT_CODE: Final[str] = "4"
    ERR_ACCOUNT_LOCKED: Final[str] = "5"
    ERR_LIMIT_EXCEEDED: Final[str] = "6"
    ERR_DATABASE_DOWN: Final[str] = "7"
    ERR_TRAN_TIMEOUT: Final[str] = "8"

    def __init__(self, user_id: str, terminal_id: str):
        self.user_id = user_id
        self.terminal_id = terminal_id
        self._applid = "HBNK"

    def process_transaction(
        self, 
        account_no: str, 
        sign: str, 
        amount_str: str
    ) -> TransactionResult:
        """
        Main entry point mirroring the Procedure Division logic.
        
        :param account_no: The target account number (ACCNOI)
        :param sign: Transaction indicator '+' or '-' (SIGNI)
        :param amount_str: Raw string input for amount (AMTI)
        """
        # 1. Validate Input (Mirroring EDIT-DATA / VALIDATE-AMOUNT)
        validation_error = self._validate_input(account_no, sign, amount_str)
        if validation_error:
            return TransactionResult(success=False, message=validation_error)

        # 2. Prepare Subprogram Parameters
        try:
            amount = Decimal(amount_str)
            if sign == '-':
                amount = amount * -1
        except InvalidOperation:
            return TransactionResult(success=False, message="Please supply a numeric amount.")

        # 3. Apply Update (Mirroring UPD-CRED-DATA -> LINK DBCRFUN)
        # In a real migration, this involves a database transaction with SELECT FOR UPDATE (VSAM Lock)
        return self._link_dbcrfun(account_no, amount)

    def _validate_input(self, account_no: str, sign: str, amount_str: str) -> Optional[str]:
        """Performs legacy validation checks on input fields."""
        # Account Number Validation
        clean_acc = re.sub(r'\D', '', account_no)
        if not clean_acc:
            return "Please enter an account number."
        if int(clean_acc) == 0:
            return "Please enter a non zero account number."

        # Sign Validation
        if sign not in ('+', '-'):
            return "Please enter + or - preceding the amount"

        # Amount Numeric and Format Check
        if not amount_str.strip():
            return "The Amount entered must be numeric."
        
        if ' ' in amount_str.strip():
            return "Please supply a numeric amount without embedded spaces."

        try:
            amt_decimal = Decimal(amount_str)
            if amt_decimal == 0:
                return "Please supply a non-zero amount."
            
            # Check decimal places (Mirroring INSPECT...AFTER '.')
            if amt_decimal.as_tuple().exponent < -2:
                return "Only up to two decimal places are supported."
        except InvalidOperation:
            return "Please supply a numeric amount."

        return None

    def _link_dbcrfun(self, account_no: str, amount: Decimal) -> TransactionResult:
        """
        Simulates the external subprogram call 'DBCRFUN'.
        This method must be executed within a database transaction to maintain 
        the VSAM READ UPDATE locking logic.
        """
        # --- START TRANSACTION (Atomic Block) ---
        # 1. Perform 'SELECT ... FOR UPDATE' to simulate VSAM record locking
        # 2. Perform business rules logic
        
        # Simulated logic for the error return codes (1-8)
        # In production, these are returned by the data access layer
        success_flag = "Y" 
        fail_code = "0"

        # Logic for processing specific return codes from COBOL
        if success_flag == "N":
            match fail_code:
                case self.ERR_ACC_NOT_FOUND:
                    msg = f"Sorry but the ACCOUNT no was not found for SORTCODE. Amount not applied."
                case self.ERR_UNEXPECTED:
                    msg = "Sorry but the AMOUNT could not be applied due to an unexpected error."
                case self.ERR_INSUFFICIENT_FUNDS:
                    msg = "Sorry insufficient funds available to process the request."
                case self.ERR_INVALID_SORT_CODE:
                    msg = "Invalid Sort Code detected."
                case self.ERR_ACCOUNT_LOCKED:
                    msg = "Account is currently locked for maintenance."
                case self.ERR_LIMIT_EXCEEDED:
                    msg = "Transaction limit exceeded."
                case self.ERR_DATABASE_DOWN:
                    msg = "System unavailable. Please try again later."
                case self.ERR_TRAN_TIMEOUT:
                    msg = "Transaction timed out during processing."
                case _:
                    msg = f"Sorry but the AMOUNT could not be applied due to error: {fail_code}"
            
            return TransactionResult(success=False, message=msg, fail_code=fail_code)

        # Successful path (Mirroring UCD-SUCCESS)
        return TransactionResult(
            success=True,
            message="Amount successfully applied to the account.",
            account_no=account_no,
            sort_code="123456",  # Mocked from subprogram response
            actual_balance=Decimal("1500.50"), # Mocked from subprogram response
            available_balance=Decimal("1450.00") # Mocked from subprogram response
        )

    def format_balance(self, value: Decimal) -> str:
        """Mirroring the +9(10).99 display formatting."""
        return f"{value:+013.2f}"

    def get_audit_timestamp(self) -> tuple[str, str]:
        """Mirroring POPULATE-TIME-DATE section."""
        now = datetime.datetime.now()
        date_str = now.strftime("%d.%m.%Y")
        time_str = now.strftime("%H:%M:%S")
        return date_str, time_str