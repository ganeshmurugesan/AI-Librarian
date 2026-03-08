import random
import time
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import IntEnum

class CICSResponse(IntEnum):
    NORMAL = 0
    ERROR = 1
    NOT_AUTHORIZED = 2
    NOT_FOUND = 3
    DUPLICATE = 4
    END_OF_FILE = 5
    INVALID_REQUEST = 6
    PROGRAM_ERROR = 7
    TRANSACTION_ERROR = 8

@dataclass
class ContainerInput:
    eyecatcher: str
    sortcode: int
    number: int
    name: str
    address: str
    date_of_birth: str
    birth_day: int
    birth_month: int
    birth_year: int
    credit_score: int
    cs_review_date: str
    success: str
    fail_code: str

class CreditAgency:
    """
    A class to simulate a credit agency service that generates random credit scores
    with a simulated delay, mimicking legacy COBOL behavior with VSAM READ UPDATE locking.
    """

    def __init__(self):
        self.container_name = "CIPA"
        self.channel_name = "CIPCREDCHANN"
        self.seed = int(time.time() * 1000)  # Using current time as seed

    def _generate_delay(self) -> int:
        """Generate a random delay between 1 and 3 seconds."""
        random.seed(self.seed)
        delay = random.randint(1, 3)
        self.seed += 1  # Increment seed for next call
        return delay

    def _handle_cics_error(self, resp: CICSResponse, resp2: CICSResponse) -> None:
        """Handle CICS errors by raising an exception with appropriate error code."""
        error_map = {
            CICSResponse.ERROR: 1,
            CICSResponse.NOT_AUTHORIZED: 2,
            CICSResponse.NOT_FOUND: 3,
            CICSResponse.DUPLICATE: 4,
            CICSResponse.END_OF_FILE: 5,
            CICSResponse.INVALID_REQUEST: 6,
            CICSResponse.PROGRAM_ERROR: 7,
            CICSResponse.TRANSACTION_ERROR: 8
        }
        error_code = error_map.get(resp, 1)  # Default to 1 if not found
        raise RuntimeError(f"CICS Error: RESP={resp}, RESP2={resp2}, Error Code={error_code}")

    def _generate_credit_score(self) -> int:
        """Generate a random credit score between 1 and 999."""
        random.seed(self.seed)
        score = random.randint(1, 999)
        self.seed += 1  # Increment seed for next call
        return score

    def _simulate_vsam_lock(self, container: ContainerInput) -> None:
        """
        Simulate VSAM READ UPDATE locking by introducing a small delay.
        In a real implementation, this would involve actual file locking.
        """
        time.sleep(0.01)  # Simulate lock acquisition time

    def process_credit_request(self) -> Tuple[ContainerInput, Optional[int]]:
        """
        Process a credit request by:
        1. Simulating a random delay (0-3 seconds)
        2. Generating a random credit score
        3. Simulating VSAM READ UPDATE locking
        4. Returning the updated container and any error code

        Returns:
            Tuple[ContainerInput, Optional[int]]: The updated container and error code (1-8) if error occurred
        """
        try:
            # Step 1: Simulate delay
            delay = self._generate_delay()
            time.sleep(delay)

            # Step 2: Get container (simulated)
            # In a real implementation, this would involve actual CICS calls
            container = ContainerInput(
                eyecatcher="",
                sortcode=0,
                number=0,
                name="",
                address="",
                date_of_birth="",
                birth_day=0,
                birth_month=0,
                birth_year=0,
                credit_score=0,
                cs_review_date="",
                success="",
                fail_code=""
            )

            # Step 3: Generate credit score
            container.credit_score = self._generate_credit_score()

            # Step 4: Simulate VSAM lock
            self._simulate_vsam_lock(container)

            # Step 5: Put container back (simulated)
            # In a real implementation, this would involve actual CICS calls

            return container, None

        except RuntimeError as e:
            # Map the error to one of the specified error codes (1-8)
            error_code = int(str(e).split("Error Code=")[1]) if "Error Code=" in str(e) else 1
            return ContainerInput(
                eyecatcher="",
                sortcode=0,
                number=0,
                name="",
                address="",
                date_of_birth="",
                birth_day=0,
                birth_month=0,
                birth_year=0,
                credit_score=0,
                cs_review_date="",
                success="",
                fail_code=str(error_code)
            ), error_code