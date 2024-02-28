import CloudFlare


class CFClients:
    def __init__(self):
        self.cf = CloudFlare.CloudFlare(raw=True)
