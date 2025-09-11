import os
import json
import time
from api_request import get_new_token, get_otp, submit_otp_code
from util import ensure_api_key

class Auth:
    _instance_ = None
    _initialized_ = False
    
    api_key = ""
    
    refresh_tokens = []
    # Format of refresh_tokens: [{"number": int, "refresh_token": str}]
    
    active_user = None
    # Format of active_user: {"number": int, "tokens": {"refresh_token": str, "access_token": str, "id_token": str}}
    
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
                # Create empty file
                with open("refresh-tokens.json", "w", encoding="utf-8") as f:
                    json.dump([], f, indent=4)

            self._initialized_ = True
    
    def load_tokens(self):
        try:
            with open("refresh-tokens.json", "r", encoding="utf-8") as f:
                self.refresh_tokens = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading tokens: {e}")
            self.refresh_tokens = []

    def save_tokens(self):
        with open("refresh-tokens.json", "w", encoding="utf-8") as f:
            json.dump(self.refresh_tokens, f, indent=4)

    def add_refresh_token(self, number: str, refresh_token: str):
        existing_token = next((t for t in self.refresh_tokens if t["number"] == number), None)
        if existing_token:
            existing_token["refresh_token"] = refresh_token
        else:
            self.refresh_tokens.append({
                "number": number,
                "refresh_token": refresh_token
            })
        self.save_tokens()
        
    def set_active_user(self, number: str):
        if not number:
            self.active_user = None
            return
            
        token_data = next((t for t in self.refresh_tokens if t["number"] == number), None)
        if token_data:
            tokens = get_new_token(token_data["refresh_token"])
            if tokens:
                self.active_user = {
                    "number": number,
                    "tokens": tokens
                }
                self.last_refresh_time = int(time.time())
                return True
        self.active_user = None
        return False
        
    def renew_active_user_token(self):
        if self.active_user:
            tokens = get_new_token(self.active_user["tokens"]["refresh_token"])
            if tokens:
                self.active_user["tokens"] = tokens
                self.last_refresh_time = int(time.time())
                self.add_refresh_token(self.active_user["number"], self.active_user["tokens"]["refresh_token"])
                
                print("Active user token renewed successfully.")
                return True
            else:
                print("Failed to renew active user token.")
        else:
            print("No active user set or missing refresh token.")
        return False
    
    def get_active_user(self):
        if not self.active_user:
            if self.refresh_tokens:
                first_rt = self.refresh_tokens[0]
                if self.set_active_user(first_rt["number"]):
                    return self.active_user
            return None
        
        if self.last_refresh_time is None or (int(time.time()) - self.last_refresh_time) > 300:
            self.renew_active_user_token()
        
        return self.active_user
    
    def get_active_tokens(self):
        active_user = self.get_active_user()
        return active_user["tokens"] if active_user else None
    
# Fungsi bantuan untuk bot Telegram
def get_otp_and_handle_session(user_id: int, phone_number: str) -> bool:
    """Mengirim OTP dan menandai sesi pengguna."""
    try:
        get_otp(phone_number)
        return True
    except Exception as e:
        print(f"Failed to get OTP for {phone_number}: {e}")
        return False
        
def submit_otp_and_login_session(user_id: int, phone_number: str, otp_code: str) -> bool:
    """Mengirimkan OTP, mendapatkan token, dan mengatur pengguna aktif."""
    try:
        tokens = submit_otp_code(phone_number, otp_code)
        if tokens:
            AuthInstance.add_refresh_token(phone_number, tokens["refresh_token"])
            AuthInstance.set_active_user(phone_number)
            return True
        return False
    except Exception as e:
        print(f"Login failed for {phone_number}: {e}")
        return False

# Buat instance
AuthInstance = Auth()
AuthInstance.api_key = ensure_api_key()

