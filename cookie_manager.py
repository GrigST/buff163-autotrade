import os
from typing import Dict
from requests.cookies import RequestsCookieJar
import json


class CookieManager:
    def __init__(self, filename: str, cookie_jars: Dict[str, RequestsCookieJar], save_enabled: bool = True):
        self.filename = filename
        self.cookie_jars = cookie_jars
        self.save_enabled = save_enabled
        self.cookies = {}

    def load(self):
        if not os.path.exists(self.filename):
            return
        
        with open(self.filename, 'r') as f:
            self.cookies = json.load(f)

        for username, user_cookies in self.cookies.items():
            if username in self.cookie_jars:
                for cookie in user_cookies:
                    self.cookie_jars[username].set(**cookie)

    def save(self):
        if not self.save_enabled:
            return
        
        for username, user_cookies in self.cookie_jars.items():
            self.cookies[username] = [{
                "name": c.name,
                "value": c.value,
                "domain": c.domain,
                "path": c.path,
                "expires": c.expires
            } for c in user_cookies]

        with open(self.filename, 'w') as f:
            json.dump(self.cookies, f)
