import os
import json
import base64
import requests

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    HAS_GOOGLE_CLIENT = True
except ImportError:
    HAS_GOOGLE_CLIENT = False

def upload_to_gdrive(file_path, filename=None, folder_id=None):
    """
    Uploads a generated image file to Google Drive with the exact filename (e.g. Name##PhoneNo.png).
    Checks for Service Account credentials or OAuth token.json or Google Drive Webhook.
    """
    try:
        from server import load_env_file
        load_env_file()
    except Exception:
        pass

    if not os.path.exists(file_path):
        print(f"[!] Error: Image file to upload does not exist: {file_path}")
        return None

    if not filename:
        filename = os.path.basename(file_path)

    # 1. Check for folder ID in arguments or environment
    folder_id = folder_id or os.environ.get("GDRIVE_FOLDER_ID") or os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
    if folder_id and folder_id == "your_google_drive_folder_id_here":
        folder_id = None

    # 2. Check for optional Apps Script / Make / Zapier Webhook fallback
    webhook_url = os.environ.get("GDRIVE_WEBHOOK_URL")
    if webhook_url and webhook_url.startswith("http"):
        print(f"[*] Uploading '{filename}' to Google Drive via configured Webhook URL...")
        try:
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, "image/png")}
                data = {"filename": filename, "folder_id": folder_id or ""}
                res = requests.post(webhook_url, files=files, data=data, timeout=30)
            if res.status_code in (200, 201):
                print(f"[+] Successfully uploaded '{filename}' to Google Drive via Webhook!")
                return res.json() if res.headers.get("content-type", "").startswith("application/json") else {"status": "success"}
            else:
                print(f"[-] Webhook upload error ({res.status_code}): {res.text}")
        except Exception as e_web:
            print(f"[-] Webhook upload failed: {e_web}")

    # 3. Check for official Google API client
    if not HAS_GOOGLE_CLIENT:
        print("[!] Google Drive API client not installed. Run: pip install google-api-python-client google-auth")
        return None

    creds = None
    try:
        from google.auth.transport.requests import Request
        
        # Check direct OAuth 2 variables in .env first
        oauth_refresh = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN")
        oauth_client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
        oauth_client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
        
        if oauth_refresh and oauth_client_id and oauth_client_secret:
            print("[*] Authenticating with Google Drive via OAuth 2 Refresh Token from .env...")
            creds = Credentials(
                token=None,
                refresh_token=oauth_refresh,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=oauth_client_id,
                client_secret=oauth_client_secret,
                scopes=None
            )
            if not creds.valid:
                creds.refresh(Request())
        
        # Or check Service Account variables in .env
        elif os.environ.get("GOOGLE_CLIENT_EMAIL") and os.environ.get("GOOGLE_PRIVATE_KEY"):
            print("[*] Authenticating with Google Drive via Service Account from .env...")
            info = {
                "type": "service_account",
                "client_email": os.environ.get("GOOGLE_CLIENT_EMAIL"),
                "private_key": os.environ.get("GOOGLE_PRIVATE_KEY").replace("\\n", "\n"),
                "token_uri": "https://oauth2.googleapis.com/token"
            }
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/drive"]
            )
        else:
            # Locate credentials file
            cred_paths = [
                os.environ.get("GDRIVE_CREDENTIALS_PATH"),
                os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
                os.path.join(os.path.dirname(__file__), "..", "gdrive_credentials.json"),
                os.path.join(os.path.dirname(__file__), "..", "service_account.json"),
                os.path.join(os.path.dirname(__file__), "..", "token.json"),
                "gdrive_credentials.json",
                "service_account.json",
                "token.json"
            ]
            
            cred_file = None
            for p in cred_paths:
                if p and os.path.exists(p) and os.path.isfile(p):
                    cred_file = p
                    break

            if not cred_file:
                print(f"[!] Google Drive upload skipped for '{filename}': Credentials (`token.json` or `.env` OAuth variables) not found.")
                return None

            print(f"[*] Authenticating with Google Drive using file: {cred_file}")
            with open(cred_file, "r", encoding="utf-8") as jf:
                c_data = json.load(jf)
                
            if "type" in c_data and c_data["type"] == "service_account":
                creds = service_account.Credentials.from_service_account_file(
                    cred_file, scopes=["https://www.googleapis.com/auth/drive"]
                )
            elif "refresh_token" in c_data or "client_id" in c_data:
                creds = Credentials.from_authorized_user_file(
                    cred_file, scopes=["https://www.googleapis.com/auth/drive"]
                )
            else:
                print(f"[!] Unrecognized format in credentials file: {cred_file}")
                return None

        service = build("drive", "v3", credentials=creds)

        file_metadata = {"name": filename}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        media = MediaFileUpload(file_path, mimetype="image/png", resumable=True)
        print(f"[*] Uploading '{filename}' to Google Drive...")
        
        file_result = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink, webContentLink"
        ).execute()

        file_id = file_result.get("id")
        web_link = file_result.get("webViewLink")
        print(f"[+] Successfully uploaded '{filename}' to Google Drive!")
        print(f"    -> Drive File ID: {file_id}")
        if web_link:
            print(f"    -> Drive Link: {web_link}")

        # Make file accessible or inherit folder permissions
        return file_result

    except Exception as e:
        print(f"[!] Error uploading '{filename}' to Google Drive via API: {str(e)}")
        return None

if __name__ == "__main__":
    print("Testing Drive Uploader module...")
    upload_to_gdrive("output_creatives/landing_page_screenshot.png", "Test_Screenshot.png")
