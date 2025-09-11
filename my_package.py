from api_request import get_package, send_api_request
from auth_helper import AuthInstance

def get_my_packages_data():
    """Mengambil dan mengembalikan data paket dalam bentuk list of dicts."""
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        return None
    
    id_token = tokens.get("id_token")
    path = "api/v8/packages/quota-details"
    payload = {
        "is_enterprise": False,
        "lang": "en",
        "family_member_id": ""
    }
    
    res = send_api_request(api_key, path, payload, id_token, "POST")
    if res.get("status") != "SUCCESS":
        print("Failed to fetch packages:", res)
        return None
    
    quotas = res["data"]["quotas"]
    my_packages = []

    for quota in quotas:
        name = quota["name"]
        
        remaining_quota = "N/A"
        if "remaining_quota" in quota:
            remaining_quota = quota["remaining_quota"]

        my_packages.append({
            "name": name,
            "remaining_quota": remaining_quota,
            "quota_code": quota["quota_code"],
        })
    
    return my_packages

