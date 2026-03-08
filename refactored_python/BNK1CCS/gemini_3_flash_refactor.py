from typing import TypedDict, Optional, Final
from dataclasses import dataclass, field
from datetime import datetime
import enum

class ReturnCode(enum.IntEnum):
    """Business logic return codes representing program status."""
    SUCCESS = 1
    INVALID_TITLE = 2
    INVALID_FIRST_NAME = 3
    INVALID_SURNAME = 4
    INVALID_ADDRESS = 5
    INVALID_DOB = 6
    BUSINESS_RULE_VIOLATION = 7  # e.g., Too old or future date
    SYSTEM_ERROR = 8

@dataclass
class CustomerMapData:
    """Represents the BNK1CCM Map structure (Input/Output)."""
    title: str = ""
    first_name: str = ""
    initials: str = ""
    surname: str = ""
    address_line1: str = ""
    address_line2: str = ""
    address_line3: str = ""
    dob_dd: str = ""
    dob_mm: str = ""
    dob_yyyy: str = ""
    sort_code: int = 0
    customer_number: int = 0
    credit_score: int = 0
    review_date_dd: str = ""
    review_date_mm: str = ""
    review_date_yyyy: str = ""
    message: str = ""

@dataclass
class SubProgramParms:
    """Communication area for the CRECUST sub-program."""
    eyecatcher: str = "CUST"
    sort_code: int = 0
    customer_number: int = 0
    full_name: str = ""
    address_blob: str = ""
    dob: int = 0
    credit_score: int = 0
    review_date: int = 0
    success_flag: str = "N"
    fail_code: str = ""

class BNK1CCS:
    """
    Create Customer program logic migrated from COBOL BNK1CCS.
    Maintains CICS UI flow logic and business validation.
    """

    VALID_TITLES: Final[list[str]] = [
        "MR", "MRS", "MISS", "MS", "DR", "PROFESSOR", "LORD", "SIR", "LADY", "DRS"
    ]

    def __init__(self):
        self.map_data = CustomerMapData()
        self.valid_data_sw: bool = True

    def process_request(self, eib_aid: str, calen: int, input_data: Optional[dict] = None) -> tuple[CustomerMapData, ReturnCode]:
        """
        Main entry point equivalent to PROCEDURE DIVISION A010.
        
        :param eib_aid: The Attention Identifier (Key pressed)
        :param calen: Communication area length (0 for first time)
        :param input_data: Dictionary of map input values
        :return: Tuple of updated Map Data and Status Code
        """
        # First time through logic (EIBCALEN = 0)
        if calen == 0:
            return self._initialize_screen()

        # Handle PF Keys (EVALUATE TRUE)
        match eib_aid:
            case "DFHPF3" | "DFHPF12":
                self.map_data.message = "Session Ended"
                return self.map_data, ReturnCode.SUCCESS
            case "DFHCLEAR":
                return self._initialize_screen()
            case "DFHENTER":
                if input_data:
                    self._map_inbound_data(input_data)
                return self._process_map()
            case _:
                self.map_data.message = "Invalid key pressed."
                return self.map_data, ReturnCode.SYSTEM_ERROR

    def _initialize_screen(self) -> tuple[CustomerMapData, ReturnCode]:
        """Initializes empty map fields."""
        self.map_data = CustomerMapData()
        return self.map_data, ReturnCode.SUCCESS

    def _map_inbound_data(self, input_dict: dict) -> None:
        """Helper to move UI input into the internal data structure."""
        for key, value in input_dict.items():
            if hasattr(self.map_data, key):
                # Simulate the replacement of underscores (INSPECT REPLACING)
                sanitized = str(value).replace("_", " ").strip()
                setattr(self.map_data, key, sanitized)

    def _process_map(self) -> tuple[CustomerMapData, ReturnCode]:
        """PM010 Section: Validation and Data Creation."""
        validation_code = self._edit_data()
        
        if validation_code == ReturnCode.SUCCESS:
            return self._create_customer_data()
        
        return self.map_data, validation_code

    def _edit_data(self) -> ReturnCode:
        """ED010 Section: Validation logic for incoming fields."""
        self.valid_data_sw = True

        # Validate Title
        clean_title = self.map_data.title.upper().replace(".", "")
        if not clean_title or clean_title not in self.VALID_TITLES:
            self.map_data.message = "Valid titles: Mr, Mrs, Miss, Ms, Dr, Professor, Lord, Sir, Lady"
            return ReturnCode.INVALID_TITLE

        # Validate Name/Surname
        if not self.map_data.first_name:
            self.map_data.message = "Please supply a valid First Name"
            return ReturnCode.INVALID_FIRST_NAME
        
        if not self.map_data.surname:
            self.map_data.message = "Please supply a valid Surname"
            return ReturnCode.INVALID_SURNAME

        # Validate Address
        if not self.map_data.address_line1:
            self.map_data.message = "Please supply a valid Address Line 1"
            return ReturnCode.INVALID_ADDRESS

        # Validate DOB Numeric and Ranges
        try:
            day = int(self.map_data.dob_dd)
            month = int(self.map_data.dob_mm)
            year = int(self.map_data.dob_yyyy)
            
            if not (1 <= day <= 31) or not (1 <= month <= 12):
                raise ValueError
            
            # Basic future check
            if year > datetime.now().year:
                self.map_data.message = "Sorry, customer D.O.B. is in the future."
                return ReturnCode.BUSINESS_RULE_VIOLATION
                
        except (ValueError, TypeError):
            self.map_data.message = "Please supply a valid Date of Birth (DD MM YYYY)"
            return ReturnCode.INVALID_DOB

        return ReturnCode.SUCCESS

    def _create_customer_data(self) -> tuple[CustomerMapData, ReturnCode]:
        """
        CCD010 Section: Preparation for CRECUST call.
        Note: The actual VSAM READ UPDATE locking happens within the 
        data layer invoked by the sub-program logic.
        """
        parms = SubProgramParms()
        
        # Format Full Name (STRING DELIMITED BY SPACE)
        name_parts = [self.map_data.title, self.map_data.first_name, 
                      self.map_data.initials, self.map_data.surname]
        parms.full_name = " ".join(filter(None, name_parts))

        # Format Address Blob
        parms.address_blob = (f"{self.map_data.address_line1:<60}"
                             f"{self.map_data.address_line2:<60}"
                             f"{self.map_data.address_line3:<40}")

        # Numeric DOB (YYYYMMDD)
        parms.dob = int(f"{self.map_data.dob_yyyy}{self.map_data.dob_mm:0>2}{self.map_data.dob_dd:0>2}")

        # Simulate EXEC CICS LINK PROGRAM('CRECUST')
        # This is where the VSAM 'READ UPDATE' lock would be acquired on the sequence/index file.
        result_parms = self._call_crecust_service(parms)

        if result_parms.success_flag == "N":
            match result_parms.fail_code:
                case "O": self.map_data.message = "Sorry, customer is too old. Please check D.O.B."
                case "Y": self.map_data.message = "Sorry, customer D.O.B. is in the future."
                case "Z": self.map_data.message = "Sorry, customer D.O.B. is invalid."
                case _: self.map_data.message = "Sorry but unable to create Customer record"
            return self.map_data, ReturnCode.BUSINESS_RULE_VIOLATION

        # Populate Success Data
        self.map_data.message = "The Customer record has been successfully created"
        self.map_data.sort_code = result_parms.sort_code
        self.map_data.customer_number = result_parms.customer_number
        self.map_data.credit_score = result_parms.credit_score
        
        # Parse review date (assuming 8-char string/int format)
        rd = str(result_parms.review_date)
        if len(rd) == 8:
            self.map_data.review_date_dd = rd[0:2]
            self.map_data.review_date_mm = rd[2:4]
            self.map_data.review_date_yyyy = rd[4:8]

        return self.map_data, ReturnCode.SUCCESS

    def _call_crecust_service(self, parms: SubProgramParms) -> SubProgramParms:
        """
        Simulates the external CRECUST CICS Program call.
        In a cloud-native environment, this would involve a Transactional Database 
        Session with a 'SELECT ... FOR UPDATE' on the key generator.
        """
        # Logic Placeholder for external business service
        parms.success_flag = "Y"
        parms.sort_code = 102030
        parms.customer_number = 5544332211
        parms.credit_score = 750
        parms.review_date = 12122025
        return parms