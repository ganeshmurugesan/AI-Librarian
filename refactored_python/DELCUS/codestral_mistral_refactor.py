import cics
import db2
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

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

@dataclass
class AccountData:
    eyecatcher: str
    cust_no: str
    sortcode: str
    acc_no: str
    acc_type: str
    int_rate: float
    opened: str
    overdraft_limit: str
    last_stmt_date: str
    next_stmt_date: str
    available_balance: float
    actual_balance: float

class Delcus:
    """
    Modern Python implementation of the COBOL DELCUS program.
    Handles customer and account deletion with VSAM READ UPDATE locking.
    """

    def __init__(self):
        self.commarea: Dict[str, Any] = {}
        self.accounts: List[AccountData] = []
        self.customer_data: Optional[CustomerData] = None
        self.token: Optional[int] = None
        self.cics_resp: int = 0
        self.cics_resp2: int = 0
        self.sortcode: str = ""
        self.customer_number: str = ""

    def execute(self, commarea: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution method that processes customer and account deletion.

        Args:
            commarea: Input commarea containing customer number and other data

        Returns:
            Updated commarea with success/failure status
        """
        self.commarea = commarea
        self.sortcode = commarea.get('sortcode', '')
        self.customer_number = commarea.get('custno', '')

        # Validate input
        if not self.customer_number:
            self._set_error(1, "Missing customer number")
            return self.commarea

        # Get customer details
        if not self._get_customer():
            return self.commarea

        # Get associated accounts
        self._get_accounts()

        # Delete accounts if any exist
        if len(self.accounts) > 0:
            self._delete_accounts()

        # Delete customer
        self._delete_customer()

        # Final success status
        self.commarea['del_success'] = 'Y'
        self.commarea['del_fail_cd'] = ' '

        return self.commarea

    def _get_customer(self) -> bool:
        """
        Retrieve customer data from VSAM with UPDATE locking.

        Returns:
            bool: True if successful, False otherwise
        """
        desired_key = f"{self.sortcode}{self.customer_number}"

        try:
            # Read with UPDATE lock
            customer_data = cics.read_file(
                filename='CUSTOMER',
                ridfld=desired_key,
                update=True,
                token=self.token
            )

            if customer_data is None:
                self._set_error(2, "Customer not found")
                return False

            self.customer_data = CustomerData(
                eyecatcher=customer_data.get('eyecatcher', ''),
                sortcode=customer_data.get('sortcode', ''),
                number=customer_data.get('number', ''),
                name=customer_data.get('name', ''),
                address=customer_data.get('address', ''),
                date_of_birth=customer_data.get('date_of_birth', ''),
                credit_score=customer_data.get('credit_score', ''),
                cs_review_date=customer_data.get('cs_review_date', '')
            )

            # Store in commarea
            self.commarea.update({
                'eye': self.customer_data.eyecatcher,
                'scode': self.customer_data.sortcode,
                'custno': self.customer_data.number,
                'name': self.customer_data.name,
                'addr': self.customer_data.address,
                'birth_day': self.customer_data.date_of_birth[:2],
                'birth_month': self.customer_data.date_of_birth[3:5],
                'birth_year': self.customer_data.date_of_birth[6:],
                'credit_score': self.customer_data.credit_score,
                'cs_review_dd': self.customer_data.cs_review_date[:2],
                'cs_review_mm': self.customer_data.cs_review_date[3:5],
                'cs_review_yyyy': self.customer_data.cs_review_date[6:]
            })

            return True

        except cics.CICSError as e:
            self._handle_cics_error(e, "READ CUSTOMER", "WPV6")
            return False

    def _get_accounts(self) -> None:
        """
        Retrieve all accounts associated with the customer.
        """
        try:
            # Simulate INQACCCU call to get accounts
            accounts = cics.link_program(
                program='INQACCCU',
                commarea={
                    'customer_number': self.customer_number,
                    'max_accounts': 20,
                    'pcb_pointer': self.commarea.get('pcb1', None)
                }
            )

            if accounts and 'accounts' in accounts:
                self.accounts = [
                    AccountData(
                        eyecatcher=acc.get('eyecatcher', ''),
                        cust_no=acc.get('cust_no', ''),
                        sortcode=acc.get('sortcode', ''),
                        acc_no=acc.get('acc_no', ''),
                        acc_type=acc.get('acc_type', ''),
                        int_rate=float(acc.get('int_rate', 0)),
                        opened=acc.get('opened', ''),
                        overdraft_limit=acc.get('overdraft_limit', ''),
                        last_stmt_date=acc.get('last_stmt_date', ''),
                        next_stmt_date=acc.get('next_stmt_date', ''),
                        available_balance=float(acc.get('available_balance', 0)),
                        actual_balance=float(acc.get('actual_balance', 0))
                    )
                    for acc in accounts['accounts']
                ]

        except cics.CICSError as e:
            self._handle_cics_error(e, "GET ACCOUNTS", "WPV8")

    def _delete_accounts(self) -> None:
        """
        Delete all accounts associated with the customer.
        """
        for account in self.accounts:
            try:
                # Simulate DELACC call for each account
                result = cics.link_program(
                    program='DELACC',
                    commarea={
                        'applid': self.commarea.get('applid', ''),
                        'accno': account.acc_no
                    }
                )

                if result and result.get('del_success') == 'N':
                    # Account already deleted, continue
                    continue

            except cics.CICSError as e:
                if e.resp != cics.DFHRESP_NOTFND:
                    self._handle_cics_error(e, "DELETE ACCOUNT", "WPV9")

    def _delete_customer(self) -> None:
        """
        Delete the customer record and write to PROCTRAN.
        """
        try:
            # Delete with the token we obtained during read
            cics.delete_file(
                filename='CUSTOMER',
                token=self.token
            )

            # Write to PROCTRAN
            self._write_proctran()

        except cics.CICSError as e:
            self._handle_cics_error(e, "DELETE CUSTOMER", "WPV7")

    def _write_proctran(self) -> None:
        """
        Write customer deletion record to PROCTRAN.
        """
        if not self.customer_data:
            return

        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_date = now.strftime("%d.%m.%Y")

        proctran_data = {
            'eyecatcher': 'PRTR',
            'sortcode': self.customer_data.sortcode,
            'acc_number': '00000000',
            'date': current_date,
            'time': current_time,
            'ref': str(cics.get_task_number()),
            'type': 'ODC',
            'desc': f"{self.customer_data.sortcode}{self.customer_data.number} "
                   f"{self.customer_data.name[:14]} "
                   f"{self.customer_data.date_of_birth}",
            'amount': 0.0
        }

        try:
            db2.execute_sql(
                "INSERT INTO PROCTRAN (PROCTRAN_EYECATCHER, PROCTRAN_SORTCODE, "
                "PROCTRAN_NUMBER, PROCTRAN_DATE, PROCTRAN_TIME, PROCTRAN_REF, "
                "PROCTRAN_TYPE, PROCTRAN_DESC, PROCTRAN_AMOUNT) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    proctran_data['eyecatcher'],
                    proctran_data['sortcode'],
                    proctran_data['acc_number'],
                    proctran_data['date'],
                    proctran_data['time'],
                    proctran_data['ref'],
                    proctran_data['type'],
                    proctran_data['desc'],
                    proctran_data['amount']
                ]
            )

        except db2.DB2Error as e:
            self._handle_db2_error(e, "WRITE PROCTRAN", "HWPT")

    def _set_error(self, error_code: int, message: str) -> None:
        """
        Set error status in commarea.

        Args:
            error_code: Error code (1-8)
            message: Error message
        """
        self.commarea.update({
            'del_success': 'N',
            'del_fail_cd': str(error_code),
            'error_message': message
        })

    def _handle_cics_error(self, error: cics.CICSError, context: str, abend_code: str) -> None:
        """
        Handle CICS errors and prepare for abend.

        Args:
            error: CICS error object
            context: Context where error occurred
            abend_code: Abend code to use
        """
        abend_info = {
            'respcode': error.resp,
            'resp2code': error.resp2,
            'applid': cics.get_applid(),
            'taskno': cics.get_task_number(),
            'tranid': cics.get_tranid(),
            'date': datetime.now().strftime("%d.%m.%Y"),
            'time': datetime.now().strftime("%H:%M:%S"),
            'utime': cics.get_abstime(),
            'code': abend_code,
            'sqlcode': 0,
            'freeform': f"{context} - CICS Error: {error.message}"
        }

        try:
            cics.link_program(
                program='ABNDPROC',
                commarea=abend_info
            )
        except:
            pass

        cics.abend(abend_code)

    def _handle_db2_error(self, error: db2.DB2Error, context: str, abend_code: str) -> None:
        """
        Handle DB2 errors and prepare for abend.

        Args:
            error: DB2 error object
            context: Context where error occurred
            abend_code: Abend code to use
        """
        abend_info = {
            'respcode': cics.get_resp(),
            'resp2code': cics.get_resp2(),
            'applid': cics.get_applid(),
            'taskno': cics.get_task_number(),
            'tranid': cics.get_tranid(),
            'date': datetime.now().strftime("%d.%m.%Y"),
            'time': datetime.now().strftime("%H:%M:%S"),
            'utime': cics.get_abstime(),
            'code': abend_code,
            'sqlcode': error.sqlcode,
            'freeform': f"{context} - DB2 Error: {error.message}"
        }

        try:
            cics.link_program(
                program='ABNDPROC',
                commarea=abend_info
            )
        except:
            pass

        cics.abend(abend_code, nodump=True)