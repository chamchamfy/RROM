import requests
from bs4 import BeautifulSoup
import time
import os

# Thông tin tài khoản
EMAIL = os.getenv("PIXELDRAIN_EMAIL")
PASSWORD = os.getenv("PIXELDRAIN_PASS")

# File lưu key
KEY_FILE = "pixeldrain_key.txt"

def login_and_get_key():
    session = requests.Session()

    # B1: Đăng nhập
    login_url = "https://pixeldrain.com/api/user/login"
    resp = session.post(login_url, json={"username": EMAIL, "password": PASSWORD})
    resp.raise_for_status()

    # B2: Lấy danh sách API keys
    keys_url = "https://pixeldrain.com/api/user/apikeys"
    resp = session.get(keys_url)
    resp.raise_for_status()

    data = resp.json()
    # Giả sử API trả về danh sách key, lấy cái đầu tiên
    if data and "keys" in data:
        new_key = data["keys"][0]["key"]
        return new_key
    else:
        raise Exception("Không tìm thấy API key")

def check_and_refresh_key():
    now = int(time.time())
    if not os.path.exists(KEY_FILE):
        print("Chưa có key, tạo mới...")
        new_key = login_and_get_key()
        with open(KEY_FILE, "w") as f:
            f.write(f"{now}:{new_key}")
        return new_key

    created, apikey = open(KEY_FILE).read().strip().split(":")
    created = int(created)
    days = (now - created) // 86400

    if days > 30:
        print("Key quá hạn, tạo mới...")
        new_key = login_and_get_key()
        with open(KEY_FILE, "w") as f:
            f.write(f"{now}:{new_key}")
        return new_key
    else:
        print("Key còn hạn, dùng lại")
        return apikey

if __name__ == "__main__":
    key = check_and_refresh_key()
    print("API key hiện tại:", key)
