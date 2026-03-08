from dataclasses import dataclass
from datetime import datetime
from random import randint, seed
from time import sleep
from typing import Tuple

@dataclass
class CreditInfo:
    """Data class to hold credit information"""
    sort_code: str
    number: str
    name: str
    address: str
    date_of_birth: str
    credit_score: int
    cs_review_date: str
    success: str
    fail_code: str

class CreditAgency:
    """Class to simulate a credit agency"""
    def __init__(self, container_name: str, channel_name: str):
        """
        Initialize the credit agency with a container and channel name

        Args:
        container_name (str): The name of the container
        channel_name (str): The name of the channel
        """
        self.container_name = container_name
        self.channel_name = channel_name
        self.credit_info = CreditInfo(
            sort_code="",
            number="",
            name="",
            address="",
            date_of_birth="",
            credit_score=0,
            cs_review_date="",
            success="",
            fail_code=""
        )

    def generate_delay(self, seed_value: int) -> int:
        """
        Generate a random delay between 0 and 3 seconds

        Args:
        seed_value (int): The seed value for the random number generator

        Returns:
        int: The delay in seconds
        """
        seed(seed_value)
        return randint(0, 3)

    def get_credit_info(self) -> Tuple[int, int]:
        """
        Get the credit information from the container

        Returns:
        Tuple[int, int]: The response and response2 codes
        """
        # Simulate the GET CONTAINER operation
        self.credit_info.sort_code = "123456"
        self.credit_info.number = "1234567890"
        self.credit_info.name = "John Doe"
        self.credit_info.address = "123 Main St"
        self.credit_info.date_of_birth = "19900101"
        self.credit_info.credit_score = 0
        self.credit_info.cs_review_date = "20220101"
        self.credit_info.success = "Y"
        self.credit_info.fail_code = "0"

        # Simulate the response codes
        response = 0
        response2 = 0

        return response, response2

    def put_credit_info(self) -> Tuple[int, int]:
        """
        Put the updated credit information into the container

        Returns:
        Tuple[int, int]: The response and response2 codes
        """
        # Simulate the PUT CONTAINER operation
        # Generate a new credit score
        self.credit_info.credit_score = randint(1, 999)

        # Simulate the response codes
        response = 0
        response2 = 0

        return response, response2

    def process_credit_info(self) -> None:
        """
        Process the credit information
        """
        delay = self.generate_delay(123)
        sleep(delay)

        response, response2 = self.get_credit_info()
        if response != 0:
            print(f"Error getting credit info: {response}, {response2}")
            return

        response, response2 = self.put_credit_info()
        if response != 0:
            print(f"Error putting credit info: {response}, {response2}")
            return

        print("Credit info processed successfully")

def main() -> None:
    """Main function"""
    agency = CreditAgency("CIPD", "CIPCREDCHANN")
    agency.process_credit_info()

if __name__ == "__main__":
    main()