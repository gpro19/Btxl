import os

def ensure_api_key():
    api_key = os.getenv("API_KEY")
    if not api_key:
        print("API_KEY environment variable not set.")
        return None
    return api_key

