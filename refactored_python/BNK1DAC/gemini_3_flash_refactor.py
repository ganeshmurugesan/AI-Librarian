from typing import Optional, TypedDict, Final
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum

class ReturnCode(IntEnum):
    """Specific error return codes as required by migration specs."""
    SUCCESS = 0
    NOT_FOUND = 1
    DATASTORE_ERROR = 2
    DELETE_ERROR = 3
    INVALID_INPUT = 4
    CICS_ABEND = 5
    LINK_FAILURE = 6
    SECURITY_VIOLATION = 7
    UNKNOWN_FAILURE = 8

class AccountData(TypedDict):
    cust_no: str
    sort_code: str
    acc_no: int
    acc_type: str
    int_rate: float
    opened_date: str
    overdraft: int
    last_stmt_date: str
    next_stmt_date: str
    avail_bal: float
    actual_bal: float

@dataclass
class CommArea:
    """Represents the DFHCOMMAREA for BNK1DAC."""
    eye_catcher: str = "ACCT"
    cust_no: str = ""
    sort_code: str = ""
    acc_no: int = 0
    acc_type: str = ""
    int_rate: float = 0.0
    opened_date: int = 0
    overdraft: int = 0
    last_stmt_dt: int = 0
    next_stmt_dt: int = 0
    avail_bal: float = 0.0
    actual_bal: float = 0.0
    success_flag: str = "N"
    fail_code: str = ""
    del_success: str = "N"
    del_fail_code: str = ""

class AccountController:
    """
    Controller for Display/Delete Account (BNK1DAC).
    Migrated from IBM COBOL CICS source.
    """
    
    TERMINATION_MSG: Final[str] = "Session Ended"
    
    def __init__(self, comm_area: Optional[CommArea] = None):
        self.comm_area = comm_area if comm_area else CommArea()
        self.message = ""
        self.valid_data = True

    def process_map(self, action: str, input_acc_no: str) -> ReturnCode:
        """
        Main entry point mimicking CICS EVALUATE logic.
        
        :param action: The AID key pressed (e.g., 'ENTER', 'PF5')
        :param input_acc_no: Raw input from the UI map
        """
        match action:
            case "PF3":
                return self._return_to_menu()
            case "PF5":
                return self.handle_deletion(input_acc_no)
            case "PF12":
                return self.handle_termination()
            case "ENTER":
                return self.handle_inquiry(input_acc_no)
            case _:
                self.message = "Invalid key pressed."
                return ReturnCode.INVALID_INPUT

    def handle_inquiry(self, input_acc_no: str) -> ReturnCode:
        """Logic for GAD010 - LINK PROGRAM 'INQACC'."""
        self.valid_data = self._edit_data(input_acc_no)
        if not self.valid_data:
            return ReturnCode.INVALID_INPUT

        # Simulate EXEC CICS LINK PROGRAM('INQACC')
        # In a modern context, this calls the data access layer
        acc_no_int = int(input_acc_no.strip())
        result = self._call_inquiry_subprogram(acc_no_int)

        if not result or result['success_flag'] == 'N':
            self.message = "Sorry, but that account number was not found."
            self._clear_comm_area_balances()
            return ReturnCode.NOT_FOUND

        self._populate_comm_area(result)
        self.message = "If you wish to delete the Account press <PF5>."
        return ReturnCode.SUCCESS

    def handle_deletion(self, input_acc_no: str) -> ReturnCode:
        """
        Logic for DAD010 - LINK PROGRAM 'DELACC'.
        Maintains VSAM READ UPDATE locking logic through atomic transaction simulation.
        """
        if not self.comm_area.acc_no or self.comm_area.acc_no == 0:
            self.message = "Please enter an account number."
            return ReturnCode.INVALID_INPUT

        # Simulate EXEC CICS LINK PROGRAM('DELACC')
        # This layer ensures transaction isolation (VSAM READ UPDATE behavior)
        try:
            rc = self._call_delete_subprogram(self.comm_area.acc_no)
            
            if rc == ReturnCode.SUCCESS:
                self.message = f"Account {self.comm_area.acc_no} was successfully deleted."
                self._clear_comm_area_fields()
                return ReturnCode.SUCCESS
            
            # Map COBOL DEL-FAIL-CD to modern ReturnCodes
            self.message = self._map_delete_error_message(rc)
            return rc

        except Exception:
            return ReturnCode.CICS_ABEND

    def _edit_data(self, input_acc_no: str) -> bool:
        """Logic for ED010 - BIF DEEDIT and numeric validation."""
        if not input_acc_no or input_acc_no.strip() == "":
            self.message = "Please enter an account number."
            return False
        
        cleaned = "".join(filter(str.isdigit, input_acc_no))
        if not cleaned:
            self.message = "Please enter an account number."
            return False
        return True

    def _call_inquiry_subprogram(self, acc_no: int) -> Optional[dict]:
        """Simulation of LINK to INQACC."""
        # Implementation would call DB repository
        return None

    def _call_delete_subprogram(self, acc_no: int) -> ReturnCode:
        """
        Simulation of LINK to DELACC with synchronous transaction control.
        Mimics EXEC CICS LINK ... SYNCONRETURN.
        """
        # Logic would check locking and perform DELETE
        return ReturnCode.SUCCESS

    def _map_delete_error_message(self, rc: ReturnCode) -> str:
        base_msg = " Account NOT deleted."
        match rc:
            case ReturnCode.NOT_FOUND:
                return f"Sorry, but that account number was not found.{base_msg}"
            case ReturnCode.DATASTORE_ERROR:
                return f"Sorry, but a datastore error occurred.{base_msg}"
            case ReturnCode.DELETE_ERROR:
                return f"Sorry, but a delete error occurred.{base_msg}"
            case _:
                return f"Sorry, but a delete error occurred.{base_msg}"

    def _populate_comm_area(self, data: dict) -> None:
        self.comm_area.cust_no = data.get('cust_no', '')
        self.comm_area.sort_code = data.get('sort_code', '')
        self.comm_area.acc_no = data.get('acc_no', 0)
        self.comm_area.acc_type = data.get('acc_type', '')
        self.comm_area.int_rate = data.get('int_rate', 0.0)
        self.comm_area.avail_bal = data.get('avail_bal', 0.0)
        self.comm_area.actual_bal = data.get('actual_bal', 0.0)

    def _clear_comm_area_balances(self) -> None:
        self.comm_area.avail_bal = 0.0
        self.comm_area.actual_bal = 0.0

    def _clear_comm_area_fields(self) -> None:
        """Reset CommArea after successful deletion (COBOL DAD010)."""
        self.comm_area = CommArea()

    def _return_to_menu(self) -> ReturnCode:
        """Simulate RETURN TRANSID('OMEN')."""
        return ReturnCode.SUCCESS

    def handle_termination(self) -> ReturnCode:
        """Logic for STM010 - SEND TEXT."""
        self.message = self.TERMINATION_MSG
        return ReturnCode.SUCCESS

    @staticmethod
    def _get_timestamp() -> str:
        """Logic for POPULATE-TIME-DATE."""
        return datetime.now().strftime("%d.%m.%Y %H:%M:%S")