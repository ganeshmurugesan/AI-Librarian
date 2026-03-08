from typing import Dict, List, Optional, Any, Final
from dataclasses import dataclass, field
import datetime

@dataclass
class InqAccCuCommaArea:
    """Represents the INQACCCU COMMAREA structure."""
    customer_number: str = ""
    number_of_accounts: int = 0
    customer_found: str = "N"
    comm_success: str = "N"
    accounts: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "scode": "",
            "acc_no": "",
            "acc_type": "",
            "avail_bal": 0.0,
            "actual_bal": 0.0
        } for _ in range(20)
    ])

@dataclass
class Bnk1accMap:
    """Represents the BNK1ACC Map I/O structure."""
    cust_no: str = ""
    message: str = ""
    accounts: List[str] = field(default_factory=lambda: [""] * 10)
    cursor_pos: int = 0

class Bnk1ccaHandler:
    """
    Senior Software Engineer Implementation: BNK1CCA Legacy Migration.
    Handles account listing for specific customers with CICS-equivalent logic.
    
    Return Codes:
    1 - SUCCESS: Map processed and data returned
    2 - NOT FOUND: Customer record does not exist
    3 - NO ACCOUNTS: Customer exists but has no accounts
    4 - INVALID INPUT: Numeric validation failed
    5 - SYSTEM ERROR: External program link failure (CICS LINK equivalent)
    6 - MAP ERROR: Screen I/O failure
    7 - TERMINATE: Session termination (PF12/AID)
    8 - NAVIGATE: Return to main menu (PF3)
    """

    # Constants for keys (EIB-equivalent)
    DFHENTER: Final[str] = "ENTER"
    DFHPF3: Final[str] = "PF3"
    DFHPF12: Final[str] = "PF12"
    DFHCLEAR: Final[str] = "CLEAR"
    DFHPA: Final[set] = {"PA1", "PA2", "PA3"}

    def __init__(self, commarea: Dict[str, Any]):
        self.ws_comm_area = commarea
        self.map_data = Bnk1accMap()
        self.valid_data = True
        self.send_type = "ERASE"  # Default behavior
        self.inq_commarea = InqAccCuCommaArea()

    def process_request(self, eib_aid: str, eib_calen: int, map_input: Dict[str, Any]) -> tuple[int, Bnk1accMap]:
        """
        Main entry point mimicking the PROCEDURE DIVISION EVALUATE logic.
        """
        # First time through
        if eib_calen == 0:
            self.map_data = Bnk1accMap(cursor_pos=-1)
            self.send_type = "ERASE"
            return 1, self.map_data

        # Handle Functional Keys
        if eib_aid in self.DFHPA:
            return 1, self.map_data
        
        if eib_aid == self.DFHPF3:
            # RETURN TRANSID('OMEN') equivalent
            return 8, self.map_data

        if eib_aid == self.DFHPF12:
            self.map_data.message = "Session Ended"
            return 7, self.map_data

        if eib_aid == self.DFHCLEAR:
            # SEND CONTROL ERASE equivalent
            return 1, Bnk1accMap()

        if eib_aid == self.DFHENTER:
            return self._handle_process_map(map_input)

        # Other keys (Invalid key)
        self.map_data = Bnk1accMap()
        self.map_data.message = "Invalid key pressed."
        self.map_data.cursor_pos = -1
        self.send_type = "DATAONLY_ALARM"
        return 1, self.map_data

    def _handle_process_map(self, map_input: Dict[str, Any]) -> tuple[int, Bnk1accMap]:
        """Implements PROCESS-MAP logic."""
        # RECEIVE-MAP
        self.map_data.cust_no = map_input.get("CUSTNOI", "")

        # EDIT-DATA
        if not str(self.map_data.cust_no).isdigit():
            self.map_data.message = "Please enter a customer number."
            self.valid_data = False
            self.send_type = "DATAONLY_ALARM"
            return 4, self.map_data

        # GET-CUST-DATA
        if self.valid_data:
            rc = self._get_cust_data()
            if rc != 1:
                return rc, self.map_data

        self.send_type = "DATAONLY_ALARM"
        return 1, self.map_data

    def _get_cust_data(self) -> int:
        """Implements GET-CUST-DATA logic and INQACCCU program link."""
        self.inq_commarea.number_of_accounts = 20
        self.inq_commarea.comm_success = "N"
        self.inq_commarea.customer_number = self.map_data.cust_no

        # Equivalent to EXEC CICS LINK PROGRAM('INQACCCU')
        try:
            # This would be the external VSAM/DB logic call
            self.inq_commarea = self._call_inq_acccu(self.inq_commarea)
        except Exception as e:
            self._log_abend("GCD010 - LINK INQACCCU FAIL", str(e))
            return 5

        # Logic for matches
        if self.inq_commarea.customer_found == "N":
            self.map_data.message = f"Unable to find customer {self.inq_commarea.customer_number}"
            self.map_data.accounts = [""] * 10
            return 2

        # Initialize screen array
        self.map_data.accounts = [""] * 10

        if self.inq_commarea.number_of_accounts == 0:
            self.map_data.message = "No accounts found for customer"
            return 3
        
        if self.inq_commarea.comm_success == "N":
            self.map_data.message = f"Error accessing accounts for customer {self.inq_commarea.customer_number}."
            return 6

        # Populate screen with formatted data (up to 10 entries)
        self.map_data.message = f"{self.inq_commarea.number_of_accounts:2} accounts found"
        
        for i in range(min(self.inq_commarea.number_of_accounts, 10)):
            acc = self.inq_commarea.accounts[i]
            
            # Balance formatting logic (+/- and V99)
            avail_sign = "-" if acc["avail_bal"] < 0 else "+"
            act_sign = "-" if acc["actual_bal"] < 0 else "+"
            
            avail_abs = abs(acc["avail_bal"])
            act_abs = abs(acc["actual_bal"])
            
            # String formatting mimicking REDEFINES and MOVE logic
            # SCODE(6) + SPACE(6) + ACCNO(8) + SPACE(9) + TYPE + SPACE(7) + SIGN + BAL + . + CENTS ...
            avail_fmt = f"{int(avail_abs):010}.{int((avail_abs * 100) % 100):02}"
            act_fmt = f"{int(act_abs):010}.{int((act_abs * 100) % 100):02}"
            
            row = (f"{acc['scode']:<6}      {acc['acc_no']:<8}         "
                   f"{acc['acc_type']:<15}       {avail_sign}{avail_fmt}  "
                   f"{act_sign}{act_fmt}")
            
            self.map_data.accounts[i] = row

        return 1

    def _call_inq_acccu(self, commarea: InqAccCuCommaArea) -> InqAccCuCommaArea:
        """
        Mock for the external business logic program INQACCCU.
        In a real migration, this would be a service call or database query.
        """
        # Logic to be implemented by the Data Access Layer
        return commarea

    def _log_abend(self, location: str, error_msg: str) -> None:
        """
        Equivalent to ABNDPROC logic.
        Captures state for diagnostic dumping.
        """
        timestamp = datetime.datetime.now()
        abend_info = {
            "PGM": "BNK1CCA",
            "LOC": location,
            "TIME": timestamp.strftime("%H:%M:%S"),
            "DATE": timestamp.strftime("%d.%m.%Y"),
            "MSG": error_msg
        }
        # In actual implementation, this writes to a log or triggers an alert
        print(f"CRITICAL - ABEND: {abend_info}")

    def get_commarea_state(self) -> Dict[str, Any]:
        """Returns the updated WS-COMM-AREA."""
        return self.ws_comm_area