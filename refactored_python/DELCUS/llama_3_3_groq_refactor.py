from datetime import datetime
import sqlite3

class LegacyMigration:
    """
    This class is responsible for migrating legacy data.
    
    It provides methods for deleting customer records and their associated accounts.
    """

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize the LegacyMigration class.

        Args:
        conn (sqlite3.Connection): A SQLite connection object.
        """
        self.conn = conn
        self.cursor = conn.cursor()

    def delete_customer(self, customer_id: int) -> None:
        """
        Delete a customer record and its associated accounts.

        Args:
        customer_id (int): The ID of the customer to delete.

        Returns:
        None
        """
        try:
            # Lock the customer record for update
            self.cursor.execute("SELECT * FROM customers WHERE id = ? FOR UPDATE", (customer_id,))
            customer = self.cursor.fetchone()

            if customer:
                # Delete the customer's accounts
                self.delete_accounts(customer_id)

                # Delete the customer record
                self.cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
                self.conn.commit()

                # Write to the PROCTRAN table
                self.write_to_proctrans(customer_id)

            else:
                print("Customer not found.")

        except sqlite3.Error as e:
            if e.args[0] == 'database is locked':
                self.delete_customer(customer_id)
            else:
                self.handle_error(e)

    def delete_accounts(self, customer_id: int) -> None:
        """
        Delete all accounts associated with a customer.

        Args:
        customer_id (int): The ID of the customer.

        Returns:
        None
        """
        try:
            # Lock the accounts for update
            self.cursor.execute("SELECT * FROM accounts WHERE customer_id = ? FOR UPDATE", (customer_id,))
            accounts = self.cursor.fetchall()

            for account in accounts:
                self.cursor.execute("DELETE FROM accounts WHERE id = ?", (account[0],))
                self.conn.commit()

                # Write to the PROCTRAN table
                self.write_to_proctrans(account[0], account_type='account')

        except sqlite3.Error as e:
            if e.args[0] == 'database is locked':
                self.delete_accounts(customer_id)
            else:
                self.handle_error(e)

    def write_to_proctrans(self, record_id: int, record_type: str = 'customer') -> None:
        """
        Write to the PROCTRAN table.

        Args:
        record_id (int): The ID of the record.
        record_type (str): The type of record (customer or account).

        Returns:
        None
        """
        try:
            now = datetime.now()
            proctrans_data = {
                'eyecatcher': 'PRTR',
                'sort_code': '123456',
                'account_number': str(record_id),
                'date': now.strftime('%Y-%m-%d'),
                'time': now.strftime('%H:%M:%S'),
                'ref': str(record_id),
                'type': 'ODC' if record_type == 'customer' else 'ODA',
                'desc': f'Deleted {record_type} {record_id}',
                'amount': 0.0
            }

            self.cursor.execute("""
                INSERT INTO proctrans (eyecatcher, sort_code, account_number, date, time, ref, type, desc, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                proctrans_data['eyecatcher'],
                proctrans_data['sort_code'],
                proctrans_data['account_number'],
                proctrans_data['date'],
                proctrans_data['time'],
                proctrans_data['ref'],
                proctrans_data['type'],
                proctrans_data['desc'],
                proctrans_data['amount']
            ))
            self.conn.commit()

        except sqlite3.Error as e:
            self.handle_error(e)

    def handle_error(self, error: sqlite3.Error) -> None:
        """
        Handle SQLite errors.

        Args:
        error (sqlite3.Error): The error to handle.

        Returns:
        None
        """
        error_code = error.args[0]
        if error_code == 1:
            print("Error: Database is locked.")
        elif error_code == 2:
            print("Error: Database is not found.")
        elif error_code == 3:
            print("Error: Table is not found.")
        elif error_code == 4:
            print("Error: Column is not found.")
        elif error_code == 5:
            print("Error: Data type mismatch.")
        elif error_code == 6:
            print("Error: Out of range value.")
        elif error_code == 7:
            print("Error: Invalid SQL statement.")
        elif error_code == 8:
            print("Error: Unknown error.")

def main():
    conn = sqlite3.connect('database.db')
    legacy_migration = LegacyMigration(conn)
    legacy_migration.delete_customer(1)

if __name__ == '__main__':
    main()