import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Final, Optional
import threading

@dataclass
class CreditAgencyContainer:
    """
    Data structure representing the WS-CONT-IN COBOL layout.
    """
    eyecatcher: str = "CIPE"
    sort_code: str = "000000"
    account_number: str = "0000000000"
    name: str = ""
    address: str = ""
    date_of_birth: str = "01011900"  # DDMMYYYY
    credit_score: int = 0
    cs_review_date: str = "00000000"
    success_flag: str = "N"
    fail_code: str = " "

class CreditAgencyProcessor:
    """
    Legacy Migration: CRDTAGY5 Credit Scoring Logic.
    
    This class emulates the CICS Async API behavior including delays,
    randomized scoring, and transactional integrity (locking) during
    container updates.
    """

    # Error Code constants as per legacy requirements
    ERR_SUCCESS: Final[int] = 0
    ERR_DELAY_FAILED: Final[int] = 1
    ERR_CONTAINER_READ: Final[int] = 2
    ERR_SCORE_GENERATION: Final[int] = 3
    ERR_CONTAINER_WRITE: Final[int] = 4
    ERR_VALIDATION: Final[int] = 5
    ERR_LOCKING_FAILURE: Final[int] = 6
    ERR_SYSTEM_ABEND: Final[int] = 8

    def __init__(self, task_id: int):
        self.task_id = task_id
        self._lock = threading.Lock()
        # Simulation of CICS Channel/Container storage
        self._storage: Dict[str, Dict[str, CreditAgencyContainer]] = {}

    def _get_timestamp_data(self) -> Dict[str, str]:
        """Equivalent to CICS ASKTIME and FORMATTIME logic."""
        now = datetime.now()
        return {
            "date": now.strftime("%d.%m.%Y"),
            "time": now.strftime("%H:%M:%S"),
            "u_time": str(int(now.timestamp()))
        }

    def _handle_abend(self, abcode: str, resp: int, resp2: int, message: str) -> None:
        """
        Emulates EXEC CICS LINK PROGRAM('ABNDPROC').
        """
        ts = self._get_timestamp_data()
        error_log = (
            f"ABEND-{abcode} | RESP: {resp} | RESP2: {resp2} | "
            f"TIME: {ts['time']} | DATE: {ts['date']} | MSG: {message}"
        )
        # In a real migration, this would log to a centralized observability stack
        print(f"CRITICAL ERROR: {error_log}")

    def process_credit_request(self, channel_name: str, container_name: str) -> int:
        """
        Main logic execution for credit scoring.
        
        Returns:
            int: Return code (0-8)
        """
        # 1. Delay Logic: Generate random delay 1-3 seconds
        try:
            random.seed(self.task_id)
            delay_amt = random.uniform(1, 3)
            time.sleep(delay_amt)
        except Exception:
            self._handle_abend("PLOP", 99, 1, "The delay messed up!")
            return self.ERR_DELAY_FAILED

        # 2. Get Container (READ)
        # Using a lock to emulate VSAM READ UPDATE / Container serialization
        with self._lock:
            try:
                # Logic equivalent to EXEC CICS GET CONTAINER
                # In Python, we assume container is provided via a shared state or API
                container_data = self._retrieve_from_channel(channel_name, container_name)
                if not container_data:
                    return self.ERR_CONTAINER_READ
            except Exception as e:
                print(f"CRDTAGY5 - UNABLE TO GET CONTAINER. {e}")
                return self.ERR_CONTAINER_READ

            # 3. Business Logic: Generate Credit Score (1-999)
            try:
                # COBOL: RANDOM without seed uses the previous sequence
                new_score = random.randint(1, 999)
                container_data.credit_score = new_score
            except Exception:
                return self.ERR_SCORE_GENERATION

            # 4. Put Container (UPDATE)
            try:
                # Logic equivalent to EXEC CICS PUT CONTAINER
                success = self._persist_to_channel(channel_name, container_name, container_data)
                if not success:
                    raise IOError("Persistence failed")
            except Exception as e:
                print(f"CRDTAGY5- UNABLE TO PUT CONTAINER. {e}")
                return self.ERR_CONTAINER_WRITE

        return self.ERR_SUCCESS

    def _retrieve_from_channel(self, channel: str, container: str) -> Optional[CreditAgencyContainer]:
        """Internal helper to simulate CICS GET CONTAINER."""
        if channel in self._storage and container in self._storage[channel]:
            return self._storage[channel][container]
        return None

    def _persist_to_channel(self, channel: str, container: str, data: CreditAgencyContainer) -> bool:
        """Internal helper to simulate CICS PUT CONTAINER."""
        if channel not in self._storage:
            self._storage[channel] = {}
        self._storage[channel][container] = data
        return True

    def initialize_mock_data(self, channel: str, container: str, record: CreditAgencyContainer) -> None:
        """Utility method for setting up data in the emulated environment."""
        if channel not in self._storage:
            self._storage[channel] = {}
        self._storage[channel][container] = record