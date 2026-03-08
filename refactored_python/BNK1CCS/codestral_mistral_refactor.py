from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple, Union
import datetime
import logging

# Constants for CICS response codes
class CICSResponse(Enum):
    NORMAL = 0
    UCTRAN = 1
    TRANIDONLY = 2
    NOUCTRAN = 3

# Error codes mapping
ERROR_CODES = {
    1: "Customer is too old",
    2: "Customer D.O.B. is in the future",
    3: "Customer D.O.B. is invalid",
    4: "Invalid key pressed",
    5: "Missing expected data",
    6: "Non-numeric date component",
    7: "Invalid date range",
    8: "Terminal operation failed"
}

class CustomerCreationError(Exception):
    """Custom exception for customer creation errors"""
    def __init__(self, error_code: int):
        self.error_code = error_code
        super().__init__(f"Customer creation failed: {ERROR_CODES.get(error_code, 'Unknown error')}")

@dataclass
class CustomerData:
    """Data structure for customer information"""
    title: str
    first_name: str
    middle_name: str
    surname: str
    address_line1: str
    address_line2: str
    address_line3: str
    birth_day: int
    birth_month: int
    birth_year: int
    sort_code: Optional[int] = None
    customer_number: Optional[int] = None
    credit_score: Optional[int] = None
    review_date: Optional[datetime.date] = None

class TerminalSettings:
    """Class to manage terminal settings"""
    def __init__(self):
        self.original_uctrans: int = 0
        self.current_uctrans: int = 0

    def store_terminal_settings(self) -> None:
        """Store the current terminal settings"""
        # In a real implementation, this would interact with CICS
        self.original_uctrans = self.current_uctrans

    def restore_terminal_settings(self) -> None:
        """Restore the original terminal settings"""
        # In a real implementation, this would interact with CICS
        self.current_uctrans = self.original_uctrans

class CustomerCreator:
    """Main class for customer creation logic"""

    VALID_TITLES = {
        'MR', 'MRS', 'MISS', 'MS', 'DR', 'PROFESSOR',
        'DRS', 'LORD', 'SIR', 'LADY'
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.terminal_settings = TerminalSettings()
        self.customer_data: Optional[CustomerData] = None
        self.error_message: str = ""

    def validate_customer_data(self, input_data: dict) -> bool:
        """Validate customer input data"""
        try:
            # Validate title
            title = input_data.get('title', '').strip().upper()
            if not title or title not in self.VALID_TITLES:
                self.error_message = "Invalid title provided"
                return False

            # Validate names
            first_name = input_data.get('first_name', '').strip()
            if not first_name:
                self.error_message = "First name is required"
                return False

            surname = input_data.get('surname', '').strip()
            if not surname:
                self.error_message = "Surname is required"
                return False

            # Validate address
            address_line1 = input_data.get('address_line1', '').strip()
            if not address_line1:
                self.error_message = "Address line 1 is required"
                return False

            # Validate date of birth
            try:
                birth_day = int(input_data.get('birth_day', '0'))
                birth_month = int(input_data.get('birth_month', '0'))
                birth_year = int(input_data.get('birth_year', '0'))

                if not (1 <= birth_day <= 31):
                    self.error_message = "Invalid day of birth"
                    return False

                if not (1 <= birth_month <= 12):
                    self.error_message = "Invalid month of birth"
                    return False

                # Basic year validation
                current_year = datetime.datetime.now().year
                if birth_year < 1900 or birth_year > current_year:
                    self.error_message = "Invalid year of birth"
                    return False

                # Check if date is in the future
                birth_date = datetime.date(birth_year, birth_month, birth_day)
                if birth_date > datetime.date.today():
                    raise CustomerCreationError(2)  # Future date

                # Check if customer is too old (arbitrary 120 years)
                if (current_year - birth_year) > 120:
                    raise CustomerCreationError(1)  # Too old

            except ValueError:
                raise CustomerCreationError(6)  # Non-numeric date component
            except CustomerCreationError as e:
                raise e
            except Exception:
                raise CustomerCreationError(3)  # Invalid date

            # If all validations pass
            self.customer_data = CustomerData(
                title=title,
                first_name=first_name,
                middle_name=input_data.get('middle_name', '').strip(),
                surname=surname,
                address_line1=address_line1,
                address_line2=input_data.get('address_line2', '').strip(),
                address_line3=input_data.get('address_line3', '').strip(),
                birth_day=birth_day,
                birth_month=birth_month,
                birth_year=birth_year
            )
            return True

        except CustomerCreationError as e:
            self.error_message = ERROR_CODES.get(e.error_code, "Validation failed")
            return False
        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}")
            self.error_message = "Validation failed"
            return False

    def create_customer(self) -> Tuple[bool, Optional[CustomerData]]:
        """Create a new customer record"""
        if not self.customer_data:
            self.error_message = "No valid customer data to create"
            return False, None

        try:
            # In a real implementation, this would interact with VSAM
            # For this example, we'll simulate the creation
            self.customer_data.sort_code = 123456  # Example sort code
            self.customer_data.customer_number = 9876543210  # Example customer number
            self.customer_data.credit_score = 750  # Example credit score
            self.customer_data.review_date = datetime.date.today()  # Example review date

            return True, self.customer_data

        except Exception as e:
            self.logger.error(f"Customer creation failed: {str(e)}")
            self.error_message = "Customer creation failed"
            return False, None

    def process_customer_creation(self, input_data: dict) -> Tuple[bool, Optional[CustomerData]]:
        """Main method to process customer creation"""
        try:
            # Store terminal settings
            self.terminal_settings.store_terminal_settings()

            # Validate input data
            if not self.validate_customer_data(input_data):
                return False, None

            # Create customer
            success, customer_data = self.create_customer()
            if not success:
                return False, None

            return True, customer_data

        except Exception as e:
            self.logger.error(f"Error processing customer creation: {str(e)}")
            self.error_message = str(e)
            return False, None
        finally:
            # Restore terminal settings
            self.terminal_settings.restore_terminal_settings()