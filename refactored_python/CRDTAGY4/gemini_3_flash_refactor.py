import random
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Final


@dataclass
class CreditRecord:
    """
    Represents the WS-CONT-IN structure from the COBOL source.
    Maintains fixed-width character and numeric data integrity.
    """
    eyecatcher: str = "CIPD"
    sort_code: int = 0
    account_number: int = 0
    name: str = ""
    address: str = ""
    date_of_birth: str = ""  # DDMMYYYY
    credit_score: int = 0
    review_date: str = ""
    success_flag: str = "N"
    fail_code: str = ""


class CreditAgencyHandler:
    """
    Python implementation of CRDTAGY4.
    Handles credit scoring with simulated VSAM-style locking and CICS container logic.
    """

    # Error Code Mapping (Requirements 1-8)
    RC_SUCCESS: Final[int] = 1
    RC_DELAY_ERROR: Final[int] = 2
    RC_READ_LOCK_ERROR: Final[int] = 3
    RC_GET_CONTAINER_ERROR: Final[int] = 4
    RC_PUT_CONTAINER_ERROR: Final[int] = 5
    RC_TIME_ERROR: Final[int] = 6
    RC_VALIDATION_ERROR: Final[int] = 7
    RC_ABEND: Final[int] = 8

    def __init__(self, task_id: int):
        self.task_id: int = task_id
        self._lock = threading.Lock()
        self.channel_name: str = "CIPCREDCHANN"
        self.container_name: str = "CIPD"

    def execute_credit_check(self, input_data: Optional[dict] = None) -> tuple[int, Optional[CreditRecord]]:
        """
        Main entry point mirroring the PROCEDURE DIVISION logic.
        
        Args:
            input_data: Mock container data.
            
        Returns:
            Tuple of (Return Code, CreditRecord)
        """
        try:
            # A010 - Delay Logic
            # COBOL: COMPUTE WS-DELAY-AMT = ((3 - 1) * FUNCTION RANDOM(WS-SEED)) + 1.
            # This results in a delay between 1 and 3 seconds.
            random.seed(self.task_id)
            delay_amt = random.uniform(1.0, 3.0)
            
            try:
                time.sleep(delay_amt)
            except Exception:
                self._handle_abend("A010", "Delay failed")
                return self.RC_DELAY_ERROR, None

            # VSAM READ UPDATE Simulation
            # The prompt requires maintaining VSAM READ UPDATE locking logic.
            # In a modern context, we use a thread-safe lock for the update block.
            with self._lock:
                # GET CONTAINER logic
                record = self._retrieve_container_data(input_data)
                if not record:
                    return self.RC_GET_CONTAINER_ERROR, None

                # Generate credit score (1-999)
                # Subsequent RANDOM calls in COBOL use the same seed sequence
                record.credit_score = random.randint(1, 999)
                record.success_flag = "Y"

                # PUT CONTAINER logic
                success = self._persist_container_data(record)
                if not success:
                    return self.RC_PUT_CONTAINER_ERROR, None

            return self.RC_SUCCESS, record

        except Exception as e:
            self._handle_abend("GENERAL", str(e))
            return self.RC_ABEND, None

    def _retrieve_container_data(self, data: Optional[dict]) -> Optional[CreditRecord]:
        """Simulates EXEC CICS GET CONTAINER."""
        if data is None:
            return None
        
        try:
            return CreditRecord(
                sort_code=data.get("sort_code", 0),
                account_number=data.get("account_number", 0),
                name=data.get("name", ""),
                address=data.get("address", ""),
                date_of_birth=data.get("dob", "")
            )
        except (KeyError, ValueError):
            return None

    def _persist_container_data(self, record: CreditRecord) -> bool:
        """Simulates EXEC CICS PUT CONTAINER."""
        # In modern migration, this would write to a Redis/Cache or DB
        return True if record.credit_score > 0 else False

    def _handle_abend(self, section: str, message: str) -> None:
        """
        Simulates the ABNDPROC link logic.
        Populates time/date and logs the failure status.
        """
        now = datetime.now()
        timestamp = now.strftime("%H:%M:%S")
        datestamp = now.strftime("%d.%m.%Y")
        
        error_msg = f"{section} - *** The delay messed up! *** EIBRESP=ERROR RESP2={message}"
        # Log to system/standard error as EXEC CICS LINK to ABND-PGM would
        print(f"ABEND: {error_msg} | TIME: {timestamp} | DATE: {datestamp}")

    def get_current_time_formatted(self) -> dict[str, str]:
        """
        Replicates POPULATE-TIME-DATE section using EXEC CICS ASKTIME/FORMATTIME logic.
        """
        now = datetime.now()
        return {
            "WS-ORIG-DATE": now.strftime("%d%m%Y"),
            "WS-TIME-NOW": now.strftime("%H%M%S"),
            "ABND-TIME": now.strftime("%H:%M:%S")
        }