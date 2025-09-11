import os, hmac, hashlib, requests, brotli, zlib, base64
from datetime import datetime, timezone, timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

API_KEY = os.getenv("API_KEY")

XDATA_DECRYPT_URL = "https://crypto.mashu.lol/api/decrypt"
XDATA_ENCRYPT_SIGN_URL = "https://crypto.mashu.lol/api/encryptsign"
PAYMENT_SIGN_URL = "https://crypto.mashu.lol/api/sign-payment"
BOUNTY_SIGN_URL = "https://crypto.mashu.lol/api/sign-bounty"
AX_SIGN_URL = "https://crypto.mashu.lol/api/sign-ax"

AES_KEY_ASCII = os.getenv("AES_KEY_ASCII")
BLOCK = AES.block_size

def random_iv_hex16() -> str:
    return os.urandom(8).hex()

def b64(data: bytes, urlsafe: bool) -> str:
    enc = base64.urlsafe_b64encode if urlsafe else base64.b64encode
    return enc(data).decode("ascii")

def build_encrypted_field(iv_hex16: str | None = None, urlsafe_b64: bool = False) -> str:
    key = AES_KEY_ASCII.encode("ascii")
    iv_hex = iv_hex16 or random_iv_hex16()
    iv = iv_hex.encode("ascii") 

    pt = pad(b"", AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    ct = cipher.encrypt(pt)

    return b64(iv, urlsafe_b64) + b64(ct, urlsafe_b64)

def hmac_sha256(key: str, message: str) -> str:
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()

def hmac_sha256_bytes(key: bytes, message: bytes) -> bytes:
    return hmac.new(key, message, hashlib.sha256).digest()

def encryptsign_xdata(api_key: str, access_token: str, sig_time_sec: int, body: dict) -> dict:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }
    
    request_body = {
        "access_token": access_token,
        "sig_time_sec": sig_time_sec,
        "body": body
    }
    
    response = requests.request("POST", XDATA_ENCRYPT_SIGN_URL, json=request_body, headers=headers, timeout=30)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Encryption failed: {response.text}")

def decrypt_xdata(api_key: str, access_token: str, sig_time_sec: int, encrypted_body: str) -> dict:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }
    
    request_body = {
        "access_token": access_token,
        "sig_time_sec": sig_time_sec,
        "encrypted_body": encrypted_body
    }
    
    response = requests.request("POST", XDATA_DECRYPT_URL, json=request_body, headers=headers, timeout=30)
    
    if response.status_code == 200:
        return response.json().get("body")
    else:
        raise Exception(f"Decryption failed: {response.text}")

def java_like_timestamp(date: datetime) -> str:
    return date.strftime('%a, %d %b %Y %H:%M:%S GMT+0700')

def ts_gmt7_without_colon() -> str:
    return datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%d %H%M%S')

def ax_api_signature(api_key: str, x_requested_at: str, encrypted_body: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }
    
    request_body = {
        "x_requested_at": x_requested_at,
        "encrypted_body": encrypted_body
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

