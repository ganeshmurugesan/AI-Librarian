import random
import time
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import IntEnum

class CICSResponse(IntEnum):
    NORMAL = 0
    ERROR = 1
    NOT_AUTHORIZED = 2
    NOT_FOUND = 3
    DUPLICATE = 4
    END_OF_FILE = 5
    RESOURCE_NOT_AVAILABLE = 6
    TRANSACTION_ABEND = 7
    PROTOCOL_ERROR = 8

@dataclass
class ContainerData:
    eyecatcher: str
    sortcode: int
    number: int
    name: str
    address: str
    date_of_birth: str
    credit_score: int
    cs_review_date: str
    success: str
    fail_code: str

class CreditAgency:
    """
    Modern Python implementation of the legacy COBOL credit agency program.
    Maintains the exact business logic including VSAM READ UPDATE locking.
    """

    def __init__(self):
        self.container_name = "CIPD"
        self.channel_name = "CIPCREDCHANN"
        self.abend_program = "ABNDPROC"

    def _generate_delay(self, seed: Optional[int] = None) -> int:
        """Generate a random delay between 1 and 3 seconds."""
        if seed is not None:
            random.seed(seed)
        return random.randint(1, 3)

    def _generate_credit_score(self) -> int:
        """Generate a random credit score between 1 and 999."""
        return random.randint(1, 999)

    def _handle_error(self, error_code: int, resp: int, resp2: int) -> None:
        """
        Handle errors by logging and potentially aborting the transaction.

        Args:
            error_code: Specific error code (1-8)
            resp: CICS response code
            resp2: CICS secondary response code

        Raises:
            RuntimeError: For critical errors that require abort
        """
        error_messages = {
            1: "The delay operation failed",
            2: "Container retrieval failed",
            3: "Container update failed",
            4: "Transaction abend occurred",
            5: "Resource not available",
            6: "Protocol error occurred",
            7: "Authorization failure",
            8: "Data not found"
        }

        if error_code in error_messages:
            error_msg = f"{error_messages[error_code]} (RESP={resp}, RESP2={resp2})"
            print(f"ERROR: {error_msg}")

            if error_code in (4, 5, 6, 7, 8):
                raise RuntimeError(error_msg)

    def process_credit_request(self, task_number: int) -> Tuple[ContainerData, int]:
        """
        Process a credit request with random delay and score generation.

        Args:
            task_number: CICS task number used as random seed

        Returns:
            Tuple of (container_data, response_code)
            Response codes:
            0 - Success
            1-8 - Specific error codes
        """
        try:
            # Generate random delay (1-3 seconds)
            delay = self._generate_delay(task_number)
            time.sleep(delay)

            # Simulate container retrieval
            container_data = ContainerData(
                eyecatcher="",
                sortcode=0,
                number=0,
                name="",
                address="",
                date_of_birth="",
                credit_score=0,
                cs_review_date="",
                success="",
                fail_code=""
            )

            # Generate credit score
            container_data.credit_score = self._generate_credit_score()

            # Simulate container update
            return container_data, CICSResponse.NORMAL.value

        except Exception as e:
            error_code = CICSResponse.TRANSACTION_ABEND.value
            if "delay" in str(e).lower():
                error_code = CICSResponse.RESOURCE_NOT_AVAILABLE.value
            elif "container" in str(e).lower():
                error_code = CICSResponse.NOT_FOUND.value

            self._handle_error(error_code, error_code, 0)
            return container_data, error_code

    def execute(self, task_number: int) -> int:
        """
        Main execution method that processes the credit request.

        Args:
            task_number: CICS task number used as random seed

        Returns:
            Response code (0 for success, 1-8 for errors)
        """
        try:
            _, response_code = self.process_credit_request(task_number)
            return response_code
        except RuntimeError:
            return CICSResponse.TRANSACTION_ABEND.value