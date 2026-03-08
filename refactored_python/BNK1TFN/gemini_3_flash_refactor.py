from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Final
from enum import IntEnum
import threading

class TransferErrorCode(IntEnum):
    """Specific error return codes as defined in the legacy system."""
    SUCCESS = 0
    FROM_ACCOUNT_NOT_FOUND = 1
    TO_ACCOUNT_NOT_FOUND = 2
    UNEXPECTED_ERROR = 3
    INVALID_AMOUNT_ZERO_OR_LESS = 4
    INSUFFICIENT_FUNDS = 5  # Extension for logic 5-8
    ACCOUNT_LOCKED = 6
    TRANSACTION_LIMIT_EXCEEDED = 7
    DATABASE_CONNECTION_FAIL = 8

@dataclass
class TransferState:
    """Represents the COBOL BNK1TFM Map and COMMAREA state."""
    from_acc: str = ""
    to_acc: str = ""
    amount_str: str = ""
    message: str = ""
    from_sort_code: str = ""
    to_sort_code: str = ""
    from_actual_bal: Decimal = Decimal("0.00")
    from_avail_bal: Decimal = Decimal("0.00")
    to_actual_bal: Decimal = Decimal("0.00")
    to_avail_bal: Decimal = Decimal("0.00")
    valid_data: bool = True
    send_alarm: bool = False

class FundTransferService:
    """
    Service to handle fund transfers between accounts.
    Migrated from BNK1TFN (COBOL/CICS).
    
    Maintains legacy business logic including validation rules and 
    simulates VSAM READ UPDATE locking for thread-safe operations.
    """

    # Global lock to simulate VSAM exclusive control during READ UPDATE
    # In a distributed environment, this would be a row-level DB lock.
    _vsam_lock: Final[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        self.state = TransferState()

    def process_transaction(self, input_data: Dict[str, Any]) -> TransferState:
        """
        Main entry point equivalent to Procedure Division A010/PROCESS-MAP.
        
        Args:
            input_data: Dictionary containing raw map input (FACCNOI, TACCNOI, AMTI).
        """
        self.state.from_acc = str(input_data.get("FACCNOI", "")).strip()
        self.state.to_acc = str(input_data.get("TACCNOI", "")).strip()
        self.state.amount_str = str(input_data.get("AMTI", "")).strip()

        if not self._validate_input():
            self.state.send_alarm = True
            return self.state

        error_code = self._execute_transfer()
        self._handle_result(error_code)
        
        return self.state

    def _validate_input(self) -> bool:
        """Equivalent to EDIT-DATA and VALIDATE-AMOUNT sections."""
        # Check if numeric
        if not (self.state.from_acc.isdigit() and self.state.to_acc.isdigit()):
            self.state.message = "Please enter numeric account numbers."
            return False

        # Legacy logic: Account '00000000' is invalid
        if self.state.from_acc == "00000000" or self.state.to_acc == "00000000":
            self.state.message = "Account no 00000000 is not valid."
            return False

        # Legacy logic: From and To must be different
        if self.state.from_acc == self.state.to_acc:
            self.state.message = "The FROM & TO account should be different."
            return False

        # Amount validation (Equivalent to VALIDATE-AMOUNT)
        try:
            # Clean embedded spaces as per legacy unstring logic
            clean_amt = self.state.amount_str.replace(" ", "")
            amount = Decimal(clean_amt)
            
            if amount <= 0:
                self.state.message = "Please supply a positive amount."
                return False
            
            # Check decimal places (max 2 supported)
            if abs(amount.as_tuple().exponent) > 2: # type: ignore
                self.state.message = "Only up to two decimal places are supported."
                return False
                
        except (InvalidOperation, ValueError):
            self.state.message = "The Amount entered must be numeric."
            return False

        return True

    def _execute_transfer(self) -> TransferErrorCode:
        """
        Equivalent to GET-ACC-DATA / EXEC CICS LINK PROGRAM('XFRFUN').
        Implements VSAM READ UPDATE locking logic.
        """
        amount = Decimal(self.state.amount_str.replace(" ", ""))

        # Critical Section: Simulate VSAM READ UPDATE exclusive control
        with self._vsam_lock:
            try:
                # 1. READ FROM-ACCOUNT WITH UPDATE (Locking)
                # 2. READ TO-ACCOUNT WITH UPDATE (Locking)
                # Note: In Python, we simulate the XFRFUN return codes (1-8)
                
                # Logic simulating account lookup (Codes 1 & 2)
                if not self._account_exists(self.state.from_acc):
                    return TransferErrorCode.FROM_ACCOUNT_NOT_FOUND
                
                if not self._account_exists(self.state.to_acc):
                    return TransferErrorCode.TO_ACCOUNT_NOT_FOUND

                # Logic simulating core transfer (XFRFUN)
                # In a real migration, this would involve a DB transaction
                success = self._perform_db_update(
                    self.state.from_acc, 
                    self.state.to_acc, 
                    amount
                )

                if success:
                    return TransferErrorCode.SUCCESS
                else:
                    return TransferErrorCode.UNEXPECTED_ERROR

            except Exception:
                return TransferErrorCode.UNEXPECTED_ERROR

    def _handle_result(self, code: TransferErrorCode) -> None:
        """Maps return codes to UI messages equivalent to GCD010 EVALUATE."""
        match code:
            case TransferErrorCode.SUCCESS:
                self.state.message = "Transfer successfully applied."
                # Simulate populating balance display fields
                self._populate_balances()
            case TransferErrorCode.FROM_ACCOUNT_NOT_FOUND:
                self.state.message = "Sorry the FROM ACCOUNT no was not found. Transfer not applied."
            case TransferErrorCode.TO_ACCOUNT_NOT_FOUND:
                self.state.message = "Sorry the TO ACCOUNT no was not found. Transfer not applied."
            case TransferErrorCode.INVALID_AMOUNT_ZERO_OR_LESS:
                self.state.message = "Please supply an amount greater than zero."
            case TransferErrorCode.UNEXPECTED_ERROR:
                self.state.message = "Sorry but the transfer could not be applied due to an unexpected error."
            case _:
                self.state.message = f"Transfer failed with error code: {code.value}"

    def _account_exists(self, account_no: str) -> bool:
        """Mock account lookup logic."""
        return True

    def _perform_db_update(self, f_acc: str, t_acc: str, amt: Decimal) -> bool:
        """Mock database update logic."""
        return True

    def _populate_balances(self) -> None:
        """Simulates the mapping of SUBPGM fields to Map output fields."""
        # Mocking balance retrieval after transfer
        self.state.from_actual_bal = Decimal("1000.00").quantize(Decimal("0.01"))
        self.state.from_avail_bal = Decimal("950.00").quantize(Decimal("0.01"))
        self.state.to_actual_bal = Decimal("500.00").quantize(Decimal("0.01"))
        self.state.to_avail_bal = Decimal("500.00").quantize(Decimal("0.01"))
        self.state.from_sort_code = "102030"
        self.state.to_sort_code = "405060"

if __name__ == "__main__":
    # Example usage mirroring a CICS transaction invocation
    service = FundTransferService()
    test_input = {
        "FACCNOI": "12345678",
        "TACCNOI": "87654321",
        "AMTI": "150.50"
    }
    result = service.process_transaction(test_input)
    print(f"Message: {result.message}")
    print(f"From Balance: {result.from_actual_bal}")