import os, json, uuid, requests, time
from datetime import datetime, timezone, timedelta

from crypto_helper import encryptsign_xdata, java_like_timestamp, ts_gmt7_without_colon, ax_api_signature, decrypt_xdata, API_KEY, get_x_signature_payment, build_encrypted_field

BASE_API_URL = os.getenv("BASE_API_URL")
BASE_CIAM_URL = os.getenv("BASE_CIAM_URL")
GET_OTP_URL = BASE_CIAM_URL + "/realms/xl-ciam/auth/otp"
BASIC_AUTH = os.getenv("BASIC_AUTH")
AX_DEVICE_ID = os.getenv("AX_DEVICE_ID")
AX_FP = os.getenv("AX_FP")
SUBMIT_OTP_URL = BASE_CIAM_URL + "/realms/xl-ciam/protocol/openid-connect/token"
UA = os.getenv("UA")

def validate_contact(contact: str) -> bool:
    if not contact.startswith("628") or len(contact) > 14:
        print("Invalid number")
        return False
    return True

def get_otp(contact: str) -> str:
    # Contact example: "6287896089467"
    if not validate_contact(contact):
        return None
    
    url = GET_OTP_URL

    querystring = {
        "contact": contact,
        "contactType": "SMS",
        "alternateContact": "false"
    }
    
    now = datetime.now(timezone(timedelta(hours=7)))
    x_requested_at = java_like_timestamp(now)
    ts = now.strftime('%Y%m%d%H%M%S')
    
    headers = {
        "host": BASE_CIAM_URL.replace("https://", ""),
        "content-type": "application/json",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Basic {BASIC_AUTH}",
        "x-hv": "v3",
        "x-version-app": "8.6.0",
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": x_requested_at,
        "x-signature-time": ts,
        "x-signature": ax_api_signature(API_KEY, x_requested_at, "{}"),
        "x-device-id": AX_DEVICE_ID,
        "x-fp": AX_FP,
        "encrypted-device-id": build_encrypted_field(urlsafe_b64=True)
    }

    try:
        response = requests.request("GET", url, headers=headers, params=querystring, timeout=30)
        return response.json()
    except requests.RequestException as e:
        print(f"Error getting OTP: {e}")
        return None


def submit_otp_code(contact: str, otp_code: str) -> dict:
    url = SUBMIT_OTP_URL
    now = datetime.now(timezone(timedelta(hours=7)))
    x_requested_at = java_like_timestamp(now)
    ts = now.strftime('%Y%m%d%H%M%S')
    
    payload = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "client_id": "api-client",
        "audience": "account",
        "source_msisdn": contact,
        "source_otp": otp_code,
        "source_service": "OTP"
    }
    
    headers = {
        "host": BASE_CIAM_URL.replace("https://", ""),
        "content-type": "application/json",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Basic {BASIC_AUTH}",
        "x-hv": "v3",
        "x-version-app": "8.6.0",
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": x_requested_at,
        "x-signature-time": ts,
        "x-signature": ax_api_signature(API_KEY, x_requested_at, json.dumps(payload)),
        "x-device-id": AX_DEVICE_ID,
        "x-fp": AX_FP,
        "encrypted-device-id": build_encrypted_field(urlsafe_b64=True)
    }

    try:
        response = requests.request("POST", url, headers=headers, json=payload, timeout=30)
        return response.json()
    except requests.RequestException as e:
        print(f"Error submitting OTP: {e}")
        return None
        
def send_api_request(api_key: str, path: str, payload: dict, id_token: str, method: str) -> dict:
    url = f"{BASE_API_URL}/{path}"
    
    sig_time = int(time.time())
    x_requested_at = datetime.fromtimestamp(sig_time, tz=timezone.utc).astimezone()
    
    enc_res = encryptsign_xdata(
        api_key=api_key,
        access_token=id_token,
        sig_time_sec=sig_time,
        body=payload
    )
    
    encrypted_body = enc_res["encrypted_body"]
    
    x_sig = ax_api_signature(
        api_key=api_key,
        x_requested_at=java_like_timestamp(x_requested_at),
        encrypted_body=encrypted_body
    )
    
    headers = {
        "host": BASE_API_URL.replace("https://", ""),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {id_token}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(x_requested_at),
        "x-version-app": "8.6.0",
        "x-device-id": AX_DEVICE_ID,
        "x-fp": AX_FP,
        "encrypted-device-id": build_encrypted_field(urlsafe_b64=True)
    }
    
    try:
        if method == "POST":
            response = requests.request(method, url, headers=headers, data=encrypted_body, timeout=30)
        else:
            response = requests.request(method, url, headers=headers, params=payload, timeout=30)
        
        dec_body = decrypt_xdata(
            api_key=api_key,
            access_token=id_token,
            sig_time_sec=sig_time,
            encrypted_body=response.text
        )
        return dec_body
    except requests.RequestException as e:
        print(f"Error sending API request: {e}")
        return {"status": "FAILED", "message": str(e)}

def get_balance(api_key: str, id_token: str) -> dict:
    path = "account/api/v8/balance"
    payload = {
        "lang": "en"
    }
    return send_api_request(api_key, path, payload, id_token, "GET")

def get_new_token(refresh_token: str) -> dict:
    url = SUBMIT_OTP_URL
    now = datetime.now(timezone(timedelta(hours=7)))
    x_requested_at = java_like_timestamp(now)
    ts = now.strftime('%Y%m%d%H%M%S')
    
    payload = {
        "grant_type": "refresh_token",
        "client_id": "api-client",
        "refresh_token": refresh_token
    }
    
    headers = {
        "host": BASE_CIAM_URL.replace("https://", ""),
        "content-type": "application/json",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Basic {BASIC_AUTH}",
        "x-hv": "v3",
        "x-version-app": "8.6.0",
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": x_requested_at,
        "x-signature-time": ts,
        "x-signature": ax_api_signature(API_KEY, x_requested_at, json.dumps(payload)),
        "x-device-id": AX_DEVICE_ID,
        "x-fp": AX_FP,
        "encrypted-device-id": build_encrypted_field(urlsafe_b64=True)
    }

    try:
        response = requests.request("POST", url, headers=headers, json=payload, timeout=30)
        return response.json()
    except requests.RequestException as e:
        print(f"Error getting new token: {e}")
        return None
        
def get_family(api_key: str, tokens: dict, family_code: str) -> dict:
    id_token = tokens.get("id_token")
    path = f"packages/api/v8/packages-by-family-code/{family_code}"
    payload = {
        "lang": "en",
        "access_token": id_token,
        "offer_code": "XL_AXIATA",
        "product_type": "DATA_PACKAGE"
    }
    
    res = send_api_request(api_key, path, payload, id_token, "GET")
    
    if res.get("status") != "SUCCESS":
        print(f"Failed to load family data. {res}")
        return None
        
    return res["data"]
    
def get_package(api_key: str, tokens: dict, package_code: str) -> dict:
    id_token = tokens.get("id_token")
    path = f"packages/api/v8/package/{package_code}"
    payload = {
        "lang": "en",
        "access_token": id_token
    }
    
    res = send_api_request(api_key, path, payload, id_token, "GET")
    
    if res.get("status") != "SUCCESS":
        print(f"Failed to load package data. {res}")
        return None
        
    return res["data"]

