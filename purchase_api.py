from datetime import datetime, timezone, timedelta
import json
import uuid
import base64
import qrcode

import requests
from api_request import *
from crypto_helper import API_KEY, build_encrypted_field, decrypt_xdata, encryptsign_xdata, java_like_timestamp, get_x_signature_payment, get_x_signature_bounty
import time

BASE_API_URL = os.getenv("BASE_API_URL")
AX_DEVICE_ID = os.getenv("AX_DEVICE_ID")
AX_FP = os.getenv("AX_FP")
UA = os.getenv("UA")

def get_payment_methods(
    api_key: str,
    tokens: dict,
    token_confirmation: str,
    payment_target: str,
):
    payment_path = "payments/api/v8/payment-methods-option"
    payment_payload = {
        "payment_type": "PURCHASE",
        "is_enterprise": False,
        "payment_target": payment_target,
        "lang": "en",
        "is_referral": False,
        "token_confirmation": token_confirmation
    }
    
    payment_res = send_api_request(api_key, payment_path, payment_payload, tokens["id_token"], "POST")
    if payment_res["status"] != "SUCCESS":
        print("Failed to fetch payment methods.")
        print(f"Error: {payment_res}")
        return None
    
    
    
    return payment_res["data"]

def settlement_multipayment(
    api_key: str,
    tokens: dict,
    package_code: str,
    price: int,
    item_name: str,
):
    settlement_path = "payments/api/v8/settlement"
    payment_target = package_code
    amount_int = price
    
    # get token confirmation
    token_path = "v2/api/package-purchase/token"
    token_payload = {
        "offer_code": "XL_AXIATA",
        "product_type": "DATA_PACKAGE",
        "payment_for": "BUY_PACKAGE",
        "item_code": payment_target,
        "transaction_source": "digital_purchase_api",
        "lang": "en",
        "device_id": AX_DEVICE_ID,
        "device_fp": AX_FP,
    }
    token_res = send_api_request(api_key, token_path, token_payload, tokens["id_token"], "POST")
    
    if token_res["status"] != "SUCCESS":
        print(f"Failed to get token confirmation. {token_res}")
        return None
        
    token_confirmation = token_res["data"]["token"]
    
    print(f"Purchase Token: {token_confirmation}")
    
    # get payment signature
    payment_sig_time = int(time.time())
    
    encrypted_payment_token = build_encrypted_field(urlsafe_b64=True)
    encrypted_authentication_id = build_encrypted_field(urlsafe_b64=True)

    settlement_payload = {
        "is_enterprise": False,
        "lang": "en",
        "payment_for": "BUY_PACKAGE",
        "payment_method": "BALANCE",
        "encrypted_payment_token": encrypted_payment_token,
        "token": "",
        "token_confirmation": token_confirmation,
        "access_token": tokens["access_token"],
        "encrypted_authentication_id": encrypted_authentication_id,
        "authentication_id": "",
        "additional_data": {},
        "total_amount": amount_int,
        "is_using_autobuy": False,
        "items": [{
            "item_code": payment_target,
            "product_type": "DATA_PACKAGE",
            "item_price": amount_int,
            "item_name": item_name,
            "tax": 0
        }]
    }
    
    purchase_result = send_api_request(api_key, settlement_path, settlement_payload, tokens["id_token"], "POST")
    
    print("Purchase result:")
    print(purchase_result)
    
    return purchase_result
    
def settlement_bounty(\
    api_key: str,\
    tokens: dict,\
    package_code: str,\
    price: int,\
    item_name: str,\
):
    path = "v2/api/package-purchase/settle-payment"
    
    payment_target = package_code
    amount_int = price
    
    # get token confirmation
    token_path = "v2/api/package-purchase/token"
    token_payload = {
        "offer_code": "XL_AXIATA",
        "product_type": "DATA_PACKAGE",
        "payment_for": "BUY_PACKAGE",
        "item_code": payment_target,
        "transaction_source": "digital_purchase_api",
        "lang": "en",
        "device_id": AX_DEVICE_ID,
        "device_fp": AX_FP,
    }
    token_res = send_api_request(api_key, token_path, token_payload, tokens["id_token"], "POST")
    
    if token_res["status"] != "SUCCESS":
        print(f"Failed to get token confirmation. {token_res}")
        return None
        
    token_confirmation = token_res["data"]["token"]
    
    print(f"Purchase Token: {token_confirmation}")
    
    # build encrypted settlement body
    now_in_millitime = int(time.time() * 1000)
    sig_time_sec = int(now_in_millitime // 1000)
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()
    
    settlement_payload = {
        "type": "settlement",
        "device_id": AX_DEVICE_ID,
        "device_fp": AX_FP,
        "user_msisdn": "",
        "payment_target": payment_target,
        "transaction_type": "BUY_PACKAGE",
        "payment_type": "BALANCE",
        "access_token": tokens["access_token"],
        "token_confirmation": token_confirmation,
        "payment_source": "",
        "referral_unique_code": "",
        "stage_token": "",
        "stage": "",
        "device": "",
        "points_gained": 0,
        "lang": "en"
    }
    
    
    body = encryptsign_xdata(
        api_key=api_key,
        access_token=tokens["access_token"],
        sig_time_sec=sig_time_sec,
        body=settlement_payload
    )
    
    encrypted_payload = body
    
    ts_to_sign = int(time.time() * 1000 // 1000)
    x_requested_at = datetime.fromtimestamp(ts_to_sign, tz=timezone.utc).astimezone()
    
    body = encrypted_payload["encrypted_body"]
        
    x_sig = get_x_signature_bounty(
        api_key=api_key,
        access_token=tokens["access_token"],
        sig_time_sec=ts_to_sign,
        package_code=payment_target,
        token_payment=token_confirmation
    )
    
    headers = {
        "host": BASE_API_URL.replace("https://", ""),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {tokens['id_token']}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(x_requested_at),
        "x-version-app": "8.6.0",
    }
    
    url = f"{BASE_API_URL}/{path}"
    print("Sending bounty request...")
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
    
    try:
        decrypted_body = decrypt_xdata(
            api_key=api_key,
            access_token=tokens["access_token"],
            sig_time_sec=sig_time_sec,
            encrypted_body=resp.text
        )
        print("Bounty response:")
        print(decrypted_body)
        return decrypted_body
    except Exception as e:
        print(f"Failed to decrypt bounty response: {e}")
        return None

