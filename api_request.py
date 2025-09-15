import os, json, uuid, requests, time
from datetime import datetime, timezone, timedelta

# Variabel Lingkungan
BASE_API_URL = "https://api.myxl.xlaxiata.co.id"
BASE_CIAM_URL = "https://gede.ciam.xlaxiata.co.id"
BASIC_AUTH = "OWZjOTdlZDEtNmEzMC00OGQ1LTk1MTYtNjBjNTNjZTNhMTM1OllEV21GNExKajlYSUt3UW56eTJlMmxiMHRKUWIyOW8z"
AX_DEVICE_ID = "92fb44c0804233eb4d9e29f838223a14"
AX_FP = "18b4d589826af50241177961590e6693"
UA = "myXL / 8.6.0(1179); com.android.vending; (samsung; SM-N935F; SDK 33; Android 13"

# Endpoint
GET_OTP_URL = BASE_CIAM_URL + "/realms/xl-ciam/auth/otp"
SUBMIT_OTP_URL = BASE_CIAM_URL + "/realms/xl-ciam/protocol/openid-connect/token"

def validate_contact(contact: str) -> bool:
    if not contact.startswith("628") or len(contact) > 14:
        return False
    return True

def get_otp(contact: str) -> str:
    if not validate_contact(contact):
        return None
    
    headers = {
        "Host": "gede.ciam.xlaxiata.co.id",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "User-Agent": UA,
        "Authorization": f"Basic {BASIC_AUTH}"
    }

    querystring = {
        "contact": contact,
        "contactType": "SMS",
        "alternateContact": "false"
    }
    
    try:
        response = requests.post(GET_OTP_URL, json=querystring, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("subscriber_id")
    except requests.exceptions.RequestException as e:
        print(f"Error getting OTP: {e}")
        return None

def submit_otp(api_key: str, contact: str, otp: str) -> dict:
    headers = {
        "Host": "gede.ciam.xlaxiata.co.id",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "User-Agent": UA,
        "Authorization": f"Basic {BASIC_AUTH}"
    }

    payload = {
        "grant_type": "otp",
        "contact": contact,
        "otp_code": otp,
        "scope": "openid",
        "x-ax-device-id": AX_DEVICE_ID,
        "x-ax-fp": AX_FP,
    }
    
    try:
        response = requests.post(SUBMIT_OTP_URL, data=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error submitting OTP: {e}")
        return None

def get_new_token(refresh_token: str) -> dict:
    headers = {
        "Host": "gede.ciam.xlaxiata.co.id",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "User-Agent": UA,
        "Authorization": f"Basic {BASIC_AUTH}"
    }

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "openid",
        "x-ax-device-id": AX_DEVICE_ID,
        "x-ax-fp": AX_FP,
    }

    try:
        response = requests.post(SUBMIT_OTP_URL, data=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting new token: {e}")
        return None

def send_api_request(api_key: str, path: str, payload: dict, id_token: str, method: str = "POST") -> dict:
    url = f"{BASE_API_URL}/{path}"
    headers = {
        "Host": "api.myxl.xlaxiata.co.id",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": UA,
        "Authorization": f"Bearer {id_token}",
        "X-API-KEY": api_key,
        "X-HV": "v3"
    }
    
    try:
        if method.upper() == "POST":
            response = requests.post(url, json=payload, headers=headers, timeout=30)
        else:
            response = requests.get(url, params=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending API request: {e}")
        return {"status": "FAILED", "error": str(e)}

def get_balance(api_key: str, id_token: str) -> dict:
    path = "api/v8/balance/detail"
    payload = {}
    response = send_api_request(api_key, path, payload, id_token, "POST")
    return response.get("data", {})

def get_family(api_key: str, tokens: dict, family_code: str) -> dict:
    path = "api/v8/package/info"
    payload = {
        "package_family_code": family_code
    }
    response = send_api_request(api_key, path, payload, tokens["id_token"], "POST")
    return response.get("data", {})

def get_package(api_key: str, tokens: dict, package_code: str) -> dict:
    path = "api/v8/package/info"
    payload = {
        "package_option_code": package_code
    }
    response = send_api_request(api_key, path, payload, tokens["id_token"], "POST")
    return response.get("data", {})
