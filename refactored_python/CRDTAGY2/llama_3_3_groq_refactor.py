from datetime import datetime, timedelta
import random
import time
from typing import Tuple

class CreditAgency:
    """
    A class representing a dummy credit agency.

    This class is used to delay for a random amount of time (between 0 and 3 seconds) 
    and to create a random credit score (between 1 and 999).
    """

    def __init__(self):
        """
        Initializes the CreditAgency object.
        """
        self.container_name = "CIPB"
        self.channel_name = "CIPCREDCHANN"
        self.seed = random.randint(1, 1000)
        self.delay_amount = self.generate_delay()
        self.container_len = 0
        self.cont_in = {
            "eyecatcher": "",
            "sortcode": "",
            "number": "",
            "name": "",
            "address": "",
            "date_of_birth": "",
            "credit_score": 0,
            "cs_review_date": "",
            "success": "",
            "fail_code": ""
        }
        self.cics_resp = 0
        self.cics_resp2 = 0
        self.abnd_info_rec = {
            "respcode": 0,
            "resp2code": 0,
            "applid": "",
            "taskno_key": "",
            "tranid": "",
            "date": "",
            "time": "",
            "utime_key": 0,
            "code": "",
            "program": "",
            "sqlcode": 0,
            "freeform": ""
        }

    def generate_delay(self) -> int:
        """
        Generates a random delay amount between 0 and 3 seconds.

        Returns:
            int: The delay amount in seconds.
        """
        return random.randint(0, 3)

    def delay(self) -> None:
        """
        Delays for the generated amount of time.
        """
        time.sleep(self.delay_amount)

    def get_container(self) -> Tuple[int, int]:
        """
        Gets the container from the channel.

        Returns:
            Tuple[int, int]: A tuple containing the response and response2 codes.
        """
        try:
            # Simulate getting the container from the channel
            self.container_len = len(self.cont_in)
            self.cont_in["eyecatcher"] = "EYEC"
            self.cont_in["sortcode"] = "123456"
            self.cont_in["number"] = "1234567890"
            self.cont_in["name"] = "John Doe"
            self.cont_in["address"] = "123 Main St"
            self.cont_in["date_of_birth"] = "19900101"
            self.cont_in["credit_score"] = 0
            self.cont_in["cs_review_date"] = "20220101"
            self.cont_in["success"] = "Y"
            self.cont_in["fail_code"] = ""
            return 0, 0
        except Exception as e:
            # Handle exception
            self.cics_resp = 1
            self.cics_resp2 = 1
            return self.cics_resp, self.cics_resp2

    def put_container(self) -> Tuple[int, int]:
        """
        Puts the container back into the channel.

        Returns:
            Tuple[int, int]: A tuple containing the response and response2 codes.
        """
        try:
            # Simulate putting the container back into the channel
            self.container_len = len(self.cont_in)
            return 0, 0
        except Exception as e:
            # Handle exception
            self.cics_resp = 2
            self.cics_resp2 = 2
            return self.cics_resp, self.cics_resp2

    def generate_credit_score(self) -> int:
        """
        Generates a random credit score between 1 and 999.

        Returns:
            int: The generated credit score.
        """
        return random.randint(1, 999)

    def populate_time_date(self) -> None:
        """
        Populates the time and date.
        """
        current_time = datetime.now()
        self.abnd_info_rec["utime_key"] = int(current_time.timestamp())
        self.abnd_info_rec["date"] = current_time.strftime("%Y%m%d")
        self.abnd_info_rec["time"] = current_time.strftime("%H%M%S")

    def abend_handler(self) -> None:
        """
        Handles the abend.
        """
        self.abnd_info_rec["respcode"] = self.cics_resp
        self.abnd_info_rec["resp2code"] = self.cics_resp2
        self.abnd_info_rec["code"] = "PLOP"
        self.abnd_info_rec["freeform"] = "A010 - *** The delay messed up! ***"
        # Simulate linking to the abend handler program
        print("Abend handler called")

    def process(self) -> None:
        """
        Processes the credit agency request.
        """
        self.delay()
        self.cics_resp, self.cics_resp2 = self.get_container()
        if self.cics_resp != 0 or self.cics_resp2 != 0:
            self.abend_handler()
            return
        self.cont_in["credit_score"] = self.generate_credit_score()
        self.cics_resp, self.cics_resp2 = self.put_container()
        if self.cics_resp != 0 or self.cics_resp2 != 0:
            self.abend_handler()
            return
        print("Credit score generated and container put back into channel")

def main() -> None:
    """
    The main function.
    """
    credit_agency = CreditAgency()
    credit_agency.process()

if __name__ == "__main__":
    main()