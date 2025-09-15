import os, json, uuid, requests, time
from datetime import datetime, timezone, timedelta
from crypto_helper import encryptsign_xdata, java_like_timestamp, ts_gmt7_without_colon, ax_api_signature, decrypt_xdata, get_x_signature_payment, build_encrypted_field

BASE_API_URL = "https://api.myxl.xlaxiata.co.id"
BASE_CIAM_URL = "https://gede.ciam.xlaxiata.co.id"
GET_OTP_URL = BASE_CIAM_URL + "/realms/xl-ciam/auth/otp"
BASIC_AUTH = "OWZjOTdlZDEtNmEzMC00OGQ1LTk1MTYtNjBjNTNjZTNhMTM1OllEV21GNExKajlYSUt3UW56eTJlMmxiMHRKUWIyOW8z"
AX_DEVICE_ID = "92fb44c0804233eb4d9e29f838223a14"
AX_FP = "18b4d589826af50241177961590e6693"
SUBMIT_OTP_URL = BASE_CIAM_URL + "/realms/xl-ciam/protocol/openid-connect/token"
UA = "myXL / 8.6.0(1179); com.android.vending; (samsung; SM-N935F; SDK 33; Android 13"

def validate_contact(contact: str) -> bool:
    if not contact.startswith("628") or len(contact) > 14:
        return False
    return True

def get_otp(contact: str) -> str:
    if not validate_contact(contact):
        return None
    
    url = GET_OTP_URL

    querystring = {
        "contact": contact,
        "contactType": "SMS",
        "alternateContact": "false"
    }
    
    now = datetime.now(timezone(timedelta(hours=7)))
    ax_request_at = java_like_timestamp(now)
    ax_request_id = str(uuid.uuid4())

    payload = ""
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Authorization": f"Basic {BASIC_AUTH}",
        "Ax-Device-Id": AX_DEVICE_ID,
        "Ax-Fingerprint": AX_FP,
        "Ax-Request-At": ax_request_at,
        "Ax-Request-Device": "samsung",
        "Ax-Request-Device-Model": "SM-N935F",
        "Ax-Request-Id": ax_request_id,
        "Ax-Substype": "PREPAID",
        "Content-Type": "application/json",
        "Host": BASE_CIAM_URL.replace("https://", ""),
        "User-Agent": UA,
    }

    try:
        response = requests.request("GET", url, data=payload, headers=headers, params=querystring, timeout=30)
        json_body = json.loads(response.text)
    
        if "subscriber_id" not in json_body:
            return None
        
        return json_body["subscriber_id"]
    except Exception as e:
        return None
    
def submit_otp(api_key: str, contact: str, code: str):
    if not validate_contact(contact):
        return None
    
    if not code or len(code) != 6:
        return None
    
    url = SUBMIT_OTP_URL

    now_gmt7 = datetime.now(timezone(timedelta(hours=7)))
    ts_for_sign = ts_gmt7_without_colon(now_gmt7)
    ts_header = ts_gmt7_without_colon(now_gmt7 - timedelta(minutes=5))
    signature = ax_api_signature(api_key, ts_for_sign, contact, code, "SMS")

    payload = f"contactType=SMS&code={code}&grant_type=password&contact={contact}&scope=openid"

    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Authorization": f"Basic {BASIC_AUTH}",
        "Ax-Api-Signature": signature,
        "Ax-Device-Id": AX_DEVICE_ID,
        "Ax-Fingerprint": AX_FP,
        "Ax-Request-At": ts_header,
        "Ax-Request-Device": "samsung",
        "Ax-Request-Device-Model": "SM-N935F",
        "Ax-Request-Id": str(uuid.uuid4()),
        "Ax-Substype": "PREPAID",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": UA,
    }

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        json_body = json.loads(response.text)
        
        if "error" in json_body:
            return None
        
        return json_body
    except requests.RequestException as e:
        return None

def get_new_token(refresh_token: str) -> str:
    url = SUBMIT_OTP_URL

    now = datetime.now(timezone(timedelta(hours=7)))
    ax_request_at = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0700"
    ax_request_id = str(uuid.uuid4())

    headers = {
        "Host": BASE_CIAM_URL.replace("https://", ""),
        "ax-request-at": ax_request_at,
        "ax-device-id": AX_DEVICE_ID,
        "ax-request-id": ax_request_id,
        "ax-request-device": "samsung",
        "ax-request-device-model": "SM-N935F",
        "ax-fingerprint": AX_FP,
        "authorization": f"Basic {BASIC_AUTH}",
        "user-agent": UA,
        "ax-substype": "PREPAID",
        "content-type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    resp = requests.post(url, headers=headers, data=data, timeout=30)
    if resp.status_code == 400:
        if resp.json().get("error_description") == "Session not active":
            return None
        
    resp.raise_for_status()

    body = resp.json()
    
    if "id_token" not in body:
        raise ValueError("ID token not found in response")
    if "error" in body:
        raise ValueError(f"Error in response: {body['error']} - {body.get('error_description', '')}")
    
    return body

def send_api_request(
    api_key: str,
    path: str,
    payload_dict: dict,
    id_token: str,
    method: str = "POST",
):
    encrypted_payload = encryptsign_xdata(
        api_key=api_key,
        method=method,
        path=path,
        id_token=id_token,
        payload=payload_dict
    )
    
    xtime = int(encrypted_payload["encrypted_body"]["xtime"])
    sig_time_sec = (xtime // 1000)

    body = encrypted_payload["encrypted_body"]
    x_sig = encrypted_payload["x_signature"]
    
    headers = {
        "host": BASE_API_URL.replace("https://", ""),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": api_key,
        "authorization": f"Bearer {id_token}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(datetime.now(timezone(timedelta(hours=7)))),
        "x-version-app": "8.6.0",
    }

    url = f"{BASE_API_URL}/{path}"
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)

    try:
        decrypted_body = decrypt_xdata(api_key, json.loads(resp.text))
        return decrypted_body
    except Exception as e:
        return None

def get_balance(api_key: str, id_token: str) -> dict:
    path = "api/v8/packages/balance-and-credit"
    
    raw_payload = {
        "is_enterprise": False,
        "lang": "en"
    }
    
    res = send_api_request(api_key, path, raw_payload, id_token, "POST")
    
    if "data" in res and "balance" in res["data"]:
        return res["data"]["balance"]
    else:
        return None
    
def get_family(api_key: str, tokens: dict, family_code: str) -> dict:
    path = "api/v8/xl-stores/options/list"
    id_token = tokens.get("id_token")
    payload_dict = {
        "is_show_tagging_tab": True,
        "is_dedicated_event": True,
        "is_transaction_routine": False,
        "migration_type": "NONE",
        "package_family_code": family_code,
        "is_autobuy": False,
        "is_enterprise": False,
        "is_pdlp": True,
        "referral_code": "",
        "is_migration": False,
        "lang": "en"
    }
    
    res = send_api_request(api_key, path, payload_dict, id_token, "POST")
    if res.get("status") != "SUCCESS":
        return None
    
    return res["data"]

def get_package(api_key: str, tokens: dict, package_option_code: str) -> dict:
    path = "api/v8/xl-stores/options/detail"
    
    raw_payload = {
        "is_transaction_routine": False,
        "migration_type": "NONE",
        "package_family_code": "",
        "family_role_hub": "",
        "is_autobuy": False,
        "is_enterprise": False,
        "is_shareable": False,
        "is_migration": False,
        "lang": "en",
        "package_option_code": package_option_code,
        "is_upsell_pdp": False,
        "package_variant_code": ""
    }
    
    res = send_api_request(api_key, path, raw_payload, tokens["id_token"], "POST")
    
    if "data" not in res:
        return None
        
    return res["data"]
