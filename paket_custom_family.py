#import json
from api_request import send_api_request, get_family
from auth_helper import AuthInstance

def get_packages_by_family(family_code: str):
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        return None
    packages = []
    data = get_family(api_key, tokens, family_code)
    if not data:
        return None
    package_variants = data["package_variants"]
    for variant in package_variants:
        for option in variant["package_options"]:
            packages.append({
                "name": option["name"],
                "price": option["price"],
                "code": option["package_option_code"]
            })
    return packages
