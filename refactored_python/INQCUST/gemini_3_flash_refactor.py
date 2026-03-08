import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Protocol, NoReturn


@dataclass
class CustomerRecord:
    """Represents the VSAM CUSTOMER record layout."""
    customer_number: int = 0
    sort_code: int = 0
    name: str = ""
    address: str = ""
    date_of_birth: str = ""
    credit_score: int = 0
    review_date: str = ""
    eyecatcher: str = "CUST"


@dataclass
class InquiryCommarea:
    """Represents the DFHCOMMAREA for INQCUST."""
    sort_code: int = 0
    customer_number: int = 0
    success_flag: str = 'N'
    fail_code: str = '0'
    # Output fields
    eye: str = ""
    scode: int = 0
    custno: int = 0
    name: str = ""
    addr: str = ""
    dob: str = ""
    credit_score: int = 0
    cs_review_dt: str = ""


class VSAMProvider(Protocol):
    """Interface for VSAM-like data access with locking capabilities."""
    def read_for_update(self, file_name: str, key: dict) -> tuple[int, int, Optional[CustomerRecord]]: ...
    def start_browse(self, file_name: str, key: dict) -> tuple[int, int]: ...
    def read_previous(self, file_name: str) -> tuple[int, int, Optional[CustomerRecord]]: ...
    def end_browse(self, file_name: str) -> None: ...
    def rollback(self) -> None: ...


class InquiryCustomer:
    """
    Legacy Migration of INQCUST COBOL program.
    Handles customer inquiry via VSAM with retry logic and specific RLS abend handling.
    """

    # CICS Response Codes (Emulated)
    DFHRESP_NORMAL = 0
    DFHRESP_NOTFND = 1
    DFHRESP_SYSIDERR = 2
    
    # RLS/Storm Drain Abend Codes
    STORM_DRAIN_CODES = {'AFCR', 'AFCS', 'AFCT'}

    def __init__(self, vsam_provider: VSAMProvider):
        self.vsam = vsam_provider
        self.retry_count = 0
        self.max_sysiderr_retries = 100
        self.max_notfound_retries = 1000

    def process(self, commarea: InquiryCommarea) -> InquiryCommarea:
        """
        Main entry point mimicking the PROCEDURE DIVISION.
        """
        try:
            commarea.success_flag = 'N'
            commarea.fail_code = '0'

            # Logic for random or last-customer retrieval
            if commarea.customer_number in (0, 9999999999):
                last_cust_no = self._get_last_customer_vsam(commarea.sort_code)
                if last_cust_no is None:
                    # If we can't find the last customer, it's a critical failure
                    commarea.fail_code = '9'
                    return commarea
                
                if commarea.customer_number == 0:
                    commarea.customer_number = self._generate_random_customer(last_cust_no)
                else:
                    commarea.customer_number = last_cust_no

            # Perform main VSAM Read
            result = self._read_customer_vsam(commarea)
            
            if result and commarea.success_flag == 'Y':
                self._map_to_commarea(result, commarea)
            
            return commarea

        except Exception as e:
            return self._handle_abend(str(e), commarea)

    def _read_customer_vsam(self, commarea: InquiryCommarea) -> Optional[CustomerRecord]:
        """
        Emulates READ-CUSTOMER-VSAM section with SYSIDERR retry logic and locking.
        """
        exit_vsam_read = False
        v_retried = False
        
        while not exit_vsam_read:
            key = {"sort_code": commarea.sort_code, "cust_no": commarea.customer_number}
            resp, resp2, data = self.vsam.read_for_update("CUSTOMER", key)

            if resp == self.DFHRESP_NORMAL:
                commarea.success_flag = 'Y'
                return data

            # Handle SYSIDERR (System ID Error) with retries
            if resp == self.DFHRESP_SYSIDERR:
                for _ in range(self.max_sysiderr_retries):
                    time.sleep(3)
                    resp, resp2, data = self.vsam.read_for_update("CUSTOMER", key)
                    if resp == self.DFHRESP_NORMAL:
                        commarea.success_flag = 'Y'
                        return data
                # If still failing after 100 retries, fall through to abend

            # Handle NOT FOUND
            if resp == self.DFHRESP_NOTFND:
                # Logic for random customer re-try
                if commarea.customer_number == 0 and self.retry_count < self.max_notfound_retries:
                    self.retry_count += 1
                    # In a real scenario, we'd need the last_cust_no cached or re-fetched
                    continue 
                
                # Logic for last customer retry
                if commarea.customer_number == 9999999999 and not v_retried:
                    last_no = self._get_last_customer_vsam(commarea.sort_code)
                    if last_no:
                        commarea.customer_number = last_no
                        v_retried = True
                        continue

                # Standard Not Found
                commarea.success_flag = 'N'
                commarea.fail_code = '1' # Error return code 1
                commarea.name = ""
                commarea.addr = ""
                return None

            # If any other error, trigger abend procedure
            self._raise_critical_error("CVR1", resp, resp2, key)

    def _get_last_customer_vsam(self, sort_code: int) -> Optional[int]:
        """
        Emulates GET-LAST-CUSTOMER-VSAM using browse operations.
        Returns the highest customer number for the sort code.
        """
        # Start browse at high values to find the end of the file
        key = {"sort_code": sort_code, "cust_no": 9999999999}
        resp, resp2 = self.vsam.start_browse("CUSTOMER", key)
        
        # Retry logic for SYSIDERR in browsing
        if resp == self.DFHRESP_SYSIDERR:
            for _ in range(self.max_sysiderr_retries):
                time.sleep(3)
                resp, resp2 = self.vsam.start_browse("CUSTOMER", key)
                if resp == self.DFHRESP_NORMAL: break
        
        if resp != self.DFHRESP_NORMAL:
            return None

        # Read previous to get the actual last record
        resp, resp2, data = self.vsam.read_previous("CUSTOMER")
        self.vsam.end_browse("CUSTOMER")

        if resp == self.DFHRESP_NORMAL and data:
            return data.customer_number
        return None

    def _generate_random_customer(self, max_val: int) -> int:
        """Emulates COMPUTE RANDOM-CUSTOMER."""
        if max_val <= 1:
            return 1
        return random.randint(1, max_val)

    def _map_to_commarea(self, record: CustomerRecord, commarea: InquiryCommarea) -> None:
        """Maps VSAM record fields to Commarea output fields."""
        commarea.fail_code = '0'
        commarea.eye = record.eyecatcher
        commarea.scode = record.sort_code
        commarea.custno = record.customer_number
        commarea.name = record.name
        commarea.addr = record.address
        commarea.dob = record.date_of_birth
        commarea.credit_score = record.credit_score
        commarea.cs_review_dt = record.review_date

    def _handle_abend(self, error_code: str, commarea: InquiryCommarea) -> InquiryCommarea:
        """
        Emulates ABEND-HANDLING section.
        Specifically handles VSAM RLS 'Storm Drain' conditions.
        """
        if error_code in self.STORM_DRAIN_CODES:
            # Perform SYNCPOINT ROLLBACK
            try:
                self.vsam.rollback()
                commarea.success_flag = 'N'
                commarea.fail_code = '2'  # Code 2: Storm Drain handled
                return commarea
            except Exception:
                # If rollback fails, we must hard abend
                self._terminate_execution("HROL")

        # Non-storm drain abends
        self._terminate_execution(error_code)

    def _raise_critical_error(self, code: str, resp: int, resp2: int, key: dict) -> NoReturn:
        """Helper to simulate CICS ABEND with diagnostic info."""
        msg = f"Inquiry Error {code}: VSAM RESP={resp}, RESP2={resp2}, KEY={key}"
        print(msg) # Equivalent to DISPLAY in COBOL
        raise Exception(code)

    def _terminate_execution(self, abend_code: str) -> NoReturn:
        """Simulates EXEC CICS ABEND."""
        print(f"CRITICAL SYSTEM ABEND: {abend_code}")
        exit(1) # In a service, this would raise a specific SystemError or restart the task