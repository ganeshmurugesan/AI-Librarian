import random
import time
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class CreditAgencyResponse:
    """Data structure for credit agency response."""
    sortcode: int
    number: int
    name: str
    address: str
    date_of_birth: str
    credit_score: int
    review_date: str
    success: str
    fail_code: str

class CreditAgency:
    """Modern Python implementation of legacy COBOL credit agency program."""

    CONTAINER_NAME = "CIPE"
    CHANNEL_NAME = "CIPCREDCHANN"
    MAX_DELAY_SECONDS = 3
    MIN_CREDIT_SCORE = 1
    MAX_CREDIT_SCORE = 999

    def __init__(self):
        self.response_code: int = 0
        self.response_code2: int = 0

    def process_credit_request(self, input_data: CreditAgencyResponse) -> Tuple[int, Optional[CreditAgencyResponse]]:
        """
        Process credit request with random delay and score generation.

        Args:
            input_data: Input credit request data

        Returns:
            Tuple of (error_code, response_data)
            error_code: 0 for success, 1-8 for specific errors
        """
        # Generate random delay (0-3 seconds)
        delay_seconds = random.randint(0, self.MAX_DELAY_SECONDS)
        time.sleep(delay_seconds)

        # Generate random credit score (1-999)
        credit_score = random.randint(self.MIN_CREDIT_SCORE, self.MAX_CREDIT_SCORE)

        # Update response with new credit score
        response = CreditAgencyResponse(
            sortcode=input_data.sortcode,
            number=input_data.number,
            name=input_data.name,
            address=input_data.address,
            date_of_birth=input_data.date_of_birth,
            credit_score=credit_score,
            review_date=input_data.review_date,
            success="Y",
            fail_code=""
        )

        return (0, response)

    def handle_error(self, error_code: int, error_message: str) -> None:
        """
        Handle errors according to legacy error codes.

        Args:
            error_code: Error code (1-8)
            error_message: Detailed error message
        """
        # In a real implementation, this would log and handle errors
        print(f"Error {error_code}: {error_message}")
        raise RuntimeError(f"Credit agency error {error_code}: {error_message}")