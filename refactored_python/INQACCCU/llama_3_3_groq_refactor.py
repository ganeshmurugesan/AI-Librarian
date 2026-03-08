from datetime import datetime
from typing import Dict, List

class Account:
    """
    Represents an account.
    """

    def __init__(self, 
                 customer_number: str, 
                 sort_code: str, 
                 account_number: str, 
                 account_type: str, 
                 interest_rate: float, 
                 opened_date: str, 
                 overdraft_limit: float, 
                 last_statement_date: str, 
                 next_statement_date: str, 
                 available_balance: float, 
                 actual_balance: float):
        """
        Initializes an Account object.

        Args:
            customer_number (str): Customer number.
            sort_code (str): Sort code.
            account_number (str): Account number.
            account_type (str): Account type.
            interest_rate (float): Interest rate.
            opened_date (str): Date the account was opened.
            overdraft_limit (float): Overdraft limit.
            last_statement_date (str): Date of the last statement.
            next_statement_date (str): Date of the next statement.
            available_balance (float): Available balance.
            actual_balance (float): Actual balance.
        """
        self.customer_number = customer_number
        self.sort_code = sort_code
        self.account_number = account_number
        self.account_type = account_type
        self.interest_rate = interest_rate
        self.opened_date = opened_date
        self.overdraft_limit = overdraft_limit
        self.last_statement_date = last_statement_date
        self.next_statement_date = next_statement_date
        self.available_balance = available_balance
        self.actual_balance = actual_balance

    def to_dict(self) -> Dict:
        """
        Returns a dictionary representation of the Account object.

        Returns:
            Dict: Dictionary representation of the Account object.
        """
        return {
            "customer_number": self.customer_number,
            "sort_code": self.sort_code,
            "account_number": self.account_number,
            "account_type": self.account_type,
            "interest_rate": self.interest_rate,
            "opened_date": self.opened_date,
            "overdraft_limit": self.overdraft_limit,
            "last_statement_date": self.last_statement_date,
            "next_statement_date": self.next_statement_date,
            "available_balance": self.available_balance,
            "actual_balance": self.actual_balance
        }


class InqAcccu:
    """
    Represents an InqAcccu object.
    """

    def __init__(self, 
                 customer_number: str, 
                 customer_comm_area: Dict, 
                 db_connection: object):
        """
        Initializes an InqAcccu object.

        Args:
            customer_number (str): Customer number.
            customer_comm_area (Dict): Customer communication area.
            db_connection (object): Database connection object.
        """
        self.customer_number = customer_number
        self.customer_comm_area = customer_comm_area
        self.db_connection = db_connection
        self.customer_found = False
        self.number_of_accounts = 0
        self.comm_success = False
        self.comm_fail_code = 0
        self.accounts = []

    def check_customer(self) -> bool:
        """
        Checks if the customer exists.

        Returns:
            bool: True if the customer exists, False otherwise.
        """
        # Link to INQCUST to retrieve customer information
        # For simplicity, this is simulated with a dictionary
        customers = {
            "1234567890": {"name": "John Doe", "address": "123 Main St"}
        }
        if self.customer_number in customers:
            self.customer_found = True
            return True
        else:
            self.customer_found = False
            return False

    def read_account_db2(self) -> List[Account]:
        """
        Reads account information from the database.

        Returns:
            List[Account]: List of Account objects.
        """
        try:
            # Open the DB2 cursor
            cursor = self.db_connection.cursor()
            query = """
                SELECT * FROM ACCOUNT
                WHERE ACCOUNT_CUSTOMER_NUMBER = %s
            """
            cursor.execute(query, (self.customer_number,))
            rows = cursor.fetchall()
            for row in rows:
                account = Account(
                    customer_number=row[0],
                    sort_code=row[1],
                    account_number=row[2],
                    account_type=row[3],
                    interest_rate=row[4],
                    opened_date=row[5],
                    overdraft_limit=row[6],
                    last_statement_date=row[7],
                    next_statement_date=row[8],
                    available_balance=row[9],
                    actual_balance=row[10]
                )
                self.accounts.append(account)
            return self.accounts
        except Exception as e:
            self.comm_success = False
            self.comm_fail_code = 2
            print(f"Error reading account information: {e}")
            return []

    def get_accounts(self) -> List[Account]:
        """
        Gets the accounts for the customer.

        Returns:
            List[Account]: List of Account objects.
        """
        if self.check_customer():
            accounts = self.read_account_db2()
            self.number_of_accounts = len(accounts)
            self.comm_success = True
            return accounts
        else:
            self.comm_success = False
            self.comm_fail_code = 1
            return []

    def to_dict(self) -> Dict:
        """
        Returns a dictionary representation of the InqAcccu object.

        Returns:
            Dict: Dictionary representation of the InqAcccu object.
        """
        return {
            "customer_number": self.customer_number,
            "customer_comm_area": self.customer_comm_area,
            "accounts": [account.to_dict() for account in self.accounts],
            "comm_success": self.comm_success,
            "comm_fail_code": self.comm_fail_code,
            "number_of_accounts": self.number_of_accounts
        }


class AbendHandler:
    """
    Represents an AbendHandler object.
    """

    def __init__(self, 
                 abend_code: str, 
                 abnd_info_rec: Dict):
        """
        Initializes an AbendHandler object.

        Args:
            abend_code (str): Abend code.
            abnd_info_rec (Dict): Abend information record.
        """
        self.abend_code = abend_code
        self.abnd_info_rec = abnd_info_rec

    def handle_abend(self) -> None:
        """
        Handles the abend.
        """
        if self.abend_code == "AD2Z":
            print("DB2 DEADLOCK DETECTED")
        elif self.abend_code in ["AFCR", "AFCS", "AFCT"]:
            print("VSAM RLS abend detected")
        else:
            print("Unknown abend code")


def check_for_storm_drain_db2(sqlcode: int) -> bool:
    """
    Checks if the SQL code indicates a storm drain condition.

    Args:
        sqlcode (int): SQL code.

    Returns:
        bool: True if the SQL code indicates a storm drain condition, False otherwise.
    """
    if sqlcode == 923:
        return True
    else:
        return False


def main():
    # Simulate the database connection
    db_connection = object()

    # Simulate the customer communication area
    customer_comm_area = {}

    # Create an InqAcccu object
    inq_acccu = InqAcccu("1234567890", customer_comm_area, db_connection)

    # Get the accounts for the customer
    accounts = inq_acccu.get_accounts()

    # Print the accounts
    for account in accounts:
        print(account.to_dict())

    # Simulate an abend
    abend_code = "AD2Z"
    abnd_info_rec = {}
    abend_handler = AbendHandler(abend_code, abnd_info_rec)
    abend_handler.handle_abend()

    # Check for storm drain condition
    sqlcode = 923
    if check_for_storm_drain_db2(sqlcode):
        print("Storm drain condition detected")


if __name__ == "__main__":
    main()