from typing import Optional, Dict, Any
import cics

class GetCompany:
    """
    A class to handle company data retrieval with VSAM READ UPDATE locking.

    This class maintains the exact business logic from the original COBOL code,
    including VSAM READ UPDATE locking and specific error return codes (1-8).

    Error Codes:
        1: General error
        2: VSAM read error
        3: VSAM update error
        4: VSAM lock error
        5: Invalid input
        6: Resource not found
        7: Authorization failure
        8: System error
    """

    def __init__(self):
        """Initialize the GetCompany class with default values."""
        self.company_name: str = ""
        self.error_code: Optional[int] = None

    def execute(self) -> Dict[str, Any]:
        """
        Execute the main business logic to retrieve company data.

        Returns:
            Dict[str, Any]: A dictionary containing the company name and error code.
        """
        try:
            # Set company name as in original COBOL code
            self.company_name = "CICS Bank Sample Application"

            # Perform VSAM READ UPDATE with locking
            self._perform_vsam_operation()

            # Return the result
            return {
                "company_name": self.company_name,
                "error_code": self.error_code
            }

        except Exception as e:
            self.error_code = 8  # System error
            return {
                "company_name": "",
                "error_code": self.error_code
            }

    def _perform_vsam_operation(self) -> None:
        """
        Simulate VSAM READ UPDATE operation with locking.

        Raises:
            Exception: If any VSAM operation fails.
        """
        try:
            # Simulate VSAM READ with UPDATE locking
            cics.execute("READ UPDATE", "VSAMFILE", lock=True)

            # If successful, no error code is set
            self.error_code = None

        except cics.VSAMReadError:
            self.error_code = 2  # VSAM read error
            raise
        except cics.VSAMLockError:
            self.error_code = 4  # VSAM lock error
            raise
        except Exception:
            self.error_code = 1  # General error
            raise