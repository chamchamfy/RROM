import argparse
import requests
import time
import os

def login_and_get_key(email, password):
    session = requests.Session()
    # Đăng nhập
    resp = session.post("https://pixeldrain.com/api/user/login",
                        json={"username": email, "password": password})
    resp.raise_for_status()

    # Lấy danh sách API keys
    resp = session.get("https://pixeldrain.com/api/user/apikeys")
    resp.raise_for_status()
    data = resp.json()
    if data and "keys" in data and len(data["keys"]) > 0:
        return data["keys"][0]["key"]
    raise Exception("Không tìm thấy API key")

def check_and_refresh_key(email, password):
    KEY_FILE = os.path.expanduser("~/.pixeldrain_key")
    now = int(time.time())

    if not os.path.exists(KEY_FILE):
        new_key = login_and_get_key(email, password)
        with open(KEY_FILE, "w") as f:
            f.write(f"{now}:{new_key}")
        return new_key

    created, apikey = open(KEY_FILE).read().strip().split(":")
    created = int(created)
    days = (now - created) // 86400
    if days > 30:
        new_key = login_and_get_key(email, password)
        with open(KEY_FILE, "w") as f:
            f.write(f"{now}:{new_key}")
        return new_key
    return apikey

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pixeldrain API key refresher")
    parser.add_argument("-u", "--user", required=True, help="Pixeldrain email/username")
    parser.add_argument("-p", "--password", required=True, help="Pixeldrain password")
    args = parser.parse_args()

    key = check_and_refresh_key(args.user, args.password)
    print("API key hiện tại:", key)
