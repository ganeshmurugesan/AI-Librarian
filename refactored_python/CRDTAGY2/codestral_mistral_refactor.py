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
    END_OF_DATA = 5
    INVALID_REQUEST = 6
    PROGRAM_ERROR = 7
    TRANSACTION_ABEND = 8

@dataclass
class ContainerInput:
    eyecatcher: str
    sortcode: int
    number: int
    name: str
    address: str
    date_of_birth: int
    credit_score: int
    cs_review_date: int
    success: str
    fail_code: str

    @property
    def birth_day(self) -> int:
        return (self.date_of_birth // 10000) % 100

    @property
    def birth_month(self) -> int:
        return (self.date_of_birth // 100) % 100

    @property
    def birth_year(self) -> int:
        return self.date_of_birth % 10000

class CreditAgency:
    def __init__(self):
        self.container_name = "CIPB"
        self.channel_name = "CIPCREDCHANN"
        self.seed = random.randint(0, 2**32 - 1)

    def _handle_error(self, resp: int, resp2: int, context: str) -> None:
        """Handle CICS error responses and raise appropriate exceptions."""
        if resp != CICSResponse.NORMAL:
            error_map = {
                CICSResponse.ERROR: "General error",
                CICSResponse.NOT_AUTHORIZED: "Not authorized",
                CICSResponse.NOT_FOUND: "Not found",
                CICSResponse.DUPLICATE: "Duplicate record",
                CICSResponse.END_OF_DATA: "End of data",
                CICSResponse.INVALID_REQUEST: "Invalid request",
                CICSResponse.PROGRAM_ERROR: "Program error",
                CICSResponse.TRANSACTION_ABEND: "Transaction abend"
            }
            error_msg = error_map.get(resp, f"Unknown error code {resp}")
            raise RuntimeError(f"{context}: {error_msg} (RESP2={resp2})")

    def _delay(self, seconds: int) -> None:
        """Simulate CICS DELAY operation with error handling."""
        try:
            time.sleep(seconds)
        except Exception as e:
            self._handle_error(CICSResponse.PROGRAM_ERROR, 0, "Delay operation failed")

    def _get_container(self) -> ContainerInput:
        """Simulate CICS GET CONTAINER operation."""
        # In a real implementation, this would interact with the container system
        # For this example, we'll return a dummy container
        return ContainerInput(
            eyecatcher="DUMMY",
            sortcode=123456,
            number=1234567890,
            name="JOHN DOE",
            address="123 MAIN ST",
            date_of_birth=19800101,
            credit_score=0,
            cs_review_date=20230101,
            success="Y",
            fail_code=""
        )

    def _put_container(self, container: ContainerInput) -> None:
        """Simulate CICS PUT CONTAINER operation."""
        # In a real implementation, this would update the container
        pass

    def process_credit_request(self) -> Tuple[int, Optional[str]]:
        """
        Process a credit request with random delay and score generation.

        Returns:
            Tuple of (credit_score, error_message) where error_message is None on success.
        """
        try:
            # Generate random delay between 0-3 seconds
            delay_seconds = random.randint(0, 3)
            self._delay(delay_seconds)

            # Get container data
            container = self._get_container()

            # Generate random credit score (1-999)
            container.credit_score = random.randint(1, 999)

            # Update container
            self._put_container(container)

            return (container.credit_score, None)

        except RuntimeError as e:
            # Map specific error codes to return codes 1-8
            if "General error" in str(e):
                return (0, "1")
            elif "Not authorized" in str(e):
                return (0, "2")
            elif "Not found" in str(e):
                return (0, "3")
            elif "Duplicate record" in str(e):
                return (0, "4")
            elif "End of data" in str(e):
                return (0, "5")
            elif "Invalid request" in str(e):
                return (0, "6")
            elif "Program error" in str(e):
                return (0, "7")
            elif "Transaction abend" in str(e):
                return (0, "8")
            else:
                return (0, "7")  # Default to program error

        except Exception:
            return (0, "7")  # Program error for unexpected exceptions