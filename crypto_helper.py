import os, hmac, hashlib, requests, brotli, zlib, base64
from datetime import datetime, timezone, timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from typing import Union

# Variabel Lingkungan
API_KEY = os.getenv("API_KEY")
AES_KEY_ASCII = os.getenv("AES_KEY_ASCII")

# Endpoint
XDATA_DECRYPT_URL = "https://crypto.mashu.lol/api/decrypt"
XDATA_ENCRYPT_SIGN_URL = "https://crypto.mashu.lol/api/encryptsign"
PAYMENT_SIGN_URL = "https://crypto.mashu.lol/api/sign-payment"
BOUNTY_SIGN_URL = "https://crypto.mashu.lol/api/sign-bounty"
AX_SIGN_URL = "https://crypto.mashu.lol/api/sign-ax"

# AES
BLOCK = AES.block_size

def random_iv_hex16() -> str:
    return os.urandom(8).hex()

def b64(data: bytes, urlsafe: bool) -> str:
    enc = base64.urlsafe_b64encode if urlsafe else base64.b64encode
    return enc(data).decode("ascii")

def build_encrypted_field(iv_hex16: Union[str, None] = None, urlsafe_b64: bool = False) -> str:
    key = AES_KEY_ASCII.encode("ascii")
    iv_hex = iv_hex16 or random_iv_hex16()
    iv = iv_hex.encode("ascii") 
    pt = pad(b"", AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct = cipher.encrypt(pt)
    if urlsafe_b64:
        return b64(ct, True)
    return b64(ct, False)

def encryptsign_xdata(
        api_key: str,
        method: str,
        path: str,
        id_token: str,
        payload: dict
    ) -> dict:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }
    
    request_body = {
        "method": method,
        "path": path,
        "id_token": id_token,
        "payload": payload,
        "aes_key": AES_KEY_ASCII,
    }
    
    response = requests.request("POST", XDATA_ENCRYPT_SIGN_URL, json=request_body, headers=headers, timeout=30)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Encryption failed: {response.text}")
    
def decrypt_xdata(api_key: str, payload: dict) -> dict:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }
    
    request_body = {
        "payload": payload,
        "aes_key": AES_KEY_ASCII,
    }
    
    response = requests.request("POST", XDATA_DECRYPT_URL, json=request_body, headers=headers, timeout=30)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Decryption failed: {response.text}")

def java_like_timestamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0700"

def ts_gmt7_without_colon(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")

def ax_api_signature(
        api_key: str,
        ts: str,
        contact: str,
        code: str,
        contact_type: str
    ) -> str:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }
    
    request_body = {
        "ts": ts,
        "contact": contact,
        "code": code,
        "contact_type": contact_type,
    }
    
    response = requests.request("POST", AX_SIGN_URL, json=request_body, headers=headers, timeout=30)
    
    if response.status_code == 200:
        return response.json().get("x_signature")
    else:
        raise Exception(f"Signature generation failed: {response.text}")
    
def get_x_signature_payment(
        api_key: str,
        access_token: str,
        sig_time_sec: int,
        package_code: str,
        token_payment: str,
        payment_method: str
    ) -> str:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }
    
    request_body = {
        "access_token": access_token,
        "sig_time_sec": sig_time_sec,
        "package_code": package_code,
        "token_payment": token_payment,
        "payment_method": payment_method
    }
    
    response = requests.request("POST", PAYMENT_SIGN_URL, json=request_body, headers=headers, timeout=30)
    
    if response.status_code == 200:
        return response.json().get("x_signature")
    else:
        raise Exception(f"Signature generation failed: {response.text}")
    
def get_x_signature_bounty(
        api_key: str,
        access_token: str,
        sig_time_sec: int,
        package_code: str,
        token_payment: str
    ) -> str:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }
    
    request_body = {
        "access_token": access_token,
        "sig_time_sec": sig_time_sec,
        "package_code": package_code,
        "token_payment": token_payment
    }
    
    response = requests.request("POST", BOUNTY_SIGN_URL, json=request_body, headers=headers, timeout=30)
    
    if response.status_code == 200:
        return response.json().get("x_signature")
    else:
        raise Exception(f"Signature generation failed: {response.text}")
