import os
import json
import time
from api_request import get_new_token, BASE_CIAM_URL, BASIC_AUTH

# Asumsi util.py berisi fungsi ini
def ensure_api_key(api_key):
    return api_key

class Auth:
    _instance_ = None
    _initialized_ = False
    
    api_key = ""
    
    refresh_tokens = []
    
    active_user = None
    
    last_refresh_time = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance_:
            cls._instance_ = super().__new__(cls)
        return cls._instance_
    
    def __init__(self):
        if not self._initialized_:
            if os.path.exists("refresh-tokens.json"):
                self.load_tokens()
            else:
                with open("refresh-tokens.json", "w", encoding="utf-8") as f:
                    json.dump([], f, indent=4)
            self._initialized_ = True
            
    def load_tokens(self):
        with open("refresh-tokens.json", "r", encoding="utf-8") as f:
            self.refresh_tokens = json.load(f)

    def save_tokens(self):
        with open("refresh-tokens.json", "w", encoding="utf-8") as f:
            json.dump(self.refresh_tokens, f, indent=4)

    def add_refresh_token(self, number: str, refresh_token: str):
        self.refresh_tokens = [rt for rt in self.refresh_tokens if rt["number"] != number]
        self.refresh_tokens.append({"number": number, "refresh_token": refresh_token})
        self.save_tokens()
    
    def set_active_user(self, number: str):
        rt = next((t for t in self.refresh_tokens if t["number"] == number), None)
        if rt:
            tokens = get_new_token(rt["refresh_token"])
            if tokens:
                self.active_user = {
                    "number": rt["number"],
                    "tokens": tokens
                }
                self.last_refresh_time = int(time.time())
                return True
        return False
    
    def renew_active_user_token(self):
        if self.active_user and self.active_user["tokens"]["refresh_token"]:
            tokens = get_new_token(self.active_user["tokens"]["refresh_token"])
            if tokens:
                self.active_user["tokens"] = tokens
                self.last_refresh_time = int(time.time())
                return True
        return False
    
    def get_active_user(self):
        if not self.active_user:
            return None
        
        if self.last_refresh_time is None or (int(time.time()) - self.last_refresh_time) > 300:
            self.renew_active_user_token()
        
        return self.active_user
    
    def get_active_tokens(self):
        active_user = self.get_active_user()
        return active_user["tokens"] if active_user else None
    
AuthInstance = Auth()
