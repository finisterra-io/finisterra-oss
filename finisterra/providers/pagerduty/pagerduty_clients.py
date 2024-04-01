from pdpyras import APISession
import os


class PagerDutyClients:
    def __init__(self):
        PAGERDUTY_TOKEN = os.environ.get("PAGERDUTY_TOKEN")
        self.pagerduty_client = APISession(PAGERDUTY_TOKEN)
