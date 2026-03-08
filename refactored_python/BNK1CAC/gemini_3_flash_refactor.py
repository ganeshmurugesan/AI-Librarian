from typing import Optional, TypedDict, Final
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import datetime
import re

@dataclass
class AccountCommunicationArea:
    """Structure representing the DFHCOMMAREA for BNK1CAC."""
    cust_no: int = 0
    acc_type: str = ""
    int_rate: Decimal = Decimal("0.00")
    overdraft_limit: int = 0

@dataclass
class SubProgramParms:
    """Structure for linking to the CREACC sub-program."""
    eyecatcher: str = "ACCT"
    cust_no: int = 0
    sort_code: int = 0
    acc_number: int = 0
    acc_type: str = ""
    int_rate: Decimal = Decimal("0.00")
    opened_date: int = 0
    overdraft_limit: int = 0
    last_stmt_date: int = 0
    next_stmt_date: int = 0
    avail_bal: Decimal = Decimal("0.00")
    act_bal: Decimal = Decimal("0.00")
    success: str = "N"
    fail_code: str = " "

class AccountCreationService:
    """
    Service handling the logic for BNK1CAC: Account Creation Verification and Persistence.
    
    Migrated from IBM COBOL legacy system. Maintains original validation rules,
    transactional flow, and specific CICS/VSAM error handling codes.
    """

    SUPPORTED_TYPES: Final[list[str]] = ["ISA", "CURRENT", "LOAN", "SAVING", "MORTGAGE"]

    def __init__(self):
        self.message: str = ""
        self.valid_data: bool = True

    def process_request(self, 
                        input_data: dict, 
                        comm_area_len: int) -> tuple[dict, AccountCommunicationArea]:
        """
        Main entry point mirroring the A010 Procedure Division logic.
        
        :param input_data: Data received from the screen map (BNK1CAI).
        :param comm_area_len: Length of the communication area (EIBCALEN).
        :return: Tuple of output map data and updated communication area.
        """
        output_map = self._initialize_output_map()
        ws_comm = AccountCommunicationArea()

        # Equivalent to EVALUATE TRUE logic for EIBAID/EIBCALEN
        aid = input_data.get("EIBAID", "DFHENTER")

        if comm_area_len == 0:
            output_map["MESSAGEO"] = ""
            return output_map, ws_comm

        if aid in ["DFHPA1", "DFHPA2", "DFHPA3"]:
            return output_map, ws_comm

        if aid == "DFHPF3":
            # Logic for return to OMEN omitted per task scope
            return output_map, ws_comm

        if aid == "DFHENTER":
            output_map = self._process_map(input_data)
        else:
            output_map["MESSAGEO"] = "Invalid key pressed."
            
        # Update Communication Area
        if comm_area_len != 0:
            ws_comm.cust_no = int(input_data.get("CUSTNOI", 0))
            ws_comm.acc_type = input_data.get("ACCTYPI", "").strip()

        return output_map, ws_comm

    def _process_map(self, input_map: dict) -> dict:
        """Logic from PROCESS-MAP section."""
        self.valid_data = True
        
        # Validation (EDIT-DATA section)
        validated_fields = self._edit_data(input_map)
        
        output_map = self._initialize_output_map()
        
        if self.valid_data:
            # Creation (CRE-ACC-DATA section)
            output_map = self._create_account_data(validated_fields)
        else:
            output_map["MESSAGEO"] = self.message
            # Reflect input back to map
            output_map.update({k.replace('I', 'O'): v for k, v in input_map.items() if k.endswith('I')})

        return output_map

    def _edit_data(self, input_map: dict) -> dict:
        """
        Implements rigorous COBOL validation for customer, account type, 
        interest rate, and overdraft limits.
        """
        # De-edit Customer Number (BIF DEEDIT)
        raw_cust = re.sub(r'\D', '', str(input_map.get("CUSTNOI", "")))
        
        if not raw_cust or len(raw_cust) != 10:
            self._set_error("Please enter a 10 digit Customer Number ")
            return {}

        # Account Type Validation
        acc_type = str(input_map.get("ACCTYPI", "")).strip().upper().replace("_", "")
        if acc_type not in self.SUPPORTED_TYPES:
            self._set_error("Account Type should be ISA,CURRENT,LOAN,SAVING or MORTGAGE")
            return {}

        # Interest Rate Validation (Complex decimal logic from COBOL)
        raw_int = str(input_map.get("INTRTI", "")).strip()
        try:
            if "." in raw_int and len(raw_int.split(".")[1]) > 2:
                self._set_error("Only up to two decimal places are supported")
                return {}
            
            int_rate = Decimal(raw_int)
            if int_rate < 0:
                self._set_error("Please supply a zero or positive interest rate")
                return {}
            if int_rate > Decimal("9999.99"):
                self._set_error("Please supply an interest rate less than 9999.99%")
                return {}
        except (InvalidOperation, ValueError):
            self._set_error("Please supply a numeric interest rate")
            return {}

        # Overdraft validation
        raw_overdraft = re.sub(r'\D', '', str(input_map.get("OVERDRI", "0")).strip())
        overdraft = int(raw_overdraft) if raw_overdraft else 0

        return {
            "cust_no": int(raw_cust),
            "acc_type": acc_type,
            "int_rate": int_rate,
            "overdraft": overdraft
        }

    def _create_account_data(self, fields: dict) -> dict:
        """
        Logic for CAD010: Preparation and linking to CREACC subprogram.
        Includes mandatory VSAM error code mappings (1-8).
        """
        params = SubProgramParms(
            cust_no=fields["cust_no"],
            acc_type=fields["acc_type"],
            int_rate=fields["int_rate"],
            overdraft_limit=fields["overdraft"]
        )

        # Mock of EXEC CICS LINK PROGRAM('CREACC')
        # In a real migration, this calls the persistence layer/service
        params = self._call_creacc_subprogram(params)
        
        output = self._initialize_output_map()

        if params.success == "N":
            self.valid_data = False
            # Specific Business Error Return Codes (1-8, 9, A)
            error_mapping = {
                "1": "The supplied customer number does not exist.",
                "2": "The customer data cannot be accessed, unable to create account.",
                "3": "Account record creation failed. (unable to ENQ ACCOUNT NC).",
                "4": "Account record creation failed, (unable to increment ACCOUNT NC).",
                "5": "Account record creation failed, (unable to restore ACCOUNT NC).",
                "6": "Account record creation failed, (unable to WRITE to ACCOUNT file).",
                "7": "Account record creation failed, (unable to INSERT into ACCOUNT).",
                "8": "Account record creation failed, (too many accounts).",
                "9": "Account record creation failed, unable to count accounts.",
                "A": "Account record creation failed, account type unsupported."
            }
            output["MESSAGEO"] = error_mapping.get(params.fail_code, "The account was not created.")
        else:
            output["MESSAGEO"] = "The Account has been successfully created"
            output.update({
                "SRTCDO": f"{params.sort_code:06d}",
                "ACCNOO": f"{params.acc_number:08d}",
                "AVAILO": f"{params.avail_bal:+013.2f}",
                "ACTBALO": f"{params.act_bal:+013.2f}",
                # Date formatting mapping (DDMMYYYY)
                "OPENDDO": str(params.opened_date)[0:2],
                "OPENMMO": str(params.opened_date)[2:4],
                "OPENYYO": str(params.opened_date)[4:8]
            })

        # Return state to map
        output.update({
            "CUSTNOO": params.cust_no,
            "ACCTYPO": params.acc_type,
            "INTRTO": f"{params.int_rate:07.2f}",
            "OVERDRO": params.overdraft_limit
        })
        
        return output

    def _call_creacc_subprogram(self, params: SubProgramParms) -> SubProgramParms:
        """
        Interface for the external account creation program.
        This is where the VSAM READ UPDATE locking logic resides.
        """
        # Implementation depends on the target DB architecture (SQL/NoSQL)
        # but must ensure atomic increment of account numbers (ENQ/DEQ logic).
        return params

    def _set_error(self, msg: str) -> None:
        self.message = msg
        self.valid_data = False

    def _initialize_output_map(self) -> dict:
        """Helper to create an empty map structure."""
        return {
            "MESSAGEO": "",
            "CUSTNOO": "",
            "ACCTYPO": "",
            "INTRTO": "",
            "OVERDRO": "",
            "SRTCDO": "",
            "ACCNOO": "",
            "AVAILO": "",
            "ACTBALO": ""
        }