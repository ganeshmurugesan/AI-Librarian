import random
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class ContainerData:
    """
    Python representation of the WS-CONT-IN COBOL structure.
    Maintains the fixed-width nature of the legacy record.
    """
    eyecatcher: str = "CIPB"
    sort_code: int = 0
    account_number: int = 0
    name: str = ""
    address: str = ""
    date_of_birth: str = ""  # YYYYMMDD
    credit_score: int = 0
    review_date: str = ""
    success_flag: str = "N"
    fail_code: str = " "


class CreditAgencyService:
    """
    Migration of CRDTAGY2 COBOL program.
    Simulates a credit scoring agency with random delays and VSAM-style record locking.
    """

    def __init__(self):
        # Simulated VSAM KSDS or CICS Channel Storage
        self._storage: Dict[str, ContainerData] = {}
        # Mutex to simulate VSAM ENQUEUE / READ UPDATE locking
        self._lock = threading.Lock()
        
        # Mapping return codes to match legacy requirements
        self.RC_SUCCESS = 1
        self.RC_CONTAINER_NOT_FOUND = 2
        self.RC_DELAY_FAILURE = 3
        self.RC_LENGTH_MISMATCH = 4
        self.RC_LOCK_ERROR = 5
        self.RC_CALCULATION_ERROR = 6
        self.RC_PUT_FAILURE = 7
        self.RC_ABEND = 8

    def process_credit_request(
        self, 
        channel_name: str, 
        container_name: str, 
        task_id: int
    ) -> int:
        """
        Executes the business logic: Delay -> Read -> Calculate -> Write.
        
        Args:
            channel_name: The CICS Channel identifier.
            container_name: The CICS Container identifier.
            task_id: Equivalent to EIBTASKN for random seeding.
            
        Returns:
            int: Result code (1-8).
        """
        try:
            # 1. Generate random delay (0-3 seconds)
            # COBOL: COMPUTE WS-DELAY-AMT = ((3 - 1) * FUNCTION RANDOM(WS-SEED)) + 1
            local_rng = random.Random(task_id)
            delay_seconds = local_rng.randint(1, 3)
            
            try:
                time.sleep(delay_seconds)
            except Exception:
                return self.RC_DELAY_FAILURE

            # 2. Simulate GET CONTAINER with READ UPDATE locking logic
            # In CICS/VSAM terms, we lock the record before modification
            with self._lock:
                # Simulate EXEC CICS GET CONTAINER
                storage_key = f"{channel_name}_{container_name}"
                if storage_key not in self._storage:
                    return self.RC_CONTAINER_NOT_FOUND
                
                record = self._storage[storage_key]

                # 3. Generate Credit Score (1-999)
                # COBOL: COMPUTE WS-NEW-CREDSCORE = ((999 - 1) * FUNCTION RANDOM) + 1
                new_score = local_rng.randint(1, 999)
                
                # Update record fields
                record.credit_score = new_score
                record.success_flag = "Y"
                
                # 4. Simulate EXEC CICS PUT CONTAINER
                try:
                    self._storage[storage_key] = record
                except Exception:
                    return self.RC_PUT_FAILURE

            return self.RC_SUCCESS

        except KeyError:
            return self.RC_CONTAINER_NOT_FOUND
        except PermissionError:
            return self.RC_LOCK_ERROR
        except Exception:
            # Equivalent to EXEC CICS ABEND
            return self.RC_ABEND

    def initialize_mock_data(self, channel: str, container: str, data: ContainerData) -> None:
        """Helper to populate the simulated CICS storage."""
        key = f"{channel}_{container}"
        self._storage[key] = data

    def _populate_time_date(self) -> Dict[str, str]:
        """
        Internal utility simulating EXEC CICS ASKTIME and FORMATTIME.
        """
        now = datetime.now()
        return {
            "ABND_DATE": now.strftime("%d%m%Y"),
            "ABND_TIME": now.strftime("%H:%M:%S"),
            "WS_U_TIME": str(int(now.timestamp()))
        }

    def get_container_data(self, channel: str, container: str) -> Optional[ContainerData]:
        """Accessor to retrieve current state of processed container."""
        return self._storage.get(f"{channel}_{container}")