from dataclasses import dataclass
from enum import Enum
from typing import Optional

class CICSRespCode(Enum):
    NORMAL = 0
    # TODO: Add more response codes as needed

@dataclass
class WSCommArea:
    eye: str
    custno: str
    scode: str
    accno: int
    acc_type: str
    int_rate: float
    opened: str
    overdraft: int
    last_stmt_dt: str
    next_stmt_dt: str
    avail_bal: float
    actual_bal: float
    success: str
    fail_cd: str
    del_success: str
    del_fail_cd: str

@dataclass
class ABNDInfoRec:
    resp_code: int
    resp2_code: int
    applid: str
    taskno_key: str
    tranid: str
    date: str
    time: str
    utime_key: int
    code: str
    program: str
    sqlcode: int
    freeform: str

class BankAccountApp:
    def __init__(self):
        self.ws_comm_area = WSCommArea(
            eye="",
            custno="",
            scode="",
            accno=0,
            acc_type="",
            int_rate=0.0,
            opened="",
            overdraft=0,
            last_stmt_dt="",
            next_stmt_dt="",
            avail_bal=0.0,
            actual_bal=0.0,
            success="",
            fail_cd="",
            del_success="",
            del_fail_cd="",
        )
        self.ws_cics_resp: Optional[int] = None
        self.ws_cics_resp2: Optional[int] = None
        self.valid_data: bool = False
        self.send_erase: bool = False
        self.send_dataonly: bool = False
        self.send_dataonly_alarm: bool = False

    def process_map(self) -> None:
        self.receive_map()
        if self.ws_cics_resp != CICSRespCode.NORMAL:
            self.abend_this_task()
            return

        if self.valid_data:
            self.get_acc_data()
            if self.ws_cics_resp != CICSRespCode.NORMAL:
                self.abend_this_task()
                return

        self.send_map()

    def receive_map(self) -> None:
        # Simulate receiving a map from CICS
        self.ws_cics_resp = CICSRespCode.NORMAL
        self.ws_cics_resp2 = None

        if self.ws_cics_resp != CICSRespCode.NORMAL:
            self.abend_this_task()

    def edit_data(self) -> None:
        # Perform validation on the incoming fields
        if not self.ws_comm_area.accno:
            print("Please enter an account number.")
            self.valid_data = False
        else:
            self.valid_data = True

    def validate_data(self) -> None:
        # Perform further validation on the incoming fields
        if not self.ws_comm_area.scode or not self.ws_comm_area.accno:
            print("Please enter an account number.")
            self.valid_data = False

    def get_acc_data(self) -> None:
        # Simulate getting account data from a subprogram
        self.ws_cics_resp = CICSRespCode.NORMAL
        self.ws_cics_resp2 = None

        if self.ws_cics_resp != CICSRespCode.NORMAL:
            self.abend_this_task()

        # Set the values on the map
        self.ws_comm_area.scode = "SCODE"
        self.ws_comm_area.custno = "CUSTNO"
        self.ws_comm_area.accno = 12345
        self.ws_comm_area.acc_type = "ACC_TYPE"
        self.ws_comm_area.int_rate = 0.0
        self.ws_comm_area.opened = "OPENED"
        self.ws_comm_area.overdraft = 0
        self.ws_comm_area.last_stmt_dt = "LAST_STMT_DT"
        self.ws_comm_area.next_stmt_dt = "NEXT_STMT_DT"
        self.ws_comm_area.avail_bal = 0.0
        self.ws_comm_area.actual_bal = 0.0

    def del_acc_data(self) -> None:
        # Simulate deleting account data from a subprogram
        self.ws_cics_resp = CICSRespCode.NORMAL
        self.ws_cics_resp2 = None

        if self.ws_cics_resp != CICSRespCode.NORMAL:
            self.abend_this_task()

        # Set the values on the map
        self.ws_comm_area.scode = ""
        self.ws_comm_area.custno = ""
        self.ws_comm_area.accno = 0
        self.ws_comm_area.acc_type = ""
        self.ws_comm_area.int_rate = 0.0
        self.ws_comm_area.opened = ""
        self.ws_comm_area.overdraft = 0
        self.ws_comm_area.last_stmt_dt = ""
        self.ws_comm_area.next_stmt_dt = ""
        self.ws_comm_area.avail_bal = 0.0
        self.ws_comm_area.actual_bal = 0.0

        print("Account deleted successfully.")

    def send_map(self) -> None:
        # Simulate sending a map to CICS
        self.ws_cics_resp = CICSRespCode.NORMAL
        self.ws_cics_resp2 = None

        if self.ws_cics_resp != CICSRespCode.NORMAL:
            self.abend_this_task()

    def send_termination_msg(self) -> None:
        # Simulate sending a termination message to CICS
        self.ws_cics_resp = CICSRespCode.NORMAL
        self.ws_cics_resp2 = None

        if self.ws_cics_resp != CICSRespCode.NORMAL:
            self.abend_this_task()

    def abend_this_task(self) -> None:
        # Simulate abending the task
        print("Task abended due to error.")

        # Create an ABNDInfoRec instance
        abnd_info_rec = ABNDInfoRec(
            resp_code=self.ws_cics_resp,
            resp2_code=self.ws_cics_resp2,
            applid="APPLID",
            taskno_key="TASKNO_KEY",
            tranid="TRANID",
            date="DATE",
            time="TIME",
            utime_key=0,
            code="CODE",
            program="PROGRAM",
            sqlcode=0,
            freeform="FREEFORM",
        )

        # Print the ABNDInfoRec instance
        print(abnd_info_rec)

def main() -> None:
    app = BankAccountApp()
    app.process_map()

if __name__ == "__main__":
    main()