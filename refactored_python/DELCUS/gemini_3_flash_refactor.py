from typing import TypedDict, List, Optional, Any
from datetime import datetime
import time
from dataclasses import dataclass, field

class Commarea(TypedDict):
    """Represents the DFHCOMMAREA structure."""
    sort_code: str
    customer_no: str
    del_success: str
    del_fail_code: str
    name: str
    address: str
    birth_day: str
    birth_month: str
    birth_year: str
    credit_score: int
    cs_review_dd: str
    cs_review_mm: str
    cs_review_yyyy: str

@dataclass
class AccountData:
    """Structure for account details returned by INQACCCU."""
    acc_no: str
    acc_type: str
    interest_rate: float
    opened_date: str
    overdraft_limit: float
    last_stmt_date: str
    next_stmt_date: str
    available_balance: float
    actual_balance: float

class VSAMError(Exception):
    """Simulates CICS/VSAM response codes."""
    def __init__(self, resp: int, resp2: int):
        self.resp = resp
        self.resp2 = resp2

class DB2Error(Exception):
    """Simulates SQLCODE errors."""
    def __init__(self, sqlcode: int):
        self.sqlcode = sqlcode

class CustomerDeletionService:
    """
    Handles the migration logic of the DELCUS COBOL program.
    Maintains VSAM READ-UPDATE locking logic and account-to-customer 
    cascading deletion via external program links.
    """

    # Simulated CICS Responses (DFHRESP)
    NORMAL = 0
    SYSIDERR = 1
    NOTFND = 2
    
    def __init__(self, data_access_layer: Any, external_services: Any):
        self.dal = data_access_layer
        self.services = external_services
        self.applid = "WPV6"
        self.task_no = 12345

    def execute(self, commarea: Commarea) -> int:
        """
        Main execution flow.
        Returns:
            1: Success
            2: Customer Not Found
            3: Inquiry Failure
            4: VSAM Read Error (Abend WPV6)
            5: VSAM Delete Error (Abend WPV7)
            6: DB2 Write Error (Abend HWPT)
            8: General Exception
        """
        try:
            # Step 1: Check if Customer Exists (INQCUST)
            inq_resp = self.services.link_inqcust(commarea['customer_no'])
            if inq_resp.get('success') == 'N':
                commarea['del_success'] = 'N'
                commarea['del_fail_code'] = inq_resp.get('fail_cd')
                return 3

            # Step 2: Retrieve Accounts (INQACCCU)
            accounts = self.services.link_inqacccu(commarea['customer_no'], limit=20)

            # Step 3: Delete Accounts (DELACC)
            if accounts:
                self._delete_accounts(accounts)

            # Step 4: Delete Customer from VSAM
            customer_record = self._delete_customer_vsam(commarea)
            if customer_record is None:
                return 2 # Not found (someone else deleted it)

            # Step 5: Log Deletion to DB2
            self._write_proctran_cust_db2(customer_record)

            commarea['del_success'] = 'Y'
            commarea['del_fail_code'] = ' '
            return 1

        except VSAMError as ve:
            if ve.resp == self.SYSIDERR: return 4
            return 5
        except DB2Error:
            return 6
        except Exception:
            return 8

    def _delete_accounts(self, accounts: List[AccountData]) -> None:
        """Iterates through account list and links to DELACC program."""
        for acc in accounts:
            # Equivalent to EXEC CICS LINK PROGRAM('DELACC')
            # Errors in DELACC are logic-ignored in COBOL unless it abends
            self.services.link_delacc({
                'acc_no': acc.acc_no,
                'applid': self.applid
            })

    def _delete_customer_vsam(self, commarea: Commarea) -> Optional[dict]:
        """
        Implements EXEC CICS READ UPDATE + DELETE logic.
        Handles SYSIDERR retries (100 iterations, 3s delay).
        """
        token = None
        record = None
        
        # READ FOR UPDATE Logic
        for retry in range(101):
            try:
                # Simulated VSAM READ UPDATE
                record, token = self.dal.read_customer_for_update(
                    sort_code=commarea['sort_code'],
                    customer_no=commarea['customer_no']
                )
                break
            except VSAMError as ve:
                if ve.resp == self.SYSIDERR and retry < 100:
                    time.sleep(3)
                    continue
                if ve.resp == self.NOTFND:
                    return None
                self._trigger_abend("WPV6", "DCV010", ve)
                raise ve

        # Map Record to Commarea (Equivalent to COBOL MOVE statements)
        commarea.update({
            'name': record['NAME'],
            'address': record['ADDRESS'],
            'birth_day': record['DOB'][0:2],
            'birth_month': record['DOB'][2:4],
            'birth_year': record['DOB'][4:8],
            'credit_score': record['CREDIT_SCORE'],
            'cs_review_dd': record['CS_DATE'][0:2],
            'cs_review_mm': record['CS_DATE'][2:4],
            'cs_review_yyyy': record['CS_DATE'][4:8]
        })

        # DELETE using Token
        try:
            for retry in range(101):
                try:
                    self.dal.delete_customer_with_token(token)
                    break
                except VSAMError as ve:
                    if ve.resp == self.SYSIDERR and retry < 100:
                        time.sleep(3)
                        continue
                    self._trigger_abend("WPV7", "DCV010(2)", ve)
                    raise ve
        except Exception as e:
            raise e

        return record

    def _write_proctran_cust_db2(self, record: dict) -> None:
        """
        Inserts audit record into PROCTRAN DB2 table.
        Equivalent to EXEC SQL INSERT.
        """
        now = datetime.now()
        
        # Prepare host variables
        hv_row = {
            'eyecatcher': 'PRTR',
            'sort_code': record['SORT_CODE'],
            'acc_number': '00000000',
            'date': now.strftime("%d.%m.%Y"),
            'time': now.strftime("%H%M%S"),
            'ref': str(self.task_no).zfill(12),
            'type': 'ODC',
            'desc': (f"{record['SORT_CODE']}{record['CUSTOMER_NO']}"
                     f"{record['NAME'][:14]}{record['DOB']}").ljust(40),
            'amount': 0.0
        }

        try:
            self.dal.insert_proctran(hv_row)
        except DB2Error as de:
            self._trigger_abend("HWPT", "WPCD010", de)
            raise de

    def _trigger_abend(self, abcode: str, location: str, error: Any) -> None:
        """
        Simulates ABNDPROC link and EXEC CICS ABEND.
        Captures state for the abend handler.
        """
        abend_info = {
            'abcode': abcode,
            'location': location,
            'applid': self.applid,
            'task_no': self.task_no,
            'time': datetime.now().isoformat(),
            'resp': getattr(error, 'resp', 0),
            'resp2': getattr(error, 'resp2', 0),
            'sqlcode': getattr(error, 'sqlcode', 0)
        }
        # In a real migration, this logs to a centralized logger or CICS dump
        self.services.link_abend_handler(abend_info)
        print(f"CRITICAL: Abend {abcode} at {location} - {error}")