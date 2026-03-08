import asyncio
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Final


@dataclass
class CreditContainer:
    """Represents the WS-CONT-IN COBOL structure."""
    eyecatcher: str = "CIPC"
    sort_code: int = 0
    number: int = 0
    name: str = ""
    address: str = ""
    birth_day: int = 0
    birth_month: int = 0
    birth_year: int = 0
    credit_score: int = 0
    review_date: int = 0
    success: str = ""
    fail_code: str = ""


class CreditAgencyProcessor:
    """
    Modern Python implementation of the CRDTAGY3 COBOL program.
    Handles credit scoring with simulated CICS async delays and VSAM-style locking logic.
    """

    # Return Codes
    RC_SUCCESS: Final[int] = 1
    RC_DELAY_FAILURE: Final[int] = 2
    RC_GET_CONTAINER_FAILURE: Final[int] = 3
    RC_PUT_CONTAINER_FAILURE: Final[int] = 4
    RC_VALIDATION_FAILURE: Final[int] = 5
    RC_LOCKING_FAILURE: Final[int] = 6
    RC_RESOURCE_TIMEOUT: Final[int] = 7
    RC_ABEND_GENERAL: Final[int] = 8

    CHANNEL_NAME: Final[str] = "CIPCREDCHANN"
    CONTAINER_NAME: Final[str] = "CIPC"

    def __init__(self, task_number: int):
        self.task_number: int = task_number
        # Seed the random generator using the task number (EIBTASKN)
        random.seed(self.task_number)
        self._lock = asyncio.Lock()

    async def process_credit_request(self) -> int:
        """
        Main execution logic maintaining COBOL sequence:
        1. Random Delay
        2. Get Container (Read Update Lock)
        3. Compute Score
        4. Put Container (Release Lock)
        """
        try:
            # 1. Generate random delay (1-3 seconds as per COBOL logic: (3-1)*RND + 1)
            delay_seconds = (random.random() * 2) + 1
            
            try:
                await asyncio.sleep(delay_seconds)
            except Exception:
                await self._handle_abend("A010", "Delay failure")
                return self.RC_DELAY_FAILURE

            # 2. Simulate VSAM READ UPDATE Locking behavior
            # In a modern context, this ensures atomicity of the GET/PUT cycle
            async with self._lock:
                container_data = await self._get_container_data()
                if not container_data:
                    return self.RC_GET_CONTAINER_FAILURE

                # 3. Generate Credit Score (1-999)
                new_score = int((random.random() * 998) + 1)
                container_data.credit_score = new_score

                # 4. Put Container
                success = await self._put_container_data(container_data)
                if not success:
                    return self.RC_PUT_CONTAINER_FAILURE

            return self.RC_SUCCESS

        except Exception as e:
            print(f"CRDTAGY3- Unexpected Error: {e}")
            return self.RC_ABEND_GENERAL

    async def _get_container_data(self) -> Optional[CreditContainer]:
        """
        Simulates EXEC CICS GET CONTAINER.
        In a real migration, this would interface with a Redis cache, 
        CICS TS 7.1+ API, or a DB2 state table.
        """
        try:
            # Simulation of retrieval logic
            return CreditContainer(
                sort_code=123456,
                number=9876543210,
                name="JOHN DOE"
            )
        except Exception as e:
            print(f"CRDTAGY3- UNABLE TO GET CONTAINER. ERR={e}")
            return None

    async def _put_container_data(self, data: CreditContainer) -> bool:
        """
        Simulates EXEC CICS PUT CONTAINER.
        Persists the modified credit score back to the async channel.
        """
        try:
            # Logic to persist container data
            return True
        except Exception as e:
            print(f"CRDTAGY3- UNABLE TO PUT CONTAINER. ERR={e}")
            return False

    async def _handle_abend(self, section: str, message: str) -> None:
        """
        Simulates the ABNDPROC link and EXEC CICS ABEND.
        Captures state information similar to the ABNDINFO-REC structure.
        """
        timestamp = datetime.now()
        abend_info = {
            "pgm": "CRDTAGY3",
            "section": section,
            "task": self.task_number,
            "time": timestamp.strftime("%H:%M:%S"),
            "date": timestamp.strftime("%d.%m.%Y"),
            "msg": message,
            "code": "PLOP"
        }
        # Log error in standard legacy format
        print(f"*** {abend_info['section']} - {abend_info['msg']} ***")
        print(f"ABEND CODE: {abend_info['code']} TASK: {abend_info['task']}")


if __name__ == "__main__":
    # Example usage mimicking CICS Task invocation
    processor = CreditAgencyProcessor(task_number=12345)
    result = asyncio.run(processor.process_credit_request())
    exit(result)