from dataclasses import dataclass, field
from typing import Optional, Protocol, Union
from enum import StrEnum


class UpdateStatus(StrEnum):
    SUCCESS = "Y"
    FAILURE = "N"


@dataclass
class CustomerRecord:
    """Represents the VSAM Customer Record structure."""
    eye_catcher: str = ""
    sort_code: int = 0
    customer_number: int = 0
    name: str = ""
    address: str = ""
    date_of_birth: str = ""
    credit_score: int = 0
    review_date: str = ""


@dataclass
class CommArea:
    """Represents the DFHCOMMAREA for UPDCUST."""
    sort_code: int = 0
    customer_number: int = 0
    name: str = ""
    address: str = ""
    dob: str = ""
    credit_score: int = 0
    cs_review_date: str = ""
    eye_catcher: str = ""
    # Return fields
    update_success: UpdateStatus = UpdateStatus.FAILURE
    update_fail_code: str = ""


class VSAMProvider(Protocol):
    """Interface for VSAM-like data access with locking capabilities."""
    def read_for_update(self, file_name: str, key: str) -> Optional[CustomerRecord]: ...
    def rewrite(self, file_name: str, record: CustomerRecord) -> bool: ...
    def unlock(self, file_name: str, key: str) -> None: ...


class CustomerUpdateService:
    """
    Service to handle customer detail updates, migrating logic from COBOL UPDCUST.
    Maintains VSAM READ UPDATE locking semantics and specific error handling.
    """

    VALID_TITLES: set[str] = {
        "Professor", "Mr", "Mrs", "Miss", "Ms", "Dr", 
        "Drs", "Lord", "Sir", "Lady", ""
    }

    def __init__(self, data_provider: VSAMProvider):
        self.db = data_provider

    def execute_update(self, commarea: CommArea) -> CommArea:
        """
        Performs the customer update logic.
        
        Error Codes (commarea.update_fail_code):
        '1' - Record Not Found
        '2' - READ error/System error
        '3' - REWRITE error
        '4' - Validation: Name and Address both empty or start with space
        '5' - Validation: Invalid Title (Mapped from 'T' in legacy)
        """
        # 1. Validate Title
        # Equivalent to COBOL UNSTRING COMM-NAME DELIMITED BY SPACE
        title = commarea.name.strip().split(' ')[0] if commarea.name.strip() else ""
        
        if title not in self.VALID_TITLES:
            commarea.update_success = UpdateStatus.FAILURE
            commarea.update_fail_code = "5"  # Mapped from 'T' to fit 1-8 requirement
            return commarea

        # 2. Access VSAM Datastore
        # Key is Sort Code (6) + Customer Number (10)
        key = f"{commarea.sort_code:06d}{commarea.customer_number:010d}"
        
        try:
            # READ FILE('CUSTOMER') UPDATE
            ws_cust_data = self.db.read_for_update("CUSTOMER", key)
            
            if ws_cust_data is None:
                commarea.update_success = UpdateStatus.FAILURE
                commarea.update_fail_code = "1"
                return commarea

        except Exception:
            commarea.update_success = UpdateStatus.FAILURE
            commarea.update_fail_code = "2"
            return commarea

        # 3. Business Logic for Field Updates
        name_input = commarea.name or ""
        addr_input = commarea.address or ""
        
        name_is_blank = not name_input or name_input.startswith(" ")
        addr_is_blank = not addr_input or addr_input.startswith(" ")

        # Check if both are empty/invalid
        if name_is_blank and addr_is_blank:
            self.db.unlock("CUSTOMER", key)
            commarea.update_success = UpdateStatus.FAILURE
            commarea.update_fail_code = "4"
            return commarea

        # Update logic based on provided fields
        if name_is_blank:
            # Update address only
            ws_cust_data.address = addr_input
        elif addr_is_blank:
            # Update name only
            ws_cust_data.name = name_input
        else:
            # Update both
            ws_cust_data.name = name_input
            ws_cust_data.address = addr_input

        # 4. REWRITE Record
        try:
            success = self.db.rewrite("CUSTOMER", ws_cust_data)
            if not success:
                commarea.update_success = UpdateStatus.FAILURE
                commarea.update_fail_code = "3"
                return commarea
        except Exception:
            commarea.update_success = UpdateStatus.FAILURE
            commarea.update_fail_code = "3"
            return commarea

        # 5. Populate return values on success
        commarea.eye_catcher = ws_cust_data.eye_catcher
        commarea.sort_code = ws_cust_data.sort_code
        commarea.customer_number = ws_cust_data.customer_number
        commarea.name = ws_cust_data.name
        commarea.address = ws_cust_data.address
        commarea.dob = ws_cust_data.date_of_birth
        commarea.credit_score = ws_cust_data.credit_score
        commarea.cs_review_date = ws_cust_data.review_date
        
        commarea.update_success = UpdateStatus.SUCCESS
        commarea.update_fail_code = ""
        
        return commarea