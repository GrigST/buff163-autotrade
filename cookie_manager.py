import os
from typing import Dict
from requests.cookies import RequestsCookieJar
import json


class CookieManager:
    def __init__(self, filename: str, cookie_jars: Dict[str, RequestsCookieJar], save_enabled: bool = True):
        self.filename = filename
        self.cookie_jars = cookie_jars
        self.save_enabled = save_enabled

    def load(self):
        if not os.path.exists(self.filename):
            return
        
        with open(self.filename, 'r') as f:
            cookies = json.load(f)

        for username, user_cookies in cookies.items():
            for cookie in user_cookies:
                self.cookie_jars[username].set(**cookie)

    def save(self):
        if not self.save_enabled:
            return
        
        cookies = {}
        for username, user_cookies in self.cookie_jars.items():
            cookies[username] = [{
                "name": c.name,
                "value": c.value,
                "domain": c.domain,
                "path": c.path,
                "expires": c.expires
            } for c in user_cookies]

        with open(self.filename, 'w') as f:
            json.dump(cookies, f)
