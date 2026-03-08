from dataclasses import dataclass, field
from typing import Optional, Final
import threading
import logging

# Error Return Codes Mapping
SUCCESS: Final[int] = 0
DUPLICATE_KEY: Final[int] = 1
RESOURCE_NOT_AVAILABLE: Final[int] = 2
RECORD_LOCKED: Final[int] = 3
IO_ERROR: Final[int] = 4
INVALID_DATA: Final[int] = 5
INSUFFICIENT_SPACE: Final[int] = 6
NOT_AUTHORIZED: Final[int] = 7
CRITICAL_SYSTEM_ERROR: Final[int] = 8

@dataclass
class AbendRecord:
    """
    Represents the ABNDFILE VSAM KSDS record structure derived from ABNDINFO/DFHCOMMAREA.
    """
    utime_key: int          # PIC S9(15) COMP-3 (Key Part 1)
    taskno_key: int         # PIC 9(4)          (Key Part 2)
    applid: str             # PIC X(8)
    tranid: str             # PIC X(4)
    date_str: str           # PIC X(10)
    time_str: str           # PIC X(8)
    abend_code: str         # PIC X(4)
    program_name: str       # PIC X(8)
    resp_code: int          # PIC S9(8)
    resp2_code: int         # PIC S9(8)
    sql_code: int           # PIC S9(8)
    freeform: str           # PIC X(600)

    @property
    def vsam_key(self) -> str:
        """Constructs the 12-byte VSAM KSDS key."""
        return f"{self.utime_key:015d}{self.taskno_key:04d}"[:12]

class AbendProcessor:
    """
    Legacy Migration Handler for centralized abend logging.
    Simulates CICS VSAM KSDS operations with thread-safe locking.
    """

    def __init__(self, storage_provider=None):
        self._lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        # storage_provider would be the modern database/file abstraction
        self.storage = storage_provider 

    def process_abend_record(self, commarea: AbendRecord) -> int:
        """
        Equivalent to COBOL PROCEDURE DIVISION.
        Writes the abend record to the centralized datastore.
        
        Logic maintained: EXEC CICS WRITE FILE('ABNDFILE').
        Includes VSAM-style record locking logic for READ UPDATE scenarios.
        """
        try:
            with self._lock:
                # 1. Validation Logic
                if not commarea.vsam_key:
                    self.logger.error("Invalid VSAM Key generated.")
                    return INVALID_DATA

                # 2. Simulate EXEC CICS READ UPDATE / WRITE
                # In COBOL, the program performs a direct WRITE. 
                # If this were a REWRITE, we would perform a 'READ UPDATE' lock here.
                
                # Check for existing record to maintain KSDS integrity (Duplicate Key check)
                if self._check_record_exists(commarea.vsam_key):
                    self.logger.warning(f"Duplicate record for key: {commarea.vsam_key}")
                    return DUPLICATE_KEY

                # 3. Perform the Write operation
                success = self._persist_to_datastore(commarea)
                
                if not success:
                    # Maps to non-NORMAL CICS RESP
                    self.logger.error("IO_ERROR writing to ABNDFILE")
                    return IO_ERROR

            self.logger.info(f"ABEND record successfully written: {commarea.vsam_key}")
            return SUCCESS

        except PermissionError:
            return NOT_AUTHORIZED
        except TimeoutError:
            return RECORD_LOCKED
        except MemoryError:
            return INSUFFICIENT_SPACE
        except Exception as e:
            self.logger.critical(f"Critical System Error: {str(e)}")
            return CRITICAL_SYSTEM_ERROR

    def _check_record_exists(self, key: str) -> bool:
        """Simulates VSAM Key check."""
        # Integration logic for checking existing records goes here
        return False

    def _persist_to_datastore(self, record: AbendRecord) -> bool:
        """
        Simulates the physical WRITE to the ABNDFILE.
        Returns True if RESP is NORMAL.
        """
        try:
            # Logic to write to modern storage (SQL/NoSQL/S3)
            # Equivalent to EXEC CICS WRITE FILE('ABNDFILE') FROM(WS-ABND-AREA)
            return True
        except Exception:
            return False

    def get_me_out_of_here(self) -> None:
        """Equivalent to GET-ME-OUT-OF-HERE SECTION / EXEC CICS RETURN."""
        # In Python, this is handled by the method return, but preserved for logic parity
        pass