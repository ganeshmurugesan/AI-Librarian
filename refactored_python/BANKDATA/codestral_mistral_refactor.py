import random
import datetime
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from enum import Enum, auto
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ErrorCode(Enum):
    """Error codes for the application."""
    SUCCESS = 0
    INVALID_PARAMETERS = 1
    FILE_OPEN_ERROR = 2
    FILE_WRITE_ERROR = 3
    DB_CONNECTION_ERROR = 4
    DB_OPERATION_ERROR = 5
    TIMEOUT_ERROR = 6
    DEADLOCK_ERROR = 7
    UNKNOWN_ERROR = 8

@dataclass
class CustomerRecord:
    """Represents a customer record in the VSAM file."""
    eyecatcher: str
    number: int
    name: str
    address: str
    birth_day: int
    birth_month: int
    birth_year: int
    sortcode: str
    credit_score: int
    cs_review_year: int
    cs_review_month: int
    cs_review_day: int

@dataclass
class AccountRecord:
    """Represents an account record in the DB2 table."""
    eyecatcher: str
    customer_number: int
    sortcode: str
    number: int
    account_type: str
    interest_rate: float
    opened_date: str
    overdraft_limit: int
    last_statement_date: str
    next_statement_date: str
    available_balance: float
    actual_balance: float

class BankDataProcessor:
    """Processes bank data and populates customer and account records."""

    def __init__(self):
        self.start_key: int = 0
        self.end_key: int = 0
        self.step_key: int = 0
        self.random_seed: str = ""
        self.sortcode: str = "000000"
        self.last_customer_number: int = 0
        self.last_account_number: int = 0
        self.number_of_customers: int = 0
        self.number_of_accounts: int = 0
        self.commit_count: int = 0
        self.today_int: int = 0

        # Initialize data arrays
        self._initialize_arrays()

    def _initialize_arrays(self) -> None:
        """Initialize all the data arrays used for generating records."""
        self.titles = [
            'Mr', 'Mrs', 'Miss', 'Ms', 'Mr', 'Mrs', 'Miss', 'Ms',
            'Mr', 'Mrs', 'Miss', 'Ms', 'Mr', 'Mrs', 'Miss', 'Ms',
            'Mr', 'Mrs', 'Miss', 'Ms', 'Dr', 'Drs', 'Dr', 'Ms',
            'Dr', 'Ms', 'Dr', 'Ms', 'Professor', 'Professor',
            'Professor', 'Lord', 'Sir', 'Sir', 'Lady', 'Lady'
        ]

        self.forenames = [
            'Michael', 'Will', 'Geoff', 'Chris', 'Dave', 'Luke', 'Adam',
            'Giuseppe', 'James', 'Jon', 'Andy', 'Lou', 'Robert', 'Sam',
            'Frederick', 'Buford', 'William', 'Howard', 'Anthony', 'Bruce',
            'Peter', 'Stephen', 'Donald', 'Dennis', 'Harold', 'Amy',
            'Belinda', 'Charlotte', 'Donna', 'Felicia', 'Gretchen',
            'Henrietta', 'Imogen', 'Josephine', 'Kimberley', 'Lucy',
            'Monica', 'Natalie', 'Ophelia', 'Patricia', 'Querida',
            'Rachel', 'Samantha', 'Tanya', 'Ulrika', 'Virginia',
            'Wendy', 'Xaviera', 'Yvonne', 'Zsa Zsa'
        ]

        self.initials = list('ABCDEFGHIJLKMNOPQRSTUVWXYZ    ')

        self.surnames = [
            'Jones', 'Davidson', 'Baker', 'Smith', 'Taylor', 'Evans',
            'Roberts', 'Wright', 'Walker', 'Green', 'Price', 'Downton',
            'Gatting', 'Robinson', 'Justice', 'Tell', 'Stark', 'Strange',
            'Parker', 'Blake', 'Jackson', 'Groves', 'Palmer', 'Ramsbottom',
            'Lloyd', 'Hughes', 'Briggs', 'Higins', 'Goodwin', 'Valmont',
            'Brown', 'Hopkins', 'Bonney', 'Jenkins', 'Lloyd', 'Wilmore',
            'Franklin', 'Renton', 'Seward', 'Morris', 'Johnson', 'Brennan',
            'Thomson', 'Barker', 'Corbett', 'Weber', 'Leigh', 'Croft',
            'Walken', 'Dubois', 'Stephens'
        ]

        self.street_name_trees = [
            'Acacia', 'Birch', 'Cypress', 'Douglas', 'Elm', 'Fir', 'Gorse',
            'Holly', 'Ironwood', 'Joshua', 'Kapok', 'Laburnam', 'Maple',
            'Nutmeg', 'Oak', 'Pine', 'Quercine', 'Rowan', 'Sycamore',
            'Thorn', 'Ulmus', 'Viburnum', 'Willow', 'Xylophone', 'Yew',
            'Zebratree'
        ]

        self.street_name_roads = [
            'Avenue', 'Boulevard', 'Close', 'Crescent', 'Drive', 'Escalade',
            'Frontage', 'Lane', 'Mews', 'Rise', 'Court', 'Opening', 'Loke',
            'Square', 'Houses', 'Gate', 'Street', 'Grove', 'March'
        ]

        self.towns = [
            'Norwich', 'Acle', 'Aylsham', 'Wymondham', 'Attleborough',
            'Cromer', 'Cambridge', 'Peterborough', 'Weobley', 'Wembley',
            'Hereford', 'Ross-on-Wye', 'Hay-on-Wye', 'Nottingham',
            'Northampton', 'Nuneaton', 'Oxford', 'Oswestry', 'Ormskirk',
            'Royston', 'Chilcomb', 'Winchester', 'Wrexham', 'Crewe',
            'Plymouth', 'Portsmouth', 'Forfar', 'Fife', 'Aberdeen',
            'Glasgow', 'Birmingham', 'Bolton', 'Whitby', 'Manchester',
            'Chester', 'Leicester', 'Lowestoft', 'Ipswich', 'Colchester',
            'Dover', 'Brighton', 'Salisbury', 'Bristol', 'Bath',
            'Gloucester', 'Cheltenham', 'Durham', 'Carlisle', 'York',
            'Exeter'
        ]

        self.account_types = [
            'ISA     ', 'SAVING  ', 'CURRENT ', 'LOAN    ', 'MORTGAGE'
        ]

        self.account_int_rates = [
            2.10, 1.75, 0.00, 17.90, 5.25
        ]

        self.account_overdraft_limits = [
            0, 0, 100, 0, 0
        ]

    def _get_todays_date(self) -> None:
        """Get today's date and store it as an integer."""
        today = datetime.date.today()
        self.today_int = int(today.strftime("%Y%m%d"))

    def _generate_opened_date(self, customer: CustomerRecord) -> Tuple[int, int, int]:
        """Generate a valid account opened date after the customer's birth date."""
        attempts = 0
        max_attempts = 100

        while attempts < max_attempts:
            day = random.randint(1, 28)
            month = random.randint(1, 12)
            year = random.randint(customer.birth_year, 2014)

            if year > customer.birth_year:
                return day, month, year

            attempts += 1

        # Fallback if we can't generate a valid date
        return customer.birth_day, customer.birth_month, customer.birth_year

    def _delete_db2_rows(self) -> ErrorCode:
        """Delete rows from DB2 tables that match the sortcode."""
        try:
            # In a real implementation, this would connect to DB2 and execute the delete
            logger.info("Deleting from ACCOUNT table for sortcode %s", self.sortcode)
            logger.info("Deleting from CONTROL table for sortcode %s", self.sortcode)
            return ErrorCode.SUCCESS
        except Exception as e:
            logger.error("Error deleting DB2 rows: %s", str(e))
            return ErrorCode.DB_OPERATION_ERROR

    def _populate_account(self, customer: CustomerRecord, account_count: int) -> ErrorCode:
        """Populate account records for a customer."""
        try:
            # Generate account opened date
            day, month, year = self._generate_opened_date(customer)
            opened_date = f"{day:02d}.{month:02d}.{year:04d}"

            # Create account record
            account = AccountRecord(
                eyecatcher="ACCT",
                customer_number=customer.number,
                sortcode=self.sortcode,
                number=self.last_account_number + 1,
                account_type=self.account_types[account_count % len(self.account_types)],
                interest_rate=self.account_int_rates[account_count % len(self.account_int_rates)],
                opened_date=opened_date,
                overdraft_limit=self.account_overdraft_limits[account_count % len(self.account_overdraft_limits)],
                last_statement_date="01.07.2021",
                next_statement_date="01.08.2021",
                available_balance=random.uniform(1, 999999),
                actual_balance=random.uniform(1, 999999)
            )

            # Adjust balance for loan/mortgage accounts
            if account.account_type.strip() in ['LOAN', 'MORTGAGE']:
                account.actual_balance *= -1
                account.available_balance *= -1

            # In a real implementation, this would insert into the DB2 table
            logger.info("Created account record for customer %d", customer.number)

            self.last_account_number += 1
            self.number_of_accounts += 1

            return ErrorCode.SUCCESS
        except Exception as e:
            logger.error("Error populating account: %s", str(e))
            return ErrorCode.DB_OPERATION_ERROR

    def _write_customer_control_record(self) -> ErrorCode:
        """Write the customer control record."""
        try:
            control_record = CustomerRecord(
                eyecatcher="CTRL",
                number=9999999999,
                name="",
                address="",
                birth_day=0,
                birth_month=0,
                birth_year=0,
                sortcode="000000",
                credit_score=0,
                cs_review_year=0,
                cs_review_month=0,
                cs_review_day=0
            )

            # In a real implementation, this would write to the VSAM file
            logger.info("Writing customer control record")
            return ErrorCode.SUCCESS
        except Exception as e:
            logger.error("Error writing customer control record: %s", str(e))
            return ErrorCode.FILE_WRITE_ERROR

    def _write_control_records(self) -> ErrorCode:
        """Write control records to DB2."""
        try:
            # In a real implementation, this would insert into the DB2 table
            logger.info("Writing control records for sortcode %s", self.sortcode)
            return ErrorCode.SUCCESS
        except Exception as e:
            logger.error("Error writing control records: %s", str(e))
            return ErrorCode.DB_OPERATION_ERROR

    def process(self, parameters: str) -> ErrorCode:
        """Main processing method."""
        try:
            # Parse parameters
            params = parameters.split(',')
            if len(params) != 4:
                logger.error("Invalid number of parameters")
                return ErrorCode.INVALID_PARAMETERS

            self.start_key = int(params[0])
            self.end_key = int(params[1])
            self.step_key = int(params[2])
            self.random_seed = params[3]

            # Validate parameters
            if self.end_key < self.start_key:
                logger.error("Final customer number cannot be smaller than first customer number")
                return ErrorCode.INVALID_PARAMETERS

            if self.step_key == 0:
                logger.error("Gap between customers cannot be zero")
                return ErrorCode.INVALID_PARAMETERS

            # Initialize random seed
            random.seed(self.random_seed)

            # Get today's date
            self._get_todays_date()

            # Delete existing DB2 rows
            result = self._delete_db2_rows()
            if result != ErrorCode.SUCCESS:
                return result

            # Open customer file (in a real implementation, this would open the VSAM file)
            logger.info("Opening customer file")

            # Process each customer
            for customer_number in range(self.start_key, self.end_key + 1, self.step_key):
                # Generate customer data
                title = random.choice(self.titles)
                forename = random.choice(self.forenames)
                initial = random.choice(self.initials)
                surname = random.choice(self.surnames)
                house_number = random.randint(1, 99)
                street_tree = random.choice(self.street_name_trees)
                street_road = random.choice(self.street_name_roads)
                town = random.choice(self.towns)

                customer_name = f"{title} {forename} {initial} {surname}"
                customer_address = f"{house_number} {street_tree} {street_road}, {town}"

                birth_day = random.randint(1, 28)
                birth_month = random.randint(1, 12)
                birth_year = random.randint(1900, 2000)

                credit_score = random.randint(1, 999)
                review_date_add = random.randint(1, 21)
                new_review_date_int = self.today_int + review_date_add

                # Convert integer date back to YYYYMMDD format
                new_review_date = datetime.datetime.strptime(str(new_review_date_int), "%Y%m%d").date()
                cs_review_year = new_review_date.year
                cs_review_month = new_review_date.month
                cs_review_day = new_review_date.day

                # Create customer record
                customer = CustomerRecord(
                    eyecatcher="CUST",
                    number=customer_number,
                    name=customer_name,
                    address=customer_address,
                    birth_day=birth_day,
                    birth_month=birth_month,
                    birth_year=birth_year,
                    sortcode=self.sortcode,
                    credit_score=credit_score,
                    cs_review_year=cs_review_year,
                    cs_review_month=cs_review_month,
                    cs_review_day=cs_review_day
                )

                # In a real implementation, this would write to the VSAM file
                logger.info("Writing customer record for customer %d", customer_number)

                # Generate accounts for this customer
                num_accounts = random.randint(1, 5)
                for account_num in range(num_accounts):
                    result = self._populate_account(customer, account_num)
                    if result != ErrorCode.SUCCESS:
                        return result

                # Update counters
                self.last_customer_number = customer_number
                self.number_of_customers += 1

                # Commit every 1000 records
                self.commit_count += 1
                if self.commit_count >= 1000:
                    logger.info("Committing after %d records", self.commit_count)
                    self.commit_count = 0

            # Write customer control record
            result = self._write_customer_control_record()
            if result != ErrorCode.SUCCESS:
                return result

            # Write control records
            result = self._write_control_records()
            if result != ErrorCode.SUCCESS:
                return result

            # Close customer file (in a real implementation, this would close the VSAM file)
            logger.info("Closing customer file")

            return ErrorCode.SUCCESS
        except Exception as e:
            logger.error("Error in processing: %s", str(e))
            return ErrorCode.UNKNOWN_ERROR