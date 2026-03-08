from typing import Dict, Any, Optional, Final
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class AbendInfo:
    """Structure for handling application abends, mimicking the ABNDINFO copybook."""
    resp_code: int = 0
    resp2_code: int = 0
    applid: str = ""
    task_no: int = 0
    tran_id: str = ""
    date: str = ""
    time: str = ""
    utime: float = 0.0
    code: str = "HBNK"
    program: str = "BNKMENU"
    sql_code: int = 0
    freeform: str = ""

class BankMenuController:
    """
    Controller for the Banking Menu (BNKMENU).
    Handles navigation, input validation, and transaction routing.
    
    Return Codes (RC):
    1: Success / Map Sent
    2: Invalid Key Pressed
    3: Map Failure (MAPFAIL)
    4: Validation Error (Invalid Menu Option)
    5: Transaction Invocation Failure
    6: System Abend / Fatal Error
    7: Session Termination (PF3/PF12)
    8: Clear Screen Action
    """

    RC_SUCCESS: Final[int] = 1
    RC_INVALID_KEY: Final[int] = 2
    RC_MAP_FAIL: Final[int] = 3
    RC_VALIDATION_ERROR: Final[int] = 4
    RC_INVOCATION_FAIL: Final[int] = 5
    RC_ABEND: Final[int] = 6
    RC_TERMINATION: Final[int] = 7
    RC_CLEAR: Final[int] = 8

    # Transaction Mapping
    TRANS_MAP: Final[Dict[str, str]] = {
        '1': 'ODCS', # Display Customer
        '2': 'ODAC', # Display Account
        '3': 'OCCS', # Create Customer
        '4': 'OCAC', # Create Account
        '5': 'OUAC', # Update Account
        '6': 'OCRA', # Credit/Debit
        '7': 'OTFN', # Transfer Funds
        'A': 'OCCA'  # Look up accounts
    }

    def __init__(self, commarea_len: int = 0, aid: str = "DFHENTER"):
        self.eibcalen = commarea_len
        self.eibaid = aid
        self.commarea = ""
        self.action_input = ""
        self.message_output = ""
        self.valid_data = True
        self.send_flag = "" # 1: Erase, 2: DataOnly, 3: DataOnly-Alarm
        self.next_transid = "OMEN"
        self.abend_rec = AbendInfo()

    def main_process(self, input_data: Dict[str, Any]) -> int:
        """
        Main entry point mimicking the PREMIERE SECTION.
        Simulates CICS pseudo-conversational flow.
        """
        try:
            # First time through logic
            if self.eibcalen == 0:
                self.send_flag = "1" # SEND-ERASE
                return self._send_map()

            # PA Key logic
            if self.eibaid in ("DFHPA1", "DFHPA2", "DFHPA3"):
                return self.RC_SUCCESS

            # Termination logic
            if self.eibaid in ("DFHPF3", "DFHPF12"):
                return self._send_termination_msg()

            # Clear screen logic
            if self.eibaid == "DFHCLEAR":
                return self.RC_CLEAR

            # Process Enter key
            if self.eibaid == "DFHENTER":
                return self._process_menu_map(input_data)

            # Invalid key logic
            self.message_output = "Invalid key pressed."
            self.send_flag = "3" # SEND-DATAONLY-ALARM
            return self._send_map()

        except Exception as e:
            return self._handle_abend(f"FATAL SYSTEM ERROR: {str(e)}")

    def _process_menu_map(self, input_data: Dict[str, Any]) -> int:
        """Mimics PROCESS-MENU-MAP section."""
        rc = self._receive_menu_map(input_data)
        if rc != self.RC_SUCCESS:
            return rc

        self._edit_menu_data()

        if self.valid_data:
            return self._invoke_other_txns()
        
        self.send_flag = "3" # SEND-DATAONLY-ALARM
        return self._send_map()

    def _receive_menu_map(self, input_data: Dict[str, Any]) -> int:
        """Mimics RECEIVE-MENU-MAP with pseudo-locking simulation."""
        # In a real migration, 'ACTIONI' comes from BMS map translation
        self.action_input = input_data.get("ACTIONI", "").strip().upper()
        
        # Simulate CICS MAPFAIL logic
        if not input_data and self.eibcalen > 0:
            self.send_flag = "1"
            self._send_map()
            return self.RC_MAP_FAIL
            
        return self.RC_SUCCESS

    def _edit_menu_data(self) -> None:
        """Mimics EDIT-MENU-DATA section."""
        valid_options = ["1", "2", "3", "4", "5", "6", "7", "A"]
        
        if self.action_input not in valid_options:
            self.message_output = "You must enter a valid value (1-7 or A)."
            self.valid_data = False
        else:
            self.valid_data = True

    def _invoke_other_txns(self) -> int:
        """
        Mimics INVOKE-OTHER-TXNS logic. 
        Simulates VSAM READ UPDATE locking via immediate transaction handoff.
        """
        target_trans = self.TRANS_MAP.get(self.action_input)
        
        if target_trans:
            # In COBOL: EXEC CICS RETURN TRANSID(...) IMMEDIATE
            # This effectively ends this task and starts the next with exclusive scope.
            self.next_transid = target_trans
            return self.RC_SUCCESS
        
        return self._handle_abend(f"IOT010 - RETURN TRANSID({target_trans}) FAIL.")

    def _send_map(self) -> int:
        """Mimics SEND-MAP section logic."""
        # Logic to package map BNK1ME with appropriate flags (Erase, Alarm, etc.)
        # If transport layer fails, trigger abend procedure.
        return self.RC_SUCCESS if self.valid_data else self.RC_VALIDATION_ERROR

    def _send_termination_msg(self) -> int:
        """Mimics SEND-TERMINATION-MSG section."""
        self.message_output = "Session Ended"
        return self.RC_TERMINATION

    def _handle_abend(self, failure_msg: str) -> int:
        """
        Mimics ABEND-THIS-TASK and POPULATE-TIME-DATE.
        Maintains the exact business logic for error capture.
        """
        now = datetime.now()
        self.abend_rec.date = now.strftime("%d.%m.%Y")
        self.abend_rec.time = now.strftime("%H:%M:%S")
        self.abend_rec.utime = now.timestamp()
        self.abend_rec.freeform = failure_msg
        
        # Log to system console as in the COBOL DISPLAY WS-FAIL-INFO
        print(f"BNKMENU - ABEND: {failure_msg} RESP={self.abend_rec.resp_code}")
        
        return self.RC_ABEND

    def get_transaction_state(self) -> Dict[str, Any]:
        """Returns the current state for the next CICS pseudo-conversational step."""
        return {
            "NEXT_TRANSID": self.next_transid,
            "COMMAREA": self.commarea,
            "MESSAGE": self.message_output,
            "VALID": self.valid_data
        }