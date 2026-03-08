import asyncio
import datetime
import random
import threading
from dataclasses import dataclass, field
from typing import Optional, TypedDict, List


class Commarea(TypedDict):
    """Represents the DFHCOMMAREA structure."""
    name: str
    address: str
    date_of_birth: str  # YYYYMMDD
    birth_year: int
    birth_month: int
    birth_day: int
    sort_code: str
    customer_number: str
    credit_score: int
    cs_review_date: str  # DDMMYYYY
    success: str  # 'Y' or 'N'
    fail_code: str  # Mapping to requirements 1-8


@dataclass
class CustomerRecord:
    eyecatcher: str = "CUST"
    sort_code: str = ""
    number: int = 0
    name: str = ""
    address: str = ""
    dob: str = ""
    credit_score: int = 0
    review_date: str = ""


class CustomerMigrationManager:
    """
    Handles customer creation logic including VSAM-style locking, 
    Asynchronous credit checks, and DB2-style transaction logging.
    """

    def __init__(self):
        # Simulated VSAM file and Named Counter locking
        self._vsam_lock = threading.Lock()
        self._named_counter_lock = threading.Lock()
        self._customer_datastore: List[CustomerRecord] = []
        self._last_customer_number = 1000  # Starting point
        self._proctran_db: List[dict] = []

    async def process_create_customer(self, commarea: Commarea) -> Commarea:
        """
        Main entry point for program CRECUST logic.
        
        Error Codes (commarea['fail_code']):
        1: VSAM Write Failure
        2: SQL/DB2 Insert Failure
        3: ENQ Resource (Locking) Failure
        4: VSAM Read/Update (Counter) Failure
        5: DEQ Resource Failure
        6: Credit Check Async Failure
        7: Date of Birth Validation Failure
        8: Title Validation Failure
        """
        
        # 1. Title Validation
        if not self._validate_title(commarea['name']):
            commarea['success'] = 'N'
            commarea['fail_code'] = '8'
            return commarea

        # 2. Credit Check (Async API Simulation)
        credit_result = await self._perform_credit_check(commarea)
        if not credit_result:
            commarea['success'] = 'N'
            commarea['fail_code'] = '6'
            return commarea
        
        commarea['credit_score'] = credit_result['score']
        commarea['cs_review_date'] = credit_result['review_date']

        # 3. DOB Check
        if not self._validate_dob(commarea):
            commarea['success'] = 'N'
            commarea['fail_code'] = '7'
            return commarea

        # 4. Critical Section: Named Counter and VSAM Update
        # Implements EXEC CICS ENQ / VSAM READ UPDATE logic
        try:
            locked = self._named_counter_lock.acquire(timeout=5)
            if not locked:
                commarea['success'] = 'N'
                commarea['fail_code'] = '3'
                return commarea

            # Update Named Counter (Simulating UPD-NCS / GET-LAST-CUSTOMER-VSAM)
            try:
                with self._vsam_lock:
                    # Simulation of EXEC CICS READ FILE('CUSTOMER') UPDATE
                    self._last_customer_number += 1
                    new_cust_no = self._last_customer_number
                    
                    # Simulation of EXEC CICS WRITE FILE('CUSTOMER')
                    success = self._write_customer_vsam(commarea, new_cust_no)
                    if not success:
                        # Rollback counter if write fails
                        self._last_customer_number -= 1
                        commarea['success'] = 'N'
                        commarea['fail_code'] = '1'
                        return commarea

                    # 5. DB2 Interaction (PROCTRAN)
                    sql_success = self._write_proctran_db2(commarea, new_cust_no)
                    if not sql_success:
                        # In COBOL, this triggers an ABEND, here we map to code 2
                        commarea['success'] = 'N'
                        commarea['fail_code'] = '2'
                        return commarea

            except Exception:
                commarea['success'] = 'N'
                commarea['fail_code'] = '4'
                return commarea
            finally:
                if not self._release_lock():
                    commarea['fail_code'] = '5'

        except Exception:
            commarea['success'] = 'N'
            commarea['fail_code'] = '3'
            return commarea

        commarea['customer_number'] = str(new_cust_no)
        commarea['success'] = 'Y'
        commarea['fail_code'] = ' '
        return commarea

    def _validate_title(self, name: str) -> bool:
        """Checks if the title at the start of the name is valid."""
        valid_titles = {
            "Professor", "Mr", "Mrs", "Miss", "Ms", "Dr", "Drs", 
            "Lord", "Sir", "Lady", ""
        }
        title = name.split()[0] if name.strip() else ""
        return title in valid_titles

    async def _perform_credit_check(self, commarea: Commarea) -> Optional[dict]:
        """
        Simulates EXEC CICS RUN TRANSID (Async) and FETCH ANY.
        Processes OCR1-OCR5 transactions.
        """
        async def mock_credit_agency_call(agency_id: int):
            # Simulation of async processing time
            await asyncio.sleep(random.uniform(0.1, 1.0))
            if random.random() < 0.05:  # 5% failure rate
                return None
            return random.randint(300, 850)

        # Fire 5 async requests
        tasks = [mock_credit_agency_call(i) for i in range(1, 6)]
        
        # COBOL: EXEC CICS DELAY FOR SECONDS(3)
        await asyncio.sleep(3)
        
        results = await asyncio.gather(*tasks)
        valid_scores = [s for s in results if s is not None]

        if not valid_scores:
            return None

        avg_score = sum(valid_scores) // len(valid_scores)
        
        # Calculate random review date within 21 days
        today = datetime.date.today()
        review_days = random.randint(1, 21)
        review_date = today + datetime.timedelta(days=review_days)
        
        return {
            "score": avg_score,
            "review_date": review_date.strftime("%d%m%Y")
        }

    def _validate_dob(self, commarea: Commarea) -> bool:
        """Validates DOB logic including age limits and Lilian date concepts."""
        try:
            dob = datetime.date(
                commarea['birth_year'], 
                commarea['birth_month'], 
                commarea['birth_day']
            )
            today = datetime.date.today()
            
            if dob.year < 1601:
                return False
            
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if age > 150 or dob > today:
                return False
                
            return True
        except ValueError:
            return False

    def _write_customer_vsam(self, commarea: Commarea, cust_no: int) -> bool:
        """Simulates VSAM record insertion."""
        try:
            record = CustomerRecord(
                sort_code=commarea['sort_code'],
                number=cust_no,
                name=commarea['name'],
                address=commarea['address'],
                dob=commarea['date_of_birth'],
                credit_score=commarea['credit_score'],
                review_date=commarea['cs_review_date']
            )
            self._customer_datastore.append(record)
            return True
        except Exception:
            return False

    def _write_proctran_db2(self, commarea: Commarea, cust_no: int) -> bool:
        """Simulates SQL INSERT INTO PROCTRAN."""
        try:
            now = datetime.datetime.now()
            row = {
                "PROCTRAN_EYECATCHER": "PRTR",
                "PROCTRAN_SORTCODE": commarea['sort_code'],
                "PROCTRAN_NUMBER": cust_no,
                "PROCTRAN_DATE": now.strftime("%d.%m.%Y"),
                "PROCTRAN_TIME": now.strftime("%H.%M.%S"),
                "PROCTRAN_REF": str(random.getrandbits(32)), # Simulated Task No
                "PROCTRAN_TYPE": "OCC",
                "PROCTRAN_DESC": f"{commarea['sort_code']}{cust_no}{commarea['name'][:14]}",
                "PROCTRAN_AMOUNT": 0.00
            }
            self._proctran_db.append(row)
            return True
        except Exception:
            return False

    def _release_lock(self) -> bool:
        """Simulates EXEC CICS DEQ."""
        try:
            if self._named_counter_lock.locked():
                self._named_counter_lock.release()
            return True
        except RuntimeError:
            return False