import random
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum, auto
from datetime import datetime

class CICSResponse(Enum):
    NORMAL = auto()
    SYSIDERR = auto()
    NOTFND = auto()

class CustomerErrorCode(Enum):
    NOT_FOUND = '1'
    VSAM_ERROR = '2'
    DB2_ERROR = '3'
    IMS_ERROR = '4'
    NCS_ERROR = '5'
    INVALID_INPUT = '6'
    SYSTEM_ERROR = '7'
    UNKNOWN_ERROR = '8'

@dataclass
class CustomerRecord:
    eyecatcher: str
    sort_code: int
    customer_number: int
    name: str
    address: str
    date_of_birth: str
    credit_score: int
    cs_review_date: str

class InqCust:
    def __init__(self):
        self.inq_success = False
        self.inq_fail_cd = '0'
        self.customer_record: Optional[CustomerRecord] = None
        self.vsam_retries = 0
        self.max_retries = 100
        self.max_customer_retries = 1000
        self.highest_customer_number = 0

    def process(self, customer_number: int, sort_code: int) -> Tuple[bool, str]:
        """Process customer inquiry request.

        Args:
            customer_number: The customer number to look up
            sort_code: The sort code for the customer

        Returns:
            Tuple of (success_flag, error_code)
        """
        self.inq_success = False
        self.inq_fail_cd = '0'

        # Handle special customer numbers
        if customer_number == 0 or customer_number == 9999999999:
            success = self._get_last_customer_number(sort_code)
            if not success:
                return (False, CustomerErrorCode.NCS_ERROR.value)
            if customer_number == 0:
                customer_number = self._generate_random_customer_number()

        # Read customer record from VSAM
        success = self._read_customer_vsam(sort_code, customer_number)
        if not success:
            return (False, self.inq_fail_cd)

        # Prepare response
        if self.customer_record:
            self.inq_success = True
            self.inq_fail_cd = '0'

        return (self.inq_success, self.inq_fail_cd)

    def _get_last_customer_number(self, sort_code: int) -> bool:
        """Get the last customer number from VSAM.

        Args:
            sort_code: The sort code to search for

        Returns:
            bool: True if successful, False otherwise
        """
        # Simulate VSAM STARTBR and READPREV operations
        try:
            # In a real implementation, this would interact with VSAM
            # For this example, we'll simulate the behavior
            self.highest_customer_number = 999999999  # Simulated highest customer number
            return True
        except Exception:
            self.inq_fail_cd = CustomerErrorCode.VSAM_ERROR.value
            return False

    def _generate_random_customer_number(self) -> int:
        """Generate a random customer number.

        Returns:
            int: Random customer number
        """
        if self.highest_customer_number == 0:
            self._get_last_customer_number(0)  # Default sort code

        return random.randint(1, self.highest_customer_number)

    def _read_customer_vsam(self, sort_code: int, customer_number: int) -> bool:
        """Read customer record from VSAM.

        Args:
            sort_code: The sort code to search for
            customer_number: The customer number to look up

        Returns:
            bool: True if successful, False otherwise
        """
        exit_vsam_read = False
        vsam_retried = False

        while not exit_vsam_read:
            # Simulate VSAM READ operation
            try:
                # In a real implementation, this would interact with VSAM
                # For this example, we'll simulate the behavior
                if customer_number == 0:
                    # For random customer, we might not find a record
                    if self.vsam_retries < self.max_customer_retries:
                        customer_number = self._generate_random_customer_number()
                        self.vsam_retries += 1
                        continue
                    else:
                        self.inq_fail_cd = CustomerErrorCode.NOT_FOUND.value
                        return False

                # Simulate successful read
                self.customer_record = CustomerRecord(
                    eyecatcher="CUST",
                    sort_code=sort_code,
                    customer_number=customer_number,
                    name="John Doe",
                    address="123 Main St",
                    date_of_birth="01/01/1980",
                    credit_score=750,
                    cs_review_date="01/01/2023"
                )
                exit_vsam_read = True
                return True

            except Exception as e:
                if str(e) == "SYSIDERR":
                    # Handle SYSIDERR with retries
                    if self.vsam_retries < self.max_retries:
                        self.vsam_retries += 1
                        continue
                    else:
                        self.inq_fail_cd = CustomerErrorCode.VSAM_ERROR.value
                        return False
                elif str(e) == "NOTFND":
                    if customer_number == 0:
                        if self.vsam_retries < self.max_customer_retries:
                            customer_number = self._generate_random_customer_number()
                            self.vsam_retries += 1
                            continue
                        else:
                            self.inq_fail_cd = CustomerErrorCode.NOT_FOUND.value
                            return False
                    elif customer_number == 9999999999 and not vsam_retried:
                        success = self._get_last_customer_number(sort_code)
                        if success:
                            customer_number = self.highest_customer_number
                            vsam_retried = True
                            continue
                        else:
                            self.inq_fail_cd = CustomerErrorCode.VSAM_ERROR.value
                            return False
                    else:
                        # Return initialized record for not found
                        self.customer_record = CustomerRecord(
                            eyecatcher="",
                            sort_code=sort_code,
                            customer_number=customer_number,
                            name="",
                            address="",
                            date_of_birth="",
                            credit_score=0,
                            cs_review_date=""
                        )
                        self.inq_fail_cd = CustomerErrorCode.NOT_FOUND.value
                        exit_vsam_read = True
                        return False
                else:
                    # Handle other errors
                    self._handle_vsam_error(sort_code, customer_number, str(e), vsam_retried)
                    return False

        return False

    def _handle_vsam_error(self, sort_code: int, customer_number: int, error_code: str, retried: bool) -> None:
        """Handle VSAM errors and potentially abort.

        Args:
            sort_code: The sort code that caused the error
            customer_number: The customer number that caused the error
            error_code: The error code received
            retried: Whether this was a retry attempt
        """
        # In a real implementation, this would log the error and potentially abort
        print(f"VSAM Error: {error_code} for customer {customer_number} in sort code {sort_code}")
        if retried:
            print("On retry attempt")

        # For this example, we'll just set the error code
        self.inq_fail_cd = CustomerErrorCode.VSAM_ERROR.value