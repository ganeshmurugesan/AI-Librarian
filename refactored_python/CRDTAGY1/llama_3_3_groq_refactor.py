import random
import time
from dataclasses import dataclass
from typing import Dict

@dataclass
class ContainerData:
    """
    Data class to represent container data.
    """
    eyecatcher: str
    sortcode: int
    number: int
    name: str
    address: str
    date_of_birth: str
    credit_score: int
    cs_review_date: str
    success: str
    fail_code: str

class CreditAgency:
    """
    Class to represent the credit agency.
    """

    def __init__(self):
        """
        Initializes the credit agency.
        """
        self.container_name = 'CIPA'
        self.channel_name = 'CIPCREDCHANN'
        self.delay_amount = 0
        self.container_len = 0
        self.new_credit_score = 0
        self.seed = 0

    def delay(self) -> None:
        """
        Generates a random delay between 0 and 3 seconds.
        """
        self.seed = int(time.time())
        self.delay_amount = random.randint(0, 3)
        time.sleep(self.delay_amount)

    def get_container(self) -> Dict:
        """
        Gets the container data.
        
        Returns:
            Dict: Container data.
        """
        container_data = ContainerData(
            eyecatcher='',
            sortcode=0,
            number=0,
            name='',
            address='',
            date_of_birth='',
            credit_score=0,
            cs_review_date='',
            success='',
            fail_code=''
        )
        # Simulate CICS GET CONTAINER
        container_data.eyecatcher = 'CIPA'
        container_data.sortcode = 123456
        container_data.number = 1234567890
        container_data.name = 'John Doe'
        container_data.address = '123 Main St'
        container_data.date_of_birth = '19900101'
        return container_data.__dict__

    def put_container(self, container_data: Dict) -> None:
        """
        Puts the container data.
        
        Args:
            container_data (Dict): Container data.
        """
        # Simulate CICS PUT CONTAINER
        print(f'Container data: {container_data}')

    def generate_credit_score(self) -> int:
        """
        Generates a random credit score between 1 and 999.
        
        Returns:
            int: Credit score.
        """
        return random.randint(1, 999)

    def process(self) -> None:
        """
        Processes the credit agency data.
        """
        self.delay()
        container_data = self.get_container()
        self.new_credit_score = self.generate_credit_score()
        container_data['credit_score'] = self.new_credit_score
        self.put_container(container_data)

    def handle_error(self, resp: int, resp2: int) -> None:
        """
        Handles errors.
        
        Args:
            resp (int): Response code.
            resp2 (int): Response code 2.
        """
        error_codes = {
            1: 'Error 1',
            2: 'Error 2',
            3: 'Error 3',
            4: 'Error 4',
            5: 'Error 5',
            6: 'Error 6',
            7: 'Error 7',
            8: 'Error 8'
        }
        print(f'Error: {error_codes.get(resp, "Unknown error")}')
        print(f'Response code: {resp}, Response code 2: {resp2}')

def main() -> None:
    """
    Main function.
    """
    credit_agency = CreditAgency()
    try:
        credit_agency.process()
    except Exception as e:
        credit_agency.handle_error(1, 0)

if __name__ == '__main__':
    main()