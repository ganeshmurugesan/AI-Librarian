from datetime import datetime
import random
import time

class CreditAgency:
    """
    A class to simulate a dummy credit agency.
    
    It delays for a random amount of time between 0 and 3 seconds, 
    generates a random credit score between 1 and 999, and 
    creates a container with the customer's information.
    """

    def __init__(self):
        """
        Initializes the CreditAgency class.
        
        Sets up the container name, channel name, and other variables.
        """
        self.container_name = "CIPC"
        self.channel_name = "CIPCREDCHANN"
        self.seed = random.randint(1, 100)
        self.delay_amount = 0
        self.container_len = 0
        self.new_credit_score = 0
        self.cics_resp = 0
        self.cics_resp2 = 0
        self.ws_cont_in = {
            "eyecatcher": "",
            "key": {
                "sortcode": "",
                "number": "",
            },
            "name": "",
            "address": "",
            "date_of_birth": "",
            "credit_score": 0,
            "cs_review_date": "",
            "success": "",
            "fail_code": "",
        }

    def generate_delay(self) -> None:
        """
        Generates a random delay between 0 and 3 seconds.
        
        Uses the random library to create a random number of seconds 
        to delay the program.
        """
        self.delay_amount = random.randint(0, 3)
        time.sleep(self.delay_amount)

    def get_container(self) -> None:
        """
        Retrieves the container from the channel.
        
        Uses the CICS GET CONTAINER command to retrieve the container 
        from the specified channel.
        """
        try:
            # Simulate CICS GET CONTAINER command
            self.ws_cont_in = {
                "eyecatcher": "CIPC",
                "key": {
                    "sortcode": "123456",
                    "number": "1234567890",
                },
                "name": "John Doe",
                "address": "123 Main St",
                "date_of_birth": "19900101",
                "credit_score": 0,
                "cs_review_date": "",
                "success": "",
                "fail_code": "",
            }
            self.cics_resp = 0
            self.cics_resp2 = 0
        except Exception as e:
            self.cics_resp = 1
            self.cics_resp2 = 2
            print(f"Error getting container: {e}")

    def put_container(self) -> None:
        """
        Puts the container back into the channel.
        
        Uses the CICS PUT CONTAINER command to put the container 
        back into the specified channel.
        """
        try:
            # Simulate CICS PUT CONTAINER command
            self.cics_resp = 0
            self.cics_resp2 = 0
        except Exception as e:
            self.cics_resp = 3
            self.cics_resp2 = 4
            print(f"Error putting container: {e}")

    def generate_credit_score(self) -> None:
        """
        Generates a random credit score between 1 and 999.
        
        Uses the random library to create a random credit score.
        """
        self.new_credit_score = random.randint(1, 999)
        self.ws_cont_in["credit_score"] = self.new_credit_score

    def populate_time_date(self) -> None:
        """
        Populates the time and date variables.
        
        Uses the datetime library to get the current time and date.
        """
        now = datetime.now()
        self.ws_cont_in["cs_review_date"] = now.strftime("%Y%m%d")

    def abend_handler(self) -> None:
        """
        Handles abend situations.
        
        Prints an error message and exits the program.
        """
        print("Abend situation occurred.")
        exit()

    def run(self) -> None:
        """
        Runs the CreditAgency program.
        
        Generates a delay, retrieves the container, generates a 
        credit score, puts the container back into the channel, and 
        handles abend situations.
        """
        self.generate_delay()
        self.get_container()
        if self.cics_resp != 0:
            self.abend_handler()
        self.generate_credit_score()
        self.populate_time_date()
        self.put_container()
        if self.cics_resp != 0:
            self.abend_handler()


def main() -> None:
    """
    Main function to start the CreditAgency program.
    """
    credit_agency = CreditAgency()
    credit_agency.run()


if __name__ == "__main__":
    main()