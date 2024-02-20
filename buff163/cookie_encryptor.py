from requests.cookies import RequestsCookieJar
from base64 import b64encode
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from pkcs7 import PKCS7Encoder
import os

class CookieEncryptor:
    COOKIE_STR = [
        {'name': 'steamLoginSecure', 'domain': 'store.steampowered.com'},
        {'name': 'steamRefresh_steam', 'domain': 'login.steampowered.com'},
        {'name': 'sessionid', 'domain': 'steamcommunity.com'},
        {'name': 'steamCountry', 'domain': 'steamcommunity.com'},
        {'name': 'steamLoginSecure', 'domain': 'steamcommunity.com'}
    ]

    def __init__(self, pubkey_file):
        with open(pubkey_file, 'rb') as f:
            self.pubkey = load_pem_public_key(f.read())

        self.pkcs7_encoder = PKCS7Encoder(16)
        self.padding = padding.PKCS1v15()

    @classmethod
    def get_cookie_string(cls, cookie_jar: RequestsCookieJar):
        return '; '.join(cookie['name'] + '=' + cookie_jar.get(**cookie) for cookie in cls.COOKIE_STR)

    def encrypt(self, cookie_str: str):
        key = os.urandom(16)
        init_vector = os.urandom(16)

        encrypted_key = self.pubkey.encrypt(key, self.padding)
        cipher = Cipher(algorithms.AES(key), modes.CBC(init_vector))
        encryptor = cipher.encryptor()
        encrypted_cookies = encryptor.update(self.pkcs7_encoder.encode(cookie_str).encode('ascii')) + encryptor.finalize()
        result_encrypted = encrypted_key + init_vector + encrypted_cookies
        return b64encode(result_encrypted).decode('ascii')
