import logging
from dataclasses import dataclass
from typing import Optional, Tuple
from datetime import date
from decimal import Decimal
import ibm_db_dbi as db2  # Assuming DB2 connectivity via ibm_db_dbi

@dataclass
class AccountUpdateResult:
    """Result of account update operation."""
    success: bool
    error_code: Optional[int] = None
    error_message: Optional[str] = None

class AccountUpdater:
    """Handles account updates in the banking system."""

    def __init__(self, db_connection: db2.Connection):
        """
        Initialize the account updater with a DB2 connection.

        Args:
            db_connection: Active DB2 database connection
        """
        self.db_connection = db_connection
        self.logger = logging.getLogger(__name__)

    def update_account(
        self,
        sort_code: str,
        account_number: str,
        account_type: str,
        interest_rate: Decimal,
        overdraft_limit: int
    ) -> AccountUpdateResult:
        """
        Update account details in the database.

        Args:
            sort_code: 6-digit sort code
            account_number: 8-digit account number
            account_type: New account type (must not be empty or start with space)
            interest_rate: New interest rate
            overdraft_limit: New overdraft limit

        Returns:
            AccountUpdateResult with success status and error details if applicable

        Error Codes:
            1: Invalid account type (empty or starts with space)
            2: Database SELECT operation failed
            3: Database UPDATE operation failed
        """
        # Validate account type
        if not account_type or account_type.startswith(' '):
            self.logger.error("Invalid account type provided")
            return AccountUpdateResult(
                success=False,
                error_code=1,
                error_message="Invalid account type"
            )

        try:
            # Prepare SQL parameters
            params = {
                'sort_code': sort_code,
                'account_number': account_number,
                'account_type': account_type,
                'interest_rate': interest_rate,
                'overdraft_limit': overdraft_limit
            }

            # Execute SELECT to verify account exists
            select_sql = """
                SELECT ACCOUNT_EYECATCHER, ACCOUNT_CUSTOMER_NUMBER,
                       ACCOUNT_SORTCODE, ACCOUNT_NUMBER, ACCOUNT_TYPE,
                       ACCOUNT_INTEREST_RATE, ACCOUNT_OPENED,
                       ACCOUNT_OVERDRAFT_LIMIT, ACCOUNT_LAST_STATEMENT,
                       ACCOUNT_NEXT_STATEMENT, ACCOUNT_AVAILABLE_BALANCE,
                       ACCOUNT_ACTUAL_BALANCE
                FROM ACCOUNT
                WHERE ACCOUNT_SORTCODE = ? AND ACCOUNT_NUMBER = ?
            """

            with self.db_connection.cursor() as cursor:
                cursor.execute(select_sql, (sort_code, account_number))
                account_data = cursor.fetchone()

                if not account_data:
                    self.logger.error(f"Account not found: {sort_code}/{account_number}")
                    return AccountUpdateResult(
                        success=False,
                        error_code=2,
                        error_message="Account not found"
                    )

                # Execute UPDATE
                update_sql = """
                    UPDATE ACCOUNT
                    SET ACCOUNT_TYPE = ?,
                        ACCOUNT_INTEREST_RATE = ?,
                        ACCOUNT_OVERDRAFT_LIMIT = ?
                    WHERE ACCOUNT_SORTCODE = ? AND ACCOUNT_NUMBER = ?
                """

                cursor.execute(
                    update_sql,
                    (account_type, interest_rate, overdraft_limit, sort_code, account_number)
                )

                if cursor.rowcount == 0:
                    self.logger.error(f"Failed to update account: {sort_code}/{account_number}")
                    return AccountUpdateResult(
                        success=False,
                        error_code=3,
                        error_message="Update failed"
                    )

                self.db_connection.commit()
                return AccountUpdateResult(success=True)

        except Exception as e:
            self.db_connection.rollback()
            self.logger.error(f"Database error: {str(e)}")
            return AccountUpdateResult(
                success=False,
                error_code=4,
                error_message=str(e)
            )

    def _parse_db2_date(self, db2_date_str: str) -> Optional[date]:
        """Parse DB2 date format (YYYY-MM-DD) to date object."""
        if not db2_date_str or len(db2_date_str) != 10:
            return None
        try:
            year = int(db2_date_str[:4])
            month = int(db2_date_str[5:7])
            day = int(db2_date_str[8:10])
            return date(year, month, day)
        except ValueError:
            return None