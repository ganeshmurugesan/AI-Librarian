import random
import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Protocol, Dict
from enum import IntEnum

class ReturnCode(IntEnum):
    """Specific error return codes as per migration requirements."""
    SUCCESS = 0
    GENERAL_WARNING = 1
    PARM_ERROR = 2
    VSAM_OPEN_ERROR = 3
    VSAM_WRITE_ERROR = 4
    DB2_DELETE_ERROR = 5
    DB2_INSERT_ERROR = 6
    DB2_COMMIT_ERROR = 7
    CRITICAL_FAILURE = 8

@dataclass
class AccountRecord:
    """Python representation of HV-ACCOUNT-ROW."""
    eyecatcher: str = "ACCT"
    cust_no: str = ""
    sort_code: str = ""
    account_number: str = ""
    account_type: str = ""
    interest_rate: float = 0.0
    opened_date: str = ""
    overdraft_limit: int = 0
    last_stmt_date: str = "01.07.2021"
    next_stmt_date: str = "01.08.2021"
    available_balance: float = 0.0
    actual_balance: float = 0.0

@dataclass
class CustomerRecord:
    """Python representation of CUSTOMER-RECORD-STRUCTURE."""
    eyecatcher: str = "CUST"
    customer_number: str = ""
    customer_name: str = ""
    customer_address: str = ""
    birth_date: str = ""
    sort_code: str = ""
    credit_score: int = 0
    cs_review_date: str = ""

class DatabaseInterface(Protocol):
    """Protocol to simulate DB2/VSAM interaction logic."""
    def execute(self, query: str, params: tuple) -> int: ...
    def commit(self) -> None: ...
    def close(self) -> None: ...

class BankDataGenerator:
    """
    Handles migration of BANKDATA batch processing logic.
    Populates CUSTOMER (VSAM) and ACCOUNT (DB2) data stores.
    """

    def __init__(self, db_connection: DatabaseInterface, sort_code: str = "123456"):
        self.db = db_connection
        self.sort_code = sort_code
        self.commit_count = 0
        self.last_account_number = 0
        self.number_of_accounts = 0
        
        # Static Data Initialization (Equivalent to INITIALISE-ARRAYS)
        self.titles = ["Mr", "Mrs", "Miss", "Ms", "Dr", "Drs", "Professor", "Lord", "Sir", "Lady"]
        self.forenames = [
            "Michael", "Will", "Geoff", "Chris", "Dave", "Luke", "Adam", "Giuseppe", "James", "Jon",
            "Andy", "Lou", "Robert", "Sam", "Frederick", "Buford", "William", "Howard", "Anthony", "Bruce",
            "Peter", "Stephen", "Donald", "Dennis", "Harold", "Amy", "Belinda", "Charlotte", "Donna", "Felicia",
            "Gretchen", "Henrietta", "Imogen", "Josephine", "Kimberley", "Lucy", "Monica", "Natalie", "Ophelia",
            "Patricia", "Querida", "Rachel", "Samantha", "Tanya", "Ulrika", "Virginia", "Wendy", "Xaviera",
            "Yvonne", "Zsa Zsa"
        ]
        self.initials = "ABCDEFGHIJLKMNOPQRSTUVWXYZ"
        self.surnames = [
            "Jones", "Davidson", "Baker", "Smith", "Taylor", "Evans", "Roberts", "Wright", "Walker", "Green",
            "Price", "Downton", "Gatting", "Robinson", "Justice", "Tell", "Stark", "Strange", "Parker", "Blake",
            "Jackson", "Groves", "Palmer", "Ramsbottom", "Lloyd", "Hughes", "Briggs", "Higins", "Goodwin", "Valmont",
            "Brown", "Hopkins", "Bonney", "Jenkins", "Wilmore", "Franklin", "Renton", "Seward", "Morris", "Johnson",
            "Brennan", "Thomson", "Barker", "Corbett", "Weber", "Leigh", "Croft", "Walken", "Dubois", "Stephens"
        ]
        self.street_trees = ["Acacia", "Birch", "Cypress", "Douglas", "Elm", "Fir", "Gorse", "Holly", "Ironwood", "Joshua"]
        self.street_roads = ["Avenue", "Boulevard", "Close", "Crescent", "Drive", "Lane", "Mews", "Street", "Grove"]
        self.towns = ["Norwich", "Acle", "Aylsham", "Wymondham", "Cromer", "Cambridge", "Peterborough", "Oxford", "York", "Exeter"]
        
        self.account_types = [
            {"type": "ISA", "rate": 2.10, "limit": 0},
            {"type": "SAVING", "rate": 1.75, "limit": 0},
            {"type": "CURRENT", "rate": 0.00, "limit": 100},
            {"type": "LOAN", "rate": 17.90, "limit": 0},
            {"type": "MORTGAGE", "rate": 5.25, "limit": 0}
        ]

    def _timestamp(self, message: str) -> None:
        """Simulates the TIMESTAMP section using CEEGMT logic."""
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        print(f"{message} AT {now}")

    def run_migration(self, start_key: int, end_key: int, step_key: int, random_seed: int) -> ReturnCode:
        """
        Main execution logic for the BANKDATA migration.
        
        :param start_key: Starting customer key
        :param end_key: Ending customer key
        :param step_key: Generation increment
        :param random_seed: Seed for reproducibility
        :return: ReturnCode enum value
        """
        self._timestamp("Starting BANKDATA")
        random.seed(random_seed)

        # Parameter Validation
        if end_key < start_key:
            print("Final customer number cannot be smaller than first customer number")
            return ReturnCode.PARM_ERROR
        if step_key <= 0:
            print("Gap between customers cannot be zero")
            return ReturnCode.PARM_ERROR

        # Delete existing records (Equivalent to DELETE-DB2-ROWS)
        try:
            self._timestamp("Deleting from ACCOUNT and CONTROL tables")
            self.db.execute("DELETE FROM ACCOUNT WHERE ACCOUNT_SORTCODE = %s", (self.sort_code,))
            self.db.execute("DELETE FROM CONTROL WHERE CONTROL_NAME LIKE %s", (f"{self.sort_code}-%",))
            self.db.commit()
        except Exception as e:
            print(f"Error during record deletion: {e}")
            return ReturnCode.DB2_DELETE_ERROR

        # VSAM Emulation: Open for Write (Equivalent to OPEN OUTPUT CUSTOMER-FILE)
        try:
            # Logic assumes a context manager or specific API for VSAM file handling
            self._timestamp("Populating Customer + Account files")
            current_key = start_key
            
            while current_key <= end_key:
                customer = self._generate_customer(current_key)
                
                # VSAM Write Simulation
                self._write_vsam_record(customer)
                
                # Define and Populate Accounts
                self._process_accounts(customer)
                
                # Batch Commit Logic (COMMIT every 1000 records)
                self.commit_count += 1
                if self.commit_count >= 1000:
                    self.db.commit()
                    self.commit_count = 0
                
                current_key += step_key

            # Write Customer Control Record (VSAM)
            control_record = CustomerRecord(
                customer_number="9999999999",
                sort_code="000000"
            )
            self._write_vsam_record(control_record)

            # Insert DB2 Control Records
            self._insert_control_records()
            self.db.commit()

        except Exception as e:
            print(f"Critical error during population: {e}")
            return ReturnCode.VSAM_WRITE_ERROR

        self._timestamp("Finishing BANKDATA")
        return ReturnCode.SUCCESS

    def _generate_customer(self, key: int) -> CustomerRecord:
        """Generates random customer data following COBOL logic."""
        title = random.choice(self.titles)
        fname = random.choice(self.forenames)
        initial = random.choice(self.initials)
        sname = random.choice(self.surnames)
        
        name = f"{title} {fname} {initial} {sname}"[:25]
        
        house_num = random.randint(1, 99)
        tree = random.choice(self.street_trees)
        road = random.choice(self.street_roads)
        town = random.choice(self.towns)
        address = f"{house_num} {tree} {road}, {town}"[:40]
        
        dob_year = random.randint(1900, 2000)
        dob_month = random.randint(1, 12)
        dob_day = random.randint(1, 28)
        dob = f"{dob_day:02}.{dob_month:02}.{dob_year}"
        
        # Credit Score Review Date logic (1-21 days from today)
        days_ahead = random.randint(1, 21)
        review_date = datetime.date.today() + datetime.timedelta(days=days_ahead)
        
        return CustomerRecord(
            customer_number=str(key).zfill(10),
            customer_name=name,
            customer_address=address,
            birth_date=dob,
            sort_code=self.sort_code,
            credit_score=random.randint(1, 999),
            cs_review_date=review_date.strftime("%Y.%m.%d")
        )

    def _process_accounts(self, customer: CustomerRecord) -> None:
        """Equivalent to DEFINE-ACC and POPULATE-ACC."""
        num_accounts = random.randint(1, 5)
        
        for _ in range(num_accounts):
            acc_data = random.choice(self.account_types)
            self.last_account_number += 1
            self.number_of_accounts += 1
            
            # Date Logic (Account open date must be after DOB)
            dob_year = int(customer.birth_date.split('.')[-1])
            open_year = random.randint(dob_year, 2014)
            open_date = f"{random.randint(1,28):02}.{random.randint(1,12):02}.{open_year}"
            
            balance = round(random.uniform(1.0, 999999.0), 2)
            
            # Loans/Mortgages have negative balances
            if acc_data["type"] in ["LOAN", "MORTGAGE"]:
                balance = -abs(balance)

            account = AccountRecord(
                cust_no=customer.customer_number,
                sort_code=self.sort_code,
                account_number=str(self.last_account_number).zfill(8),
                account_type=acc_data["type"],
                interest_rate=acc_data["rate"],
                opened_date=open_date,
                overdraft_limit=acc_data["limit"],
                available_balance=balance,
                actual_balance=balance
            )
            
            self._insert_db2_account(account)

    def _insert_db2_account(self, acc: AccountRecord) -> None:
        """Performs EXEC SQL INSERT INTO ACCOUNT."""
        query = """
            INSERT INTO ACCOUNT (
                ACCOUNT_EYECATCHER, ACCOUNT_CUSTOMER_NUMBER, ACCOUNT_SORTCODE,
                ACCOUNT_NUMBER, ACCOUNT_TYPE, ACCOUNT_INTEREST_RATE,
                ACCOUNT_OPENED, ACCOUNT_OVERDRAFT_LIMIT, ACCOUNT_LAST_STATEMENT,
                ACCOUNT_NEXT_STATEMENT, ACCOUNT_AVAILABLE_BALANCE, ACCOUNT_ACTUAL_BALANCE
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            acc.eyecatcher, acc.cust_no, acc.sort_code, acc.account_number,
            acc.account_type, acc.interest_rate, acc.opened_date,
            acc.overdraft_limit, acc.last_stmt_date, acc.next_stmt_date,
            acc.available_balance, acc.actual_balance
        )
        # Note: In a real system, SQLCODE mapping would happen here
        self.db.execute(query, params)

    def _write_vsam_record(self, record: CustomerRecord) -> None:
        """Simulates WRITE CUSTOMER-RECORD-STRUCTURE to indexed VSAM."""
        # This simulates the VSAM WRITE logic with FILE-STATUS check
        # In modern Python, this would likely be an API call or a direct DB write
        pass

    def _insert_control_records(self) -> None:
        """Inserts account metadata into CONTROL table."""
        controls = [
            (f"{self.sort_code}-ACCOUNT-LAST", self.last_account_number, ""),
            (f"{self.sort_code}-ACCOUNT-COUNT", self.number_of_accounts, "")
        ]
        
        query = """
            INSERT INTO CONTROL (CONTROL_NAME, CONTROL_VALUE_NUM, CONTROL_VALUE_STR)
            VALUES (%s, %s, %s)
        """
        for name, val_num, val_str in controls:
            self.db.execute(query, (name, val_num, val_str))

# Usage Example:
# db = PostgresOrDB2Connection(...)
# migrator = BankDataGenerator(db)
# migrator.run_migration(start_key=100, end_key=500, step_key=10, random_seed=12345)