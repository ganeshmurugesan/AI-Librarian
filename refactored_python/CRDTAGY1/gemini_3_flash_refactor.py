import random
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final, Optional

@dataclass
class CreditContainer:
    """
    Represents the WS-CONT-IN data structure from the legacy COBOL system.
    Maintains the exact field lengths and types for data integrity.
    """
    eyecatcher: str = "CIPA"
    sort_code: int = 0  # PIC 9(6)
    account_number: int = 0  # PIC 9(10)
    name: str = ""  # PIC X(60)
    address: str = ""  # PIC X(160)
    date_of_birth: str = ""  # PIC 9(8) YYYYMMDD
    credit_score: int = 0  # PIC 999
    cs_review_date: str = ""  # PIC 9(8)
    success_flag: str = " "  # PIC X
    fail_code: str = " "  # PIC X

class CreditAgencyHandler:
    """
    Python implementation of CRDTAGY1.
    Handles random delays, credit score generation, and simulated 
    VSAM-style READ UPDATE locking on shared containers.
    """

    # Error Code Constants
    RC_SUCCESS: Final[int] = 1
    RC_DELAY_ERROR: Final[int] = 2
    RC_GET_CONTAINER_FAIL: Final[int] = 3
    RC_PUT_CONTAINER_FAIL: Final[int] = 4
    RC_ABEND_PROC_ERROR: Final[int] = 5
    RC_LOCK_TIMEOUT: Final[int] = 6
    RC_RESOURCE_NOT_FOUND: Final[int] = 7
    RC_DATA_INTEGRITY_ERROR: Final[int] = 8

    def __init__(self, task_id: int):
        self.task_id = task_id
        self.channel_name: str = "CIPCREDCHANN"
        self.container_name: str = "CIPA"
        self._lock = threading.RLock()  # Simulates VSAM READ UPDATE locking mechanism

    def process_credit_scoring(self, shared_storage: dict[str, CreditContainer]) -> int:
        """
        Main execution logic for credit scoring.
        
        :param shared_storage: Simulated CICS Channel/Container environment.
        :return: Integer status code (1-8).
        """
        try:
            # A010 - Generate random delay between 1 and 3 seconds
            # Based on COBOL: ((3 - 1) * RANDOM(SEED)) + 1
            random.seed(self.task_id)
            delay_amt = random.uniform(1.0, 3.0)
            
            try:
                time.sleep(delay_amt)
            except Exception:
                self._handle_abend("A010 - The delay messed up!", self.RC_DELAY_ERROR)
                return self.RC_DELAY_ERROR

            # Simulate EXEC CICS GET CONTAINER with READ UPDATE locking
            with self._lock:
                container_data = shared_storage.get(self.container_name)
                
                if container_data is None:
                    print(f"CRDTAGY1 - UNABLE TO GET CONTAINER. RESP=NOTFND")
                    return self.RC_GET_CONTAINER_FAIL

                # Perform Credit Score Logic
                # Logic: Generate score between 1 and 999
                new_credit_score = random.randint(1, 999)
                container_data.credit_score = new_credit_score

                # Simulate EXEC CICS PUT CONTAINER
                try:
                    shared_storage[self.container_name] = container_data
                except Exception:
                    print(f"CRDTAGY1 - UNABLE TO PUT CONTAINER.")
                    return self.RC_PUT_CONTAINER_FAIL

            return self.RC_SUCCESS

        except Exception as e:
            self._handle_abend(str(e), self.RC_ABEND_PROC_ERROR)
            return self.RC_ABEND_PROC_ERROR

    def _handle_abend(self, message: str, error_code: int) -> None:
        """
        Simulates the logic found in ABNDPROC/ABNDINFO-REC.
        """
        timestamp = datetime.now()
        abend_info = {
            "RESP": error_code,
            "TASKNO": self.task_id,
            "TIME": timestamp.strftime("%H:%M:%S"),
            "DATE": timestamp.strftime("%d.%m.%Y"),
            "FREEFORM": f"LOG: {message}"
        }
        print(f"*** ABEND INITIATED: {abend_info['FREEFORM']} ***")
        # In a real migration, this would log to a centralized telemetry service

    def populate_time_date(self) -> dict[str, str]:
        """
        Simulates CICS ASKTIME and FORMATTIME logic.
        """
        now = datetime.now()
        return {
            "WS-ORIG-DATE": now.strftime("%d%m%Y"),
            "WS-TIME-NOW": now.strftime("%H%M%S"),
            "WS-U-TIME": str(int(now.timestamp()))
        }