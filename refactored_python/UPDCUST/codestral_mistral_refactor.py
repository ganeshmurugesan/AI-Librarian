from typing import Optional, Tuple
from dataclasses import dataclass
import cics

@dataclass
class CustomerData:
    eyecatcher: str
    sortcode: str
    number: str
    name: str
    address: str
    date_of_birth: str
    credit_score: str
    cs_review_date: str

class CustomerUpdater:
    """
    A class to handle updating customer records in a VSAM datastore.

    Maintains the exact business logic including VSAM READ UPDATE locking
    and specific error return codes (1-8).

    Attributes:
        commarea: The communication area containing input/output data
    """

    VALID_TITLES = {
        'Professor', 'Mr', 'Mrs', 'Miss', 'Ms', 'Dr', 'Drs',
        'Lord', 'Sir', 'Lady', ''
    }

    def __init__(self, commarea: dict):
        self.commarea = commarea
        self.ws_cust_data: Optional[CustomerData] = None
        self.ws_cics_resp: int = 0
        self.ws_cics_resp2: int = 0

    def update_customer(self) -> Tuple[bool, str]:
        """
        Main method to update customer records.

        Returns:
            Tuple containing (success_flag, error_code)
            success_flag: 'Y' if successful, 'N' otherwise
            error_code: Specific error code (1-8) or empty string if successful
        """
        self._validate_title()
        if self.commarea['UPD_SUCCESS'] == 'N':
            return (False, self.commarea['UPD_FAIL_CD'])

        success, error_code = self._update_customer_vsam()
        if not success:
            return (False, error_code)

        self._populate_commarea()
        return (True, '')

    def _validate_title(self) -> None:
        """Validate the customer title against allowed values."""
        name_parts = self.commarea['NAME'].split()
        title = name_parts[0] if name_parts else ''

        if title not in self.VALID_TITLES:
            self.commarea['UPD_SUCCESS'] = 'N'
            self.commarea['UPD_FAIL_CD'] = 'T'

    def _update_customer_vsam(self) -> Tuple[bool, str]:
        """
        Update the customer record in VSAM with proper locking.

        Returns:
            Tuple containing (success_flag, error_code)
        """
        desired_cust_key = {
            'SORT_CODE': self.commarea['SCODE'],
            'CUSTNO': self.commarea['CUSTNO']
        }

        # Read with UPDATE lock
        try:
            self.ws_cust_data = cics.read_file(
                'CUSTOMER',
                ridfld=desired_cust_key,
                update=True
            )
            self.ws_cics_resp = cics.get_response()
            self.ws_cics_resp2 = cics.get_response2()
        except cics.CICSError as e:
            self.ws_cics_resp = e.response_code

        if self.ws_cics_resp != cics.DFHRESP_NORMAL:
            self.commarea['UPD_SUCCESS'] = 'N'
            if self.ws_cics_resp == cics.DFHRESP_NOTFND:
                return (False, '1')
            return (False, '2')

        # Validate input data
        if (not self.commarea['NAME'].strip() and
            not self.commarea['ADDR'].strip()):
            self.commarea['UPD_SUCCESS'] = 'N'
            return (False, '4')

        # Update fields conditionally
        if not self.commarea['NAME'].strip() or self.commarea['NAME'][0] == ' ':
            self.ws_cust_data.address = self.commarea['ADDR']
        elif not self.commarea['ADDR'].strip() or self.commarea['ADDR'][0] == ' ':
            self.ws_cust_data.name = self.commarea['NAME']
        else:
            self.ws_cust_data.name = self.commarea['NAME']
            self.ws_cust_data.address = self.commarea['ADDR']

        # Rewrite the record
        try:
            cics.rewrite_file(
                'CUSTOMER',
                data=self.ws_cust_data,
                length=len(self.ws_cust_data)
            )
            self.ws_cics_resp = cics.get_response()
        except cics.CICSError as e:
            self.ws_cics_resp = e.response_code

        if self.ws_cics_resp != cics.DFHRESP_NORMAL:
            self.commarea['UPD_SUCCESS'] = 'N'
            return (False, '3')

        return (True, '')

    def _populate_commarea(self) -> None:
        """Populate the commarea with updated customer data."""
        if not self.ws_cust_data:
            return

        self.commarea.update({
            'EYE': self.ws_cust_data.eyecatcher,
            'SCODE': self.ws_cust_data.sortcode,
            'CUSTNO': self.ws_cust_data.number,
            'NAME': self.ws_cust_data.name,
            'ADDR': self.ws_cust_data.address,
            'DOB': self.ws_cust_data.date_of_birth,
            'CREDIT_SCORE': self.ws_cust_data.credit_score,
            'CS_REVIEW_DATE': self.ws_cust_data.cs_review_date,
            'UPD_SUCCESS': 'Y'
        })

    def execute(self) -> None:
        """Execute the customer update process."""
        self.update_customer()
        cics.return_transaction()