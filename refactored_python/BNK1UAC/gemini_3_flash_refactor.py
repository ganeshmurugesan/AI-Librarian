from typing import Optional, Dict, Any, Final, Self
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from datetime import datetime
import re

@dataclass
class AccountCommArea:
    """Represents the DFHCOMMAREA structure for BNK1UAC."""
    eye: str = "COMM"
    cust_no: str = ""
    sort_code: str = ""
    acc_no: int = 0
    acc_type: str = ""
    int_rate: Decimal = Decimal("0.00")
    opened_date: int = 0
    overdraft: int = 0
    last_stmt_dt: int = 0
    next_stmt_dt: int = 0
    avail_bal: Decimal = Decimal("0.00")
    actual_bal: Decimal = Decimal("0.00")
    success_flag: str = " "

@dataclass
class MapData:
    """Represents the BNK1UAM Map fields."""
    acc_no: str = ""
    acc_no_display: str = ""
    cust_no: str = ""
    sort_code: str = ""
    acc_type: str = ""
    int_rate: str = ""
    open_dd: str = ""
    open_mm: str = ""
    open_yyyy: str = ""
    lstmt_dd: str = ""
    lstmt_mm: str = ""
    lstmt_yyyy: str = ""
    nstmt_dd: str = ""
    nstmt_mm: str = ""
    nstmt_yyyy: str = ""
    overdraft: str = ""
    avail_bal: str = ""
    actual_bal: str = ""
    message: str = ""

class AccountUpdateService:
    """
    Legacy Migration of BNK1UAC - Account Update Business Logic.
    Handles VSAM-style READ UPDATE coordination and screen validation.
    """

    # Error Return Codes
    RC_SUCCESS: Final[int] = 0
    RC_INITIALIZED: Final[int] = 1
    RC_VALIDATION_ERROR: Final[int] = 2
    RC_NOT_FOUND: Final[int] = 3
    RC_UPDATE_FAILED: Final[int] = 4
    RC_SYSTEM_ERROR: Final[int] = 5
    RC_INVALID_KEY: Final[int] = 6
    RC_SESSION_END: Final[int] = 7
    RC_FORMAT_ERROR: Final[int] = 8

    VALID_ACC_TYPES: Final[list[str]] = [
        "CURRENT", "SAVING", "LOAN", "MORTGAGE", "ISA"
    ]

    def __init__(self):
        self.comm_area = AccountCommArea()
        self.map_data = MapData()

    def handle_request(self, aid_key: str, input_map: Optional[MapData] = None) -> tuple[int, MapData, AccountCommArea]:
        """
        Main entry point mimicking the PROCEDURE DIVISION.
        
        :param aid_key: The CICS Attention Identifier (e.g., 'ENTER', 'PF3', 'PF5')
        :param input_map: Data received from the screen
        :return: Tuple of (Return Code, Output Map, Comm Area)
        """
        if not input_map:
            # First time through (EIBCALEN = 0)
            return self.RC_INITIALIZED, MapData(message="Please enter account number"), self.comm_area

        self.map_data = input_map

        match aid_key:
            case 'PF3' | 'PF12':
                return self.RC_SESSION_END, MapData(message="Session Ended"), self.comm_area
            case 'CLEAR':
                return self.RC_INITIALIZED, MapData(), self.comm_area
            case 'ENTER':
                return self._process_inquiry()
            case 'PF5':
                return self._process_update()
            case _:
                self.map_data.message = "Invalid key pressed."
                return self.RC_INVALID_KEY, self.map_data, self.comm_area

    def _process_inquiry(self) -> tuple[int, MapData, AccountCommArea]:
        """Mimics PM010 logic for Inquiry."""
        if not self.map_data.acc_no.isdigit():
            self.map_data.message = "Please enter an account number."
            return self.RC_VALIDATION_ERROR, self.map_data, self.comm_area

        # Call simulated external INQACC program (CICS LINK)
        success, record = self._link_inqacc(int(self.map_data.acc_no))
        
        if not success:
            self.map_data.message = "This account number could not be found"
            return self.RC_NOT_FOUND, self.map_data, self.comm_area

        self._populate_map_from_comm(record)
        self.map_data.message = "Please amend fields and hit <pf5> to apply changes"
        return self.RC_SUCCESS, self.map_data, self.comm_area

    def _process_update(self) -> tuple[int, MapData, AccountCommArea]:
        """Mimics PM010 logic for Update with VSAM LOCK logic."""
        # 1. Validate Map Data
        validation_rc = self._validate_data()
        if validation_rc != self.RC_SUCCESS:
            return validation_rc, self.map_data, self.comm_area

        # 2. Sync Map to CommArea
        self._sync_comm_from_map()

        # 3. Call simulated external UPDACC program (CICS LINK with SYNCONRETURN)
        # This handles the actual 'EXEC CICS READ UPDATE' / 'REWRITE'
        update_success = self._link_updacc()

        if not update_success:
            self.map_data.message = "Update unsuccessful, try again later."
            return self.RC_UPDATE_FAILED, self.map_data, self.comm_area

        self.map_data.message = "Account update successfully applied."
        return self.RC_SUCCESS, self.map_data, self.comm_area

    def _validate_data(self) -> int:
        """Mimics VALIDATE-DATA SECTION (VD010)."""
        # Account Type Check
        if self.map_data.acc_type.strip() not in self.VALID_ACC_TYPES:
            self.map_data.message = f"Account Type must be {', '.join(self.VALID_ACC_TYPES)}. Then press PF5."
            return self.RC_VALIDATION_ERROR

        # Interest Rate Check (Mimics INSPECT TALLYING logic)
        try:
            rate_str = self.map_data.int_rate.strip()
            if not rate_str or not re.match(r'^\d{1,4}(\.\d{0,2})?$', rate_str):
                raise ValueError
            rate_val = Decimal(rate_str)
            if rate_val < 0 or rate_val > Decimal("9999.99"):
                raise ValueError
            
            # Specific Business Rule: Non-zero for Loan/Mortgage
            if self.map_data.acc_type.strip() in ["LOAN", "MORTGAGE"] and rate_val == 0:
                self.map_data.message = "Interest rate cannot be 0 with this account type."
                return self.RC_VALIDATION_ERROR
        except (ValueError, InvalidOperation):
            self.map_data.message = "Please supply a numeric interest rate (max 9999.99) with up to 2 decimals."
            return self.RC_VALIDATION_ERROR

        # Date Validation (Mimics VSAM/COBOL logic for day ranges)
        if not self._is_valid_date(self.map_data.lstmt_dd, self.map_data.lstmt_mm, self.map_data.lstmt_yyyy):
            self.map_data.message = "Incorrect date for LAST STATEMENT."
            return self.RC_VALIDATION_ERROR

        if not self._is_valid_date(self.map_data.nstmt_dd, self.map_data.nstmt_mm, self.map_data.nstmt_yyyy):
            self.map_data.message = "Incorrect date for NEXT STATEMENT."
            return self.RC_VALIDATION_ERROR

        return self.RC_SUCCESS

    def _is_valid_date(self, d: str, m: str, y: str) -> bool:
        """Helper to mimic COBOL date logic including manual boundary checks."""
        try:
            day, month, year = int(d), int(m), int(y)
            if not (1 <= month <= 12 and 1 <= day <= 31):
                return False
            # Specific month checks from legacy code
            if month in [4, 6, 9, 11] and day == 31:
                return False
            if month == 2 and day > 29:
                return False
            return True
        except (ValueError, TypeError):
            return False

    def _sync_comm_from_map(self) -> None:
        """Mimics UAD010 data conversion from screen format to internal binary."""
        self.comm_area.acc_no = int(self.map_data.acc_no_display or self.map_data.acc_no)
        self.comm_area.cust_no = self.map_data.cust_no
        self.comm_area.sort_code = self.map_data.sort_code
        self.comm_area.acc_type = self.map_data.acc_type
        self.comm_area.int_rate = Decimal(self.map_data.int_rate)
        
        # Pack dates into YYYYMMDD style ints for CommArea
        self.comm_area.opened_date = int(f"{self.map_data.open_yyyy}{self.map_data.open_mm}{self.map_data.open_dd}")
        self.comm_area.last_stmt_dt = int(f"{self.map_data.lstmt_yyyy}{self.map_data.lstmt_mm}{self.map_data.lstmt_dd}")
        self.comm_area.next_stmt_dt = int(f"{self.map_data.nstmt_yyyy}{self.map_data.nstmt_mm}{self.map_data.nstmt_dd}")
        
        self.comm_area.overdraft = int(self.map_data.overdraft or 0)
        
        # Balance conversions (Handling signs/decimals as in WS-CONVERT-PICX)
        self.comm_area.avail_bal = self._parse_currency(self.map_data.avail_bal)
        self.comm_area.actual_bal = self._parse_currency(self.map_data.actual_bal)

    def _populate_map_from_comm(self, comm: AccountCommArea) -> None:
        """Mimics IAD010 moving fields to output map."""
        self.comm_area = comm
        self.map_data.acc_no_display = str(comm.acc_no)
        self.map_data.cust_no = comm.cust_no
        self.map_data.sort_code = comm.sort_code
        self.map_data.acc_type = comm.acc_type
        self.map_data.int_rate = f"{comm.int_rate:07.2f}"
        
        date_str = str(comm.opened_date).zfill(8)
        self.map_data.open_dd, self.map_data.open_mm, self.map_data.open_yyyy = date_str[6:], date_str[4:6], date_str[:4]
        
        ls_str = str(comm.last_stmt_dt).zfill(8)
        self.map_data.lstmt_dd, self.map_data.lstmt_mm, self.map_data.lstmt_yyyy = ls_str[6:], ls_str[4:6], ls_str[:4]
        
        ns_str = str(comm.next_stmt_dt).zfill(8)
        self.map_data.nstmt_dd, self.map_data.nstmt_mm, self.map_data.nstmt_yyyy = ns_str[6:], ns_str[4:6], ns_str[:4]
        
        self.map_data.overdraft = str(comm.overdraft)
        self.map_data.avail_bal = f"{comm.avail_bal:+013.2f}"
        self.map_data.actual_bal = f"{comm.actual_bal:+013.2f}"

    def _parse_currency(self, val: str) -> Decimal:
        """Mimics WS-CONVERT-PICX logic for parsing currency with signs."""
        if not val: return Decimal("0.00")
        clean_val = val.replace(" ", "").replace("+", "")
        try:
            return Decimal(clean_val)
        except InvalidOperation:
            return Decimal("0.00")

    def _link_inqacc(self, acc_no: int) -> tuple[bool, AccountCommArea]:
        """Simulation of EXEC CICS LINK PROGRAM('INQACC')."""
        # In a real migration, this would call a repository or microservice
        # For logic demonstration, we return a mock record
        if acc_no == 0:
            return False, AccountCommArea()
        return True, AccountCommArea(acc_no=acc_no, cust_no="CUST001", acc_type="CURRENT")

    def _link_updacc(self) -> bool:
        """Simulation of EXEC CICS LINK PROGRAM('UPDACC') with locking logic."""
        # In a real migration, this method executes the database update 
        # inside a transaction with 'SELECT FOR UPDATE'
        self.comm_area.success_flag = "Y"
        return True