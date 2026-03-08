from dataclasses import dataclass
from typing import Final, Protocol, Optional
import enum

# Constants simulating the COPY SORTCODE REPLACING ... BY LITERAL-SORTCODE
LITERAL_SORTCODE: Final[str] = "X99001"

class StatusCode(enum.IntEnum):
    """
    Standard Return Codes for the GETSCODE Service.
    Maps to CICS EIBRESP/Custom application codes.
    """
    SUCCESS = 1
    NOT_FOUND = 2
    RECORD_LOCKED = 3
    IO_ERROR = 4
    DATA_EXCEPTION = 5
    NOT_AUTHORIZED = 6
    RESOURCE_UNAVAILABLE = 7
    UNKNOWN_ERROR = 8

@dataclass
class GetScodeCommarea:
    """
    Represents the DFHCOMMAREA structure defined in COPY GETSCODE.
    """
    sortcode: str = ""
    status_code: int = 0
    error_message: str = ""

class VsamStorageProvider(Protocol):
    """Protocol for VSAM-style file access handlers."""
    def read_for_update(self, key: str) -> Optional[str]: ...
    def release_lock(self, key: str) -> None: ...

class GetSCode:
    """
    Legacy Migration: GETSCODE (CICS/COBOL)
    
    This class handles the retrieval of sort codes, maintaining 
    transactional integrity via simulated VSAM READ UPDATE locking mechanisms.
    """

    def __init__(self, storage_provider: Optional[VsamStorageProvider] = None):
        self.storage_provider = storage_provider

    def execute(self, commarea: GetScodeCommarea) -> None:
        """
        Main entry point equivalent to PROCEDURE DIVISION USING DFHCOMMAREA.
        
        Performs the MOVE LITERAL-SORTCODE TO SORTCODE operation while
        enforcing the requested VSAM READ UPDATE locking logic.
        
        Args:
            commarea: The communication area instance passed from the caller.
        """
        try:
            # Simulate VSAM READ UPDATE logic
            # In a real migration, the 'key' would be derived from the commarea
            if self.storage_provider:
                record_key = "CURRENT_SORT_CONFIG"
                
                # Attempt to obtain a lock (READ UPDATE)
                record = self.storage_provider.read_for_update(record_key)
                
                if record is None:
                    commarea.status_code = StatusCode.NOT_FOUND
                    return

            # COBOL LOGIC: MOVE LITERAL-SORTCODE TO SORTCODE OF DFHCOMMAREA
            commarea.sortcode = LITERAL_SORTCODE
            commarea.status_code = StatusCode.SUCCESS

        except PermissionError:
            commarea.status_code = StatusCode.NOT_AUTHORIZED
        except TimeoutError:
            # Equivalent to EXEC CICS READ UPDATE results in ENQ failure
            commarea.status_code = StatusCode.RECORD_LOCKED
        except ConnectionError:
            commarea.status_code = StatusCode.RESOURCE_UNAVAILABLE
        except ValueError:
            commarea.status_code = StatusCode.DATA_EXCEPTION
        except OSError:
            commarea.status_code = StatusCode.IO_ERROR
        except Exception:
            commarea.status_code = StatusCode.UNKNOWN_ERROR
        finally:
            # Simulation of EXEC CICS RETURN (unlocking and returning control)
            if self.storage_provider:
                self.storage_provider.release_lock("CURRENT_SORT_CONFIG")

def main(request_data: GetScodeCommarea) -> GetScodeCommarea:
    """
    Helper function to mimic the CICS invocation.
    """
    program = GetSCode()
    program.execute(request_data)
    return request_data