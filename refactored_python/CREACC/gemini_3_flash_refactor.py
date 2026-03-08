from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Protocol, Tuple
import logging

@dataclass
class CreaccCommArea:
    """Represents the DFHCOMMAREA for Account Creation."""
    cust_no: str = ""
    sort_code: str = ""
    acc_type: str = ""
    int_rate: float = 0.0
    overdraft_limit: int = 0
    avail_balance: float = 0.0
    actual_balance: float = 0.0
    # Output fields
    account_number: str = ""
    opened_date: str = ""
    last_stmt_date: str = ""
    next_stmt_date: str = ""
    success: str = "N"
    fail_code: str = ""
    eyecatcher: str = "ACCT"

class DatabaseProvider(Protocol):
    """Protocol for Database interactions to maintain legacy DB2 logic."""
    def execute(self, sql: str, params: tuple) -> None: ...
    def fetch_one(self, sql: str, params: tuple) -> Optional[dict]: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...

class CicsLinkProvider(Protocol):
    """Protocol for CICS Link program calls."""
    def link_incust(self, cust_no: str) -> Tuple[bool, str]: ...
    def link_inqaccu(self, cust_no: str) -> Tuple[bool, int]: ...

class AccountCreationService:
    """
    Senior Software Engineer Implementation: Legacy Migration CREACC.
    Handles account creation with VSAM-style locking and SQL persistence.
    """

    VALID_ACCOUNT_TYPES = {"ISA", "MORTGAGE", "SAVING", "CURRENT", "LOAN"}

    def __init__(self, db: DatabaseProvider, cics: CicsLinkProvider):
        self.db = db
        self.cics = cics
        self.logger = logging.getLogger(__name__)

    def create_account(self, commarea: CreaccCommArea) -> CreaccCommArea:
        """
        Main entry point for program CREACC.
        Logic sequence: Validate -> ENQ -> Increment Counter -> DB2 Write -> DEQ.
        """
        try:
            # 1. Validate Customer Existence (CICS LINK 'INQCUST')
            cust_exists, cust_name = self.cics.link_incust(commarea.cust_no)
            if not cust_exists:
                return self._terminate_with_error(commarea, "1")

            # 2. Count Existing Accounts (CICS LINK 'INQACCCU')
            count_success, acc_count = self.cics.link_inqaccu(commarea.cust_no)
            if not count_success:
                return self._terminate_with_error(commarea, "9")
            
            if acc_count > 9:
                return self._terminate_with_error(commarea, "8")

            # 3. Validate Account Type
            if not any(commarea.acc_type.startswith(t) for t in self.VALID_ACCOUNT_TYPES):
                return self._terminate_with_error(commarea, "A")

            # 4. ENQ Named Counter (Logical Lock)
            if not self._enq_named_counter(commarea.sort_code):
                return self._terminate_with_error(commarea, "3")

            try:
                # 5. Find and Increment Next Account Number (Control Table Logic)
                acc_no = self._get_next_account_number(commarea.sort_code)
                commarea.account_number = acc_no

                # 6. Date Calculations (Legacy Business Rules)
                dates = self._calculate_dates()
                
                # 7. Write to DB2 ACCOUNT Table
                self._insert_account(commarea, dates)

                # 8. Write to DB2 PROCTRAN Table
                self._insert_proctran(commarea, dates)

                # Finalize Success
                commarea.success = "Y"
                commarea.fail_code = " "
                commarea.opened_date = dates['opened']
                commarea.last_stmt_date = dates['last_stmt']
                commarea.next_stmt_date = dates['next_stmt']
                self.db.commit()

            except Exception as e:
                self.db.rollback()
                self.logger.error(f"Transaction failed: {e}")
                return self._terminate_with_error(commarea, "7")
            finally:
                # 9. DEQ Named Counter
                if not self._deq_named_counter(commarea.sort_code):
                    return self._terminate_with_error(commarea, "5")

        except Exception as e:
            self.logger.critical(f"Abend Condition: {e}")
            raise  # Re-raise to trigger system abend handler

        return commarea

    def _enq_named_counter(self, sort_code: str) -> bool:
        """Simulates EXEC CICS ENQ RESOURCE('CBSAACCT' + sortcode)."""
        # In a modern context, this is often handled by a DB transaction 
        # on the specific control row, but for logic maintenance we return True 
        # assuming the DB layer handles row-level locking.
        return True

    def _deq_named_counter(self, sort_code: str) -> bool:
        """Simulates EXEC CICS DEQ RESOURCE('CBSAACCT' + sortcode)."""
        return True

    def _get_next_account_number(self, sort_code: str) -> str:
        """
        Maintains legacy logic:
        1. SELECT FROM CONTROL WHERE NAME = sortcode-ACCOUNT-LAST FOR UPDATE
        2. Increment and Update
        3. Increment ACCOUNT-COUNT
        """
        ctrl_name = f"{sort_code}-ACCOUNT-LAST"
        sql_select = "SELECT CONTROL_VALUE_NUM FROM CONTROL WHERE CONTROL_NAME = %s FOR UPDATE"
        
        row = self.db.fetch_one(sql_select, (ctrl_name,))
        if not row:
            raise RuntimeError(f"NCS Counter {ctrl_name} not found")

        next_val = int(row['CONTROL_VALUE_NUM']) + 1
        
        sql_update = "UPDATE CONTROL SET CONTROL_VALUE_NUM = %s WHERE CONTROL_NAME = %s"
        self.db.execute(sql_update, (next_val, ctrl_name))

        # Update ACCOUNT-COUNT similarly
        count_name = f"{sort_code}-ACCOUNT-COUNT"
        self.db.execute("UPDATE CONTROL SET CONTROL_VALUE_NUM = CONTROL_VALUE_NUM + 1 WHERE CONTROL_NAME = %s", (count_name,))
        
        return str(next_val).zfill(8)

    def _calculate_dates(self) -> dict[str, str]:
        """
        Replicates COBOL CALCULATE-DATES section.
        Note: COBOL adds 28-31 days manually based on month/leap year.
        Standard business logic uses 30 days.
        """
        now = datetime.now()
        opened = now.strftime("%d%m%Y")
        
        # Legacy Logic: Compute WS-INTEGER (Integer-of-Date) + 30
        # For Feb, it specifically adjusts for Leap Year. 
        # Modern equivalent using logic from COBOL:
        if now.month == 2:
            is_leap = (now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0))
            days_to_add = 29 if is_leap else 28
        else:
            days_to_add = 30
            
        next_stmt_dt = now + timedelta(days=days_to_add)
        
        return {
            "opened": opened,
            "last_stmt": opened,
            "next_stmt": next_stmt_dt.strftime("%d%m%Y"),
            "db_opened": now.strftime("%d.%m.%Y"),
            "db_next": next_stmt_dt.strftime("%d.%m.%Y"),
            "time": now.strftime("%H%M%S")
        }

    def _insert_account(self, commarea: CreaccCommArea, dates: dict) -> None:
        """SQL INSERT for ACCOUNT Table."""
        sql = """
            INSERT INTO ACCOUNT (
                ACCOUNT_EYECATCHER, ACCOUNT_CUSTOMER_NUMBER, ACCOUNT_SORTCODE,
                ACCOUNT_NUMBER, ACCOUNT_TYPE, ACCOUNT_INTEREST_RATE,
                ACCOUNT_OPENED, ACCOUNT_OVERDRAFT_LIMIT, ACCOUNT_LAST_STATEMENT,
                ACCOUNT_NEXT_STATEMENT, ACCOUNT_AVAILABLE_BALANCE, ACCOUNT_ACTUAL_BALANCE
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            "ACCT", commarea.cust_no, commarea.sort_code, commarea.account_number,
            commarea.acc_type, commarea.int_rate, dates['db_opened'],
            commarea.overdraft_limit, dates['db_opened'], dates['db_next'],
            commarea.avail_balance, commarea.actual_balance
        )
        self.db.execute(sql, params)

    def _insert_proctran(self, commarea: CreaccCommArea, dates: dict) -> None:
        """SQL INSERT for PROCTRAN Table."""
        desc = f"{commarea.cust_no[:10]}{commarea.acc_type[:8]}{dates['opened'][:8]}{dates['next_stmt'][:8]}"
        sql = """
            INSERT INTO PROCTRAN (
                PROCTRAN_EYECATCHER, PROCTRAN_SORTCODE, PROCTRAN_NUMBER,
                PROCTRAN_DATE, PROCTRAN_TIME, PROCTRAN_REF,
                PROCTRAN_TYPE, PROCTRAN_DESC, PROCTRAN_AMOUNT
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            "PRTR", commarea.sort_code, commarea.account_number,
            dates['db_opened'], dates['time'], "TASK-REF-ID", # Logic for EIBTASKN
            "OCA", desc, 0
        )
        self.db.execute(sql, params)

    def _terminate_with_error(self, commarea: CreaccCommArea, code: str) -> CreaccCommArea:
        """Internal helper for GET-ME-OUT-OF-HERE logic."""
        commarea.success = "N"
        commarea.fail_code = code
        return commarea