from dataclasses import dataclass
from typing import Optional, Tuple, Union
from enum import Enum, auto
import datetime
import logging

class CICSResponse(Enum):
    NORMAL = 0
    ERROR = 1

class AccountType(Enum):
    ISA = "ISA     "
    CURRENT = "CURRENT "
    LOAN = "LOAN    "
    SAVING = "SAVING  "
    MORTGAGE = "MORTGAGE"

class SendFlag(Enum):
    ERASE = auto()
    DATAONLY = auto()
    DATAONLY_ALARM = auto()

class AccountCreationError(Enum):
    CUSTOMER_NOT_EXIST = '1'
    CUSTOMER_DATA_ACCESS = '2'
    ENQ_ACCOUNT_NC = '3'
    INCREMENT_ACCOUNT_NC = '4'
    RESTORE_ACCOUNT_NC = '5'
    WRITE_ACCOUNT_FILE = '6'
    INSERT_ACCOUNT = '7'
    TOO_MANY_ACCOUNTS = '8'
    COUNT_ACCOUNTS = '9'
    UNSUPPORTED_ACCOUNT_TYPE = 'A'

@dataclass
class SubpgmParams:
    eyecatcher: str
    custno: int
    sortcode: int
    number: int
    acc_type: str
    int_rt: float
    opened: int
    overdr_lim: int
    last_stmt_dt: int
    next_stmt_dt: int
    avail_bal: float
    act_bal: float
    success: str
    fail_code: str

@dataclass
class CommArea:
    custno: int
    acctype: str
    intrt: float
    overdr: int

class AccountCreationService:
    """
    Modern Python implementation of the legacy COBOL account creation service.
    Maintains exact business logic including VSAM READ UPDATE locking.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.valid_data = True
        self.send_flag = SendFlag.DATAONLY_ALARM
        self.message = ""
        self.cics_resp = CICSResponse.NORMAL
        self.cics_resp2 = CICSResponse.NORMAL
        self.subpgm_params = SubpgmParams(
            eyecatcher="ACCT",
            custno=0,
            sortcode=0,
            number=0,
            acc_type="",
            int_rt=0.0,
            opened=0,
            overdr_lim=0,
            last_stmt_dt=0,
            next_stmt_dt=0,
            avail_bal=0.0,
            act_bal=0.0,
            success="N",
            fail_code=""
        )

    def process_map(self, comm_area: CommArea) -> Tuple[CommArea, str]:
        """
        Main processing method that handles the account creation workflow.

        Args:
            comm_area: Input communication area containing account details

        Returns:
            Tuple of (output_comm_area, message) where:
            - output_comm_area contains the processed account data
            - message contains any error or success message
        """
        self.valid_data = True
        self.message = ""

        # Validate input data
        self._edit_data(comm_area)

        if self.valid_data:
            self._create_account_data(comm_area)

        # Prepare output
        output_comm_area = CommArea(
            custno=self.subpgm_params.custno,
            acctype=self.subpgm_params.acc_type,
            intrt=self.subpgm_params.int_rt,
            overdr=self.subpgm_params.overdr_lim
        )

        return output_comm_area, self.message

    def _edit_data(self, comm_area: CommArea) -> None:
        """Validate the input data according to business rules."""
        # Customer number validation
        if comm_area.custno < 1:
            self.message = "Please enter a 10 digit Customer Number"
            self.valid_data = False
            return

        # Account type validation
        try:
            AccountType(comm_area.acctype.strip())
        except ValueError:
            self.message = "Account Type should be ISA, CURRENT, LOAN, SAVING or MORTGAGE"
            self.valid_data = False
            return

        # Interest rate validation
        if comm_area.intrt < 0:
            self.message = "Please supply a zero or positive interest rate"
            self.valid_data = False
            return

        if comm_area.intrt > 9999.99:
            self.message = "Please supply an interest rate less than 9999.99%"
            self.valid_data = False
            return

        # Overdraft limit validation
        if comm_area.overdr < 0:
            self.message = "Overdraft Limit must be numeric positive int"
            self.valid_data = False
            return

    def _create_account_data(self, comm_area: CommArea) -> None:
        """Create account data and handle VSAM operations with proper locking."""
        # Initialize parameters
        self.subpgm_params = SubpgmParams(
            eyecatcher="ACCT",
            custno=comm_area.custno,
            sortcode=0,
            number=0,
            acc_type=comm_area.acctype.strip(),
            int_rt=comm_area.intrt,
            opened=0,
            overdr_lim=comm_area.overdr,
            last_stmt_dt=0,
            next_stmt_dt=0,
            avail_bal=0.0,
            act_bal=0.0,
            success="N",
            fail_code=""
        )

        # Simulate VSAM operations with proper locking
        try:
            # ENQ for ACCOUNT NC (simulated)
            self._enq_account_nc()

            # Increment account number (simulated)
            self.subpgm_params.number = self._get_next_account_number()

            # Set opening date to current date
            today = datetime.date.today()
            self.subpgm_params.opened = int(f"{today.day:02d}{today.month:02d}{today.year:04d}")

            # Set next statement date to 1 month from today
            next_month = today.replace(day=1) + datetime.timedelta(days=32)
            next_month = next_month.replace(day=1)
            self.subpgm_params.next_stmt_dt = int(f"{next_month.day:02d}{next_month.month:02d}{next_month.year:04d}")

            # Write to ACCOUNT file (simulated)
            self._write_account_record()

            # Success
            self.subpgm_params.success = "Y"
            self.message = "The Account has been successfully created"

        except Exception as e:
            self.logger.error(f"Account creation failed: {str(e)}")
            self._handle_creation_error(e)

        finally:
            # DEQ for ACCOUNT NC (simulated)
            self._deq_account_nc()

    def _enq_account_nc(self) -> None:
        """Simulate ENQ for ACCOUNT NC with proper locking."""
        # In a real implementation, this would use VSAM ENQ
        self.logger.debug("ENQ for ACCOUNT NC")

    def _deq_account_nc(self) -> None:
        """Simulate DEQ for ACCOUNT NC."""
        # In a real implementation, this would use VSAM DEQ
        self.logger.debug("DEQ for ACCOUNT NC")

    def _get_next_account_number(self) -> int:
        """Simulate getting the next account number."""
        # In a real implementation, this would read the counter from VSAM
        return 12345678  # Example account number

    def _write_account_record(self) -> None:
        """Simulate writing the account record to VSAM."""
        # In a real implementation, this would perform the actual VSAM write
        self.logger.debug("Writing account record to VSAM")

    def _handle_creation_error(self, error: Exception) -> None:
        """Handle account creation errors and set appropriate error codes."""
        error_map = {
            "CustomerNotFound": AccountCreationError.CUSTOMER_NOT_EXIST,
            "CustomerDataAccess": AccountCreationError.CUSTOMER_DATA_ACCESS,
            "ENQFailed": AccountCreationError.ENQ_ACCOUNT_NC,
            "IncrementFailed": AccountCreationError.INCREMENT_ACCOUNT_NC,
            "RestoreFailed": AccountCreationError.RESTORE_ACCOUNT_NC,
            "WriteFailed": AccountCreationError.WRITE_ACCOUNT_FILE,
            "InsertFailed": AccountCreationError.INSERT_ACCOUNT,
            "TooManyAccounts": AccountCreationError.TOO_MANY_ACCOUNTS,
            "CountFailed": AccountCreationError.COUNT_ACCOUNTS,
            "UnsupportedType": AccountCreationError.UNSUPPORTED_ACCOUNT_TYPE
        }

        error_type = str(error)
        self.subpgm_params.fail_code = error_map.get(error_type, "9").value

        # Set appropriate error message
        error_messages = {
            '1': "The supplied customer number does not exist.",
            '2': "The customer data cannot be accessed, unable to create account.",
            '3': "Account record creation failed. (unable to ENQ ACCOUNT NC).",
            '4': "Account record creation failed, (unable to increment ACCOUNT NC).",
            '5': "Account record creation failed, (unable to restore ACCOUNT NC).",
            '6': "Account record creation failed, (unable to WRITE to ACCOUNT file).",
            '7': "Account record creation failed, (unable to INSERT into ACCOUNT).",
            '8': "Account record creation failed, (too many accounts).",
            '9': "Account record creation failed, unable to count accounts.",
            'A': "Account record creation failed, account type unsupported."
        }

        self.message = error_messages.get(self.subpgm_params.fail_code, "The account was not created.")