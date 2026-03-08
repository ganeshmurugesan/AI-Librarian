from typing import Optional, TypedDict, Final
from dataclasses import dataclass, field
from datetime import datetime

# Error Return Codes based on COBOL logic requirements
SUCCESS: Final[int] = 0
ERR_NOT_FOUND: Final[int] = 1
ERR_DATASTORE: Final[int] = 2
ERR_ACTION_FAILED: Final[int] = 3
ERR_INVALID_INPUT: Final[int] = 4
ERR_INVALID_TITLE: Final[int] = 5
ERR_ADDRESS_REQUIRED: Final[int] = 6
ERR_SORT_CODE_INVALID: Final[int] = 7
ERR_UNKNOWN: Final[int] = 8

class CustomerCommArea(TypedDict):
    """Represents the DFHCOMMAREA state preservation between CICS interactions."""
    term_id: int
    eye_catcher: str
    sort_code: str
    cust_no: str
    name: str
    address: str
    dob: int
    credit_score: int
    cs_review_date: int
    update_flag: str  # 'Y' if in update mode (PF10 pressed)

@dataclass
class CustomerRecord:
    """Structure mirroring the VSAM record layout for Customer data."""
    cust_no: str
    sort_code: str
    name: str
    address: str
    dob: int
    credit_score: int
    review_date: int

class BankCustomerService:
    """
    Modern implementation of BNK1DCS CICS/COBOL Display Customer Program.
    Handles Inquiry, Update (with field unlocking), and Deletion of customer records.
    """

    VALID_TITLES: Final[set[str]] = {
        "Mr", "Mrs", "Miss", "Ms", "Dr", "Professor",
        "Drs", "Lord", "Sir", "Lady"
    }

    def __init__(self):
        self.message: str = ""
        self.comm_area: CustomerCommArea = self._initialize_comm_area()

    def _initialize_comm_area(self) -> CustomerCommArea:
        return {
            "term_id": 0, "eye_catcher": "", "sort_code": "", "cust_no": "",
            "name": "", "address": "", "dob": 0, "credit_score": 0,
            "cs_review_date": 0, "update_flag": "N"
        }

    def process_request(self, aid_key: str, input_data: dict) -> tuple[int, str]:
        """
        Main entry point mimicking the PROCEDURE DIVISION EVALUATE EIBAID logic.
        
        :param aid_key: The Attention Identifier (e.g., 'ENTER', 'PF3', 'PF5', 'PF10')
        :param input_data: Dictionary containing screen field values
        :return: Tuple of (Return Code, Message)
        """
        match aid_key:
            case 'PF3':
                return SUCCESS, "Session Ended"
            case 'PF5':
                return self._handle_delete(input_data)
            case 'PF10':
                return self._handle_unlock_for_update(input_data)
            case 'ENTER':
                if self.comm_area["update_flag"] == "Y":
                    return self._handle_update_execution(input_data)
                return self._handle_inquiry(input_data)
            case 'CLEAR':
                self.comm_area = self._initialize_comm_area()
                return SUCCESS, ""
            case _:
                return ERR_INVALID_INPUT, "Invalid key pressed."

    def _handle_inquiry(self, data: dict) -> tuple[int, str]:
        """Processes customer lookup logic (GCD010)."""
        cust_no = data.get("cust_no", "").strip()
        
        rc = self._validate_cust_no(cust_no)
        if rc != SUCCESS:
            return rc, self.message

        # Simulated EXEC CICS LINK PROGRAM('INQCUST')
        record = self._data_access_layer_get(cust_no)
        
        if not record:
            self.message = "Sorry, but that customer number was not found."
            return ERR_NOT_FOUND, self.message

        self._map_record_to_comm_area(record)
        self.message = "Customer lookup successful. <PF5> to Delete. <PF10> to Update."
        return SUCCESS, self.message

    def _handle_unlock_for_update(self, data: dict) -> tuple[int, str]:
        """Logic for PF10 - Unprotects fields and sets update state (UCD010)."""
        cust_no = data.get("cust_no", "").strip()
        
        # Validation matches COBOL VD010
        if not cust_no or cust_no == "9999999999":
            return ERR_INVALID_INPUT, "The customer number is not VALID."

        self.comm_area["update_flag"] = "Y"
        return SUCCESS, "Amend data then press <ENTER>."

    def _handle_update_execution(self, data: dict) -> tuple[int, str]:
        """Logic for executing the VSAM UPDATE (UPDCD010)."""
        # Validate Title (ED2010)
        name = data.get("name", "")
        title = name.split()[0] if name.split() else ""
        if title not in self.VALID_TITLES:
            return ERR_INVALID_TITLE, "Valid titles are: Mr,Mrs,Miss,Ms,Dr,Professor,Drs,Lord,Sir,Lady"

        # Validate Address (ED2010)
        if not any([data.get("addr1"), data.get("addr2"), data.get("addr3")]):
            return ERR_ADDRESS_REQUIRED, "Address must not be all spaces - please reenter"

        # Simulated EXEC CICS LINK PROGRAM('UPDCUST') with READ UPDATE lock
        # Maintaining the business logic requirement for VSAM-style locking
        success = self._data_access_layer_update(data)
        
        if success:
            self.comm_area["update_flag"] = "N"
            return SUCCESS, f"Customer {data['cust_no']} was updated successfully"
        
        return ERR_ACTION_FAILED, "Sorry but an update error occurred. Customer NOT updated."

    def _handle_delete(self, data: dict) -> tuple[int, str]:
        """Logic for PF5 customer deletion (DCD010)."""
        cust_no = data.get("cust_no", "").strip()
        
        # Simulated EXEC CICS LINK PROGRAM('DELCUS')
        # Matches COBOL return code logic for COMM-DEL-FAIL-CD
        status = self._data_access_layer_delete(cust_no)
        
        match status:
            case "1": return ERR_NOT_FOUND, "Sorry but that Cust no was not found. Customer NOT deleted."
            case "2": return ERR_DATASTORE, "Sorry but a datastore error occurred. Action NOT applied."
            case "3": return ERR_ACTION_FAILED, "Sorry but a delete error occurred. Customer NOT deleted."
            case "0": return SUCCESS, f"Customer {cust_no} and associated accounts deleted."
            case _: return ERR_UNKNOWN, "Sorry but an unknown error occurred."

    def _validate_cust_no(self, cust_no: str) -> int:
        """Internal validation mirroring BIF DEEDIT and VD010."""
        if not cust_no:
            self.message = "Please enter a customer number."
            return ERR_INVALID_INPUT
        
        if not cust_no.isdigit():
            self.message = "Please enter a numeric customer number."
            return ERR_INVALID_INPUT
            
        return SUCCESS

    def _map_record_to_comm_area(self, record: CustomerRecord) -> None:
        """Helper to synchronize state, mirroring BNK1DCS screen/commarea mapping."""
        self.comm_area.update({
            "sort_code": record.sort_code,
            "cust_no": record.cust_no,
            "name": record.name,
            "address": record.address,
            "dob": record.dob,
            "credit_score": record.credit_score,
            "cs_review_date": record.review_date
        })

    # Mock Data Access Layer (Simulating LINK programs and VSAM operations)
    def _data_access_layer_get(self, cust_no: str) -> Optional[CustomerRecord]:
        # Implementation would interface with a Database or Mainframe Connector
        return None 

    def _data_access_layer_update(self, data: dict) -> bool:
        """Simulates VSAM READ UPDATE followed by REWRITE."""
        # Logical lock acquisition happens here in a modern environment (e.g., SELECT FOR UPDATE)
        return True

    def _data_access_layer_delete(self, cust_no: str) -> str:
        """Simulates the DELCUS program return codes."""
        return "0"