from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple, Union
import cics
import datetime

class ErrorCode(Enum):
    """Error codes returned by the transfer operation."""
    FROM_ACCOUNT_NOT_FOUND = '1'
    TO_ACCOUNT_NOT_FOUND = '2'
    UNEXPECTED_ERROR = '3'
    INVALID_AMOUNT = '4'
    GENERIC_ERROR = '5'

class SendFlag(Enum):
    """Flags for controlling map sending behavior."""
    ERASE = '1'
    DATAONLY = '2'
    DATAONLY_ALARM = '3'

@dataclass
class SubpgmParams:
    """Parameters for the XFRFUN subprogram."""
    faccno: int
    fscode: int
    taccno: int
    tscode: int
    amt: float
    favbal: float
    factbal: float
    tavbal: float
    tactbal: float
    fail_code: str
    success: str

class BankTransfer:
    """Modern Python implementation of the COBOL BNK1TFN program."""

    def __init__(self):
        self.ws_cics_resp = 0
        self.ws_cics_resp2 = 0
        self.valid_data_sw = True
        self.send_flag = SendFlag.DATAONLY
        self.ws_amount_as_float = 0.0
        self.ws_commarea = {'faccno': 0, 'taccno': 0, 'amt': 0}
        self.abend_pgm = 'ABNDPROC'
        self.end_of_session_message = 'Session Ended'

    def process(self, commarea: dict) -> Tuple[int, int]:
        """Main processing entry point."""
        self.ws_commarea = commarea

        if cics.EIBCALEN == 0:
            self._send_map(erase=True)
        elif cics.EIBAID in (cics.DFHPA1, cics.DFHPA2, cics.DFHPA3):
            pass
        elif cics.EIBAID == cics.DFHPF3:
            cics.RETURN(transid='OMEN')
        elif cics.EIBAID in (cics.DFHAID, cics.DFHPF12):
            self._send_termination_msg()
            cics.RETURN()
        elif cics.EIBAID == cics.DFHCLEAR:
            cics.SEND_CONTROL(erase=True, freekb=True)
            cics.RETURN()
        elif cics.EIBAID == cics.DFHENTER:
            self._process_map()
        else:
            self._send_invalid_key_message()

        cics.RETURN(transid='OTFN', commarea=self.ws_commarea, length=29)

        if self.ws_cics_resp != cics.DFHRESP_NORMAL:
            self._handle_cics_error('A010 - RETURN TRANSID(OCCS) FAIL')

        return (self.ws_cics_resp, self.ws_cics_resp2)

    def _process_map(self) -> None:
        """Process the received map data."""
        self._receive_map()
        self._edit_data()

        if self.valid_data_sw:
            self._get_acc_data()

        self.send_flag = SendFlag.DATAONLY_ALARM
        self._send_map()

    def _receive_map(self) -> None:
        """Receive the map data from CICS."""
        cics.RECEIVE_MAP('BNK1TF', 'BNK1TFM', into='BNK1TFI')

        if self.ws_cics_resp != cics.DFHRESP_NORMAL:
            self._handle_cics_error('RM010 - RECEIVE MAP FAIL')

    def _edit_data(self) -> None:
        """Validate the received data."""
        self.valid_data_sw = True

        # Validate FROM account number
        cics.BIF_DEEDIT(field='FACCNOI')
        if not self._is_numeric('FACCNOI'):
            self._set_error_message('Please enter a FROM account no  ')
            self.valid_data_sw = False
            return

        # Validate TO account number
        cics.BIF_DEEDIT(field='TACCNOI')
        if not self._is_numeric('TACCNOI'):
            self._set_error_message('Please enter a TO account no    ')
            self.valid_data_sw = False
            return

        # Check account numbers are different
        if 'FACCNOI' == 'TACCNOI':
            self._set_error_message('The FROM & TO account should be different ')
            self.valid_data_sw = False
            return

        # Check account numbers are not zero
        if 'FACCNOI' == '00000000' or 'TACCNOI' == '00000000':
            self._set_error_message('Account no 00000000 is not valid          ')
            self.valid_data_sw = False
            return

        # Validate amount
        self._validate_amount()

    def _validate_amount(self) -> None:
        """Validate the transfer amount."""
        if 'AMTL' == 0:
            self._set_error_message('The Amount entered must be numeric.')
            self.valid_data_sw = False
            return

        if self._is_numeric('AMTI'):
            self.ws_amount_as_float = float('AMTI')
            if self.ws_amount_as_float <= 0:
                self._set_error_message('Please supply a positive amount.')
                self.valid_data_sw = False
            return

        # More complex validation for non-numeric input
        leading_spaces = 'AMTI'.count(' ', 0, 'AMTL')
        if leading_spaces == 'AMTL':
            self._set_error_message('The Amount entered must be numeric.')
            self.valid_data_sw = False
            return

        amount_unstr = 'AMTI'[leading_spaces:]
        amount_unstr_l = len(amount_unstr)

        # Check for negative amounts
        if '-' in amount_unstr:
            self._set_error_message('Please supply a positive amount.')
            self.valid_data_sw = False
            return

        # Check for embedded spaces
        if ' ' in amount_unstr:
            self._set_error_message('Please supply a numeric amount without embedded spaces.')
            self.valid_data_sw = False
            return

        # Check for valid numeric characters
        valid_chars = set('0123456789.')
        if not all(c in valid_chars for c in amount_unstr):
            self._set_error_message('Please supply a numeric amount.')
            self.valid_data_sw = False
            return

        # Check decimal point count
        decimal_count = amount_unstr.count('.')
        if decimal_count > 1:
            self._set_error_message('Use one decimal point for amount only.')
            self.valid_data_sw = False
            return

        # Check decimal places
        if decimal_count == 1:
            decimal_pos = amount_unstr.index('.')
            decimal_places = len(amount_unstr) - decimal_pos - 1
            if decimal_places > 2:
                self._set_error_message('Only up to two decimal places are supported.')
                self.valid_data_sw = False
                return

        # Convert to float
        try:
            self.ws_amount_as_float = float(amount_unstr)
        except ValueError:
            self._set_error_message('Please supply a valid numeric amount.')
            self.valid_data_sw = False
            return

        if self.ws_amount_as_float == 0:
            self._set_error_message('Please supply a non-zero amount.')
            self.valid_data_sw = False

    def _get_acc_data(self) -> None:
        """Get account data and perform transfer."""
        params = SubpgmParams(
            faccno=int('FACCNOI'),
            fscode=0,
            taccno=int('TACCNOI'),
            tscode=0,
            amt=self.ws_amount_as_float,
            favbal=0.0,
            factbal=0.0,
            tavbal=0.0,
            tactbal=0.0,
            fail_code='',
            success='N'
        )

        cics.LINK('XFRFUN', commarea=params, sync=True)

        if self.ws_cics_resp != cics.DFHRESP_NORMAL:
            self._handle_cics_error('GCD010 - LINK XFRFUN FAIL')

        # Map returned data to screen
        self._map_account_data(params)

        # Handle transfer result
        if params.success == 'N':
            self.valid_data_sw = False
            self._handle_transfer_error(params.fail_code)
        else:
            self._set_success_message()

    def _map_account_data(self, params: SubpgmParams) -> None:
        """Map account data to screen fields."""
        # Map basic account information
        'FACCNO2O' = str(params.faccno)
        'FSORTCO' = str(params.fscode)
        'TACCNO2O' = str(params.taccno)
        'TSORTCO' = str(params.tscode)

        # Initialize balance displays
        'FACTBALO' = '0.00'
        'FAVBALO' = '0.00'
        'TACTBALO' = '0.00'
        'TAVBALO' = '0.00'

        # Map balance information if transfer was successful
        if params.success == 'Y':
            'FACTBALO' = f"{params.factbal:.2f}"
            'FAVBALO' = f"{params.favbal:.2f}"
            'TACTBALO' = f"{params.tactbal:.2f}"
            'TAVBALO' = f"{params.tavbal:.2f}"

    def _handle_transfer_error(self, error_code: str) -> None:
        """Handle transfer errors based on error code."""
        error_messages = {
            ErrorCode.FROM_ACCOUNT_NOT_FOUND.value: 'Sorry the FROM ACCOUNT no was not found. Transfer not applied.',
            ErrorCode.TO_ACCOUNT_NOT_FOUND.value: 'Sorry the TO ACCOUNT no was not found. Transfer not applied.',
            ErrorCode.UNEXPECTED_ERROR.value: 'Sorry but the transfer could not be applied due to an unexpected error.',
            ErrorCode.INVALID_AMOUNT.value: 'Please supply an amount greater than zero.',
            ErrorCode.GENERIC_ERROR.value: 'Sorry but the transfer could not be applied due to an error.'
        }

        self._set_error_message(error_messages.get(error_code, 'Sorry but the transfer could not be applied due to an error.'))

    def _send_map(self, erase: bool = False, alarm: bool = False) -> None:
        """Send the map to CICS."""
        if erase:
            cics.SEND_MAP('BNK1TF', 'BNK1TFM', from_='BNK1TFO', erase=True, freekb=True)
            if self.ws_cics_resp != cics.DFHRESP_NORMAL:
                self._handle_cics_error('SM010 - SEND MAP ERASE FAIL')
        elif alarm:
            cics.SEND_MAP('BNK1TF', 'BNK1TFM', from_='BNK1TFO', dataonly=True, alarm=True, freekb=True)
            if self.ws_cics_resp != cics.DFHRESP_NORMAL:
                self._handle_cics_error('SM010 - SEND MAP DATAONLY ALARM FAIL')
        else:
            cics.SEND_MAP('BNK1TF', 'BNK1TFM', from_='BNK1TFO', dataonly=True, freekb=True)
            if self.ws_cics_resp != cics.DFHRESP_NORMAL:
                self._handle_cics_error('SM010 - SEND MAP DATAONLY FAIL')

    def _send_termination_msg(self) -> None:
        """Send termination message to CICS."""
        cics.SEND_TEXT(self.end_of_session_message, erase=True, freekb=True)
        if self.ws_cics_resp != cics.DFHRESP_NORMAL:
            self._handle_cics_error('STM010 - SEND TEXT FAIL')

    def _send_invalid_key_message(self) -> None:
        """Send invalid key message to CICS."""
        self._set_error_message('Invalid key pressed.')
        self.send_flag = SendFlag.DATAONLY_ALARM
        self._send_map()

    def _set_error_message(self, message: str) -> None:
        """Set the error message in the output map."""
        'MESSAGEO' = message.ljust(70)

    def _set_success_message(self) -> None:
        """Set the success message in the output map."""
        'MESSAGEO' = 'Transfer successfully applied.             '

    def _handle_cics_error(self, context: str) -> None:
        """Handle CICS errors and abend the task."""
        fail_info = f"{context} RESP={self.ws_cics_resp} RESP2={self.ws_cics_resp2} ABENDING TASK."
        print(fail_info)
        cics.ABEND(abcode='HBNK', nodump=True)

    def _is_numeric(self, field: str) -> bool:
        """Check if a field contains numeric data."""
        try:
            float(field)
            return True
        except ValueError:
            return False