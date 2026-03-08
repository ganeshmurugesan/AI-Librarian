import asyncio
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
import random
import logging

# Constants for error codes
ERROR_CODES = {
    1: "VSAM WRITE FAILED",
    2: "DB2 WRITE FAILED",
    3: "ENQUEUE FAILED",
    4: "VSAM READ FAILED",
    5: "DEQUEUE FAILED",
    6: "CREDIT CHECK FAILED",
    7: "INVALID TITLE",
    8: "INVALID DATE OF BIRTH"
}

@dataclass
class CustomerData:
    eyecatcher: str
    sort_code: str
    number: str
    name: str
    address: str
    date_of_birth: str
    credit_score: int
    cs_review_date: str

@dataclass
class ProctranData:
    eyecatcher: str
    sort_code: str
    acc_number: str
    date: str
    time: str
    ref: str
    type: str
    desc: str
    amount: float

class CustomerProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.customer_counter_lock = asyncio.Lock()
        self.customer_counter = 0
        self.credit_check_timeout = 3  # seconds

    async def process_customer(self, name: str, address: str, date_of_birth: str) -> Tuple[bool, Optional[CustomerData], Optional[str]]:
        """
        Process a new customer record with the following steps:
        1. Validate title
        2. Get sort code
        3. Perform credit check
        4. Get next customer number
        5. Write to customer datastore
        6. Write to proctran datastore
        7. Return results

        Returns:
            Tuple of (success: bool, customer_data: Optional[CustomerData], error_code: Optional[str])
        """
        # Step 1: Validate title
        if not self._validate_title(name):
            return False, None, '7'

        # Step 2: Get sort code (simplified for this example)
        sort_code = "123456"  # In real implementation, this would come from the input

        # Step 3: Perform credit check
        credit_score, review_date = await self._perform_credit_check(sort_code, name, address, date_of_birth)
        if credit_score is None:
            return False, None, '6'

        # Step 4: Get next customer number
        customer_number = await self._get_next_customer_number(sort_code)

        # Step 5: Write to customer datastore
        customer_data = CustomerData(
            eyecatcher="CUST",
            sort_code=sort_code,
            number=str(customer_number),
            name=name,
            address=address,
            date_of_birth=date_of_birth,
            credit_score=credit_score,
            cs_review_date=review_date
        )

        if not await self._write_customer_vsam(customer_data):
            await self._decrement_customer_counter(sort_code)
            return False, None, '1'

        # Step 6: Write to proctran datastore
        proctran_data = self._create_proctran_data(customer_data)
        if not await self._write_proctran_db2(proctran_data):
            await self._decrement_customer_counter(sort_code)
            return False, None, '2'

        # Step 7: Return success
        return True, customer_data, None

    def _validate_title(self, name: str) -> bool:
        """Validate that the name has a valid title."""
        valid_titles = {
            'Professor', 'Mr', 'Mrs', 'Miss', 'Ms', 'Dr', 'Drs',
            'Lord', 'Sir', 'Lady', ''
        }
        first_word = name.split()[0] if name else ''
        return first_word in valid_titles

    async def _perform_credit_check(self, sort_code: str, name: str, address: str, date_of_birth: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Perform asynchronous credit checks with multiple agencies.
        Returns average credit score and review date.
        """
        # Simulate async credit checks with multiple agencies
        async def check_agency(agency_id: int) -> Optional[int]:
            # Simulate network delay and random response
            await asyncio.sleep(random.uniform(0.1, 1.0))
            if random.random() < 0.9:  # 90% chance of success
                return random.randint(300, 850)
            return None

        # Run checks with all agencies
        tasks = [check_agency(i) for i in range(1, 6)]  # 5 agencies
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=self.credit_check_timeout)
        except asyncio.TimeoutError:
            self.logger.warning("Credit check timeout")
            results = []

        valid_scores = [score for score in results if score is not None]

        if not valid_scores:
            today = datetime.now().strftime("%d%m%Y")
            return 0, today

        avg_score = sum(valid_scores) // len(valid_scores)
        review_date = (datetime.now() + timedelta(days=random.randint(1, 21))).strftime("%d%m%Y")

        return avg_score, review_date

    async def _get_next_customer_number(self, sort_code: str) -> int:
        """Get the next customer number with proper locking."""
        async with self.customer_counter_lock:
            # In a real implementation, this would read from VSAM
            self.customer_counter += 1
            return self.customer_counter

    async def _write_customer_vsam(self, customer_data: CustomerData) -> bool:
        """
        Write customer data to VSAM with proper locking.
        Simulates VSAM READ UPDATE locking.
        """
        # Simulate VSAM write with retry logic
        for attempt in range(3):
            try:
                # In a real implementation, this would use actual VSAM calls
                # with proper locking (READ UPDATE)
                self.logger.info(f"Writing customer {customer_data.number} to VSAM")
                return True
            except Exception as e:
                self.logger.warning(f"VSAM write attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(1)
        return False

    async def _decrement_customer_counter(self, sort_code: str) -> None:
        """Decrement the customer counter when a write fails."""
        async with self.customer_counter_lock:
            if self.customer_counter > 0:
                self.customer_counter -= 1

    def _create_proctran_data(self, customer_data: CustomerData) -> ProctranData:
        """Create proctran record from customer data."""
        now = datetime.now()
        return ProctranData(
            eyecatcher="PRTR",
            sort_code=customer_data.sort_code,
            acc_number="00000000",
            date=now.strftime("%d.%m.%Y"),
            time=now.strftime("%H:%M:%S"),
            ref=str(random.randint(100000000000, 999999999999)),
            type="OCC",
            desc=f"{customer_data.sort_code}{customer_data.number}{customer_data.name[:14]}{customer_data.date_of_birth[:10]}",
            amount=0.0
        )

    async def _write_proctran_db2(self, proctran_data: ProctranData) -> bool:
        """Write proctran data to DB2."""
        # Simulate DB2 write with retry logic
        for attempt in range(3):
            try:
                # In a real implementation, this would use actual DB2 calls
                self.logger.info(f"Writing proctran record for {proctran_data.sort_code}")
                return True
            except Exception as e:
                self.logger.warning(f"DB2 write attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(1)
        return False