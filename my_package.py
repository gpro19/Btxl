from api_request import get_package, send_api_request
from auth_helper import AuthInstance

def fetch_my_packages(id_token: str):
    api_key = AuthInstance.api_key
    
    path = "api/v8/packages/quota-details"
    
    payload = {
        "is_enterprise": False,
        "lang": "en",
        "family_member_id": ""
    }
    
    res = send_api_request(api_key, path, payload, id_token, "POST")
    if res.get("status") != "SUCCESS":
        return None
    
    quotas = res["data"]["quotas"]
    
    my_packages =[]
    for quota in quotas:
        quota_code = quota["quota_code"]
        name = quota["name"]
        family_code = "N/A"
        
        # Ambil family code
        package_details = get_package(api_key, {"id_token": id_token}, quota_code)
        if package_details:
            family_code = package_details.get("package_family", {}).get("package_family_code", "N/A")
        
        my_packages.append({
            "name": name,
            "quota_code": quota_code,
            "family_code": family_code,
        })
    return my_packages
