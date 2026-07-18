import os
from datetime import datetime

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    HAS_GOOGLE_SHEETS = True
except ImportError:
    HAS_GOOGLE_SHEETS = False

DEFAULT_SPREADSHEET_ID = "1q15EEkyWa8xeURpUgXhpaoritMosRCD7F998z9lBJjU"

def get_sheets_service():
    if not HAS_GOOGLE_SHEETS:
        print("[!] Google Sheets client libraries not available.")
        return None, None

    try:
        from server import load_env_file
        load_env_file()
    except Exception:
        pass

    spreadsheet_id = os.environ.get("GOOGLE_SHEET_ID") or os.environ.get("GOOGLE_SHEETS_ID") or os.environ.get("SPREADSHEET_ID") or DEFAULT_SPREADSHEET_ID

    # Use Service Account for Google Sheets
    client_email = os.environ.get("GOOGLE_CLIENT_EMAIL")
    pk = os.environ.get("GOOGLE_PRIVATE_KEY", "")
    
    # Ultra-robust PEM formatter to handle any environment variable mangling (Nixpacks/Docker)
    import re
    clean_pk = re.sub(r"-----BEGIN PRIVATE KEY-----", "", pk)
    clean_pk = re.sub(r"-----END PRIVATE KEY-----", "", clean_pk)
    clean_pk = re.sub(r"\\n", "", clean_pk)
    clean_pk = re.sub(r"[\"']", "", clean_pk) # Strip outer/stray quotes
    clean_pk = re.sub(r"\s+", "", clean_pk) # Strip all spaces and newlines
    
    if clean_pk:
        # Fix padding if Coolify or env parsers stripped trailing equals signs
        padding_needed = len(clean_pk) % 4
        if padding_needed > 0:
            clean_pk += "=" * (4 - padding_needed)
            
        chunks = [clean_pk[i:i+64] for i in range(0, len(clean_pk), 64)]
        pk = "-----BEGIN PRIVATE KEY-----\n" + "\n".join(chunks) + "\n-----END PRIVATE KEY-----\n"
    if "\\\\n" in pk: pk = pk.replace("\\\\n", "\n")

    if client_email and pk and "-----BEGIN" in pk:
        try:
            print("[*] Authenticating with Google Sheets via Service Account from .env...")
            info = {
                "type": "service_account",
                "client_email": client_email,
                "private_key": pk,
                "token_uri": "https://oauth2.googleapis.com/token"
            }
            try:
                creds = service_account.Credentials.from_service_account_info(
                    info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
                )
            except Exception as e:
                print(f"[-] Service account sheets auth error: {e}")
                print("[*] Falling back to OAuth2 for Google Sheets...")
                from google.oauth2.credentials import Credentials
                creds = Credentials(
                    token=None,
                    refresh_token=os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN"),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID"),
                    client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
                )
            
            service = build("sheets", "v4", credentials=creds)
            return service, spreadsheet_id
        except Exception as e_sa:
            print(f"[-] Service account sheets auth error: {e_sa}")

    return None, spreadsheet_id

def update_lead_sheet(data_dict, creative_link="", drive_status="", target_row_idx=None):
    """
    If target_row_idx is provided, updates that exact row.
    Otherwise, appends a brand new row and returns the new row index.
    """
    name = str(data_dict.get("name") or data_dict.get("Name") or data_dict.get("client_name") or "")
    email = str(data_dict.get("email") or data_dict.get("Email") or "")
    phone = str(data_dict.get("phone") or data_dict.get("Phone Number") or data_dict.get("Phone") or data_dict.get("client_phone") or data_dict.get("phone_no") or "")
    url = str(data_dict.get("url") or data_dict.get("Website URL") or "")
    brand_name = str(data_dict.get("brandName") or data_dict.get("brand_name") or data_dict.get("Brand Name") or "")
    category = str(data_dict.get("category") or data_dict.get("niche") or data_dict.get("Category or Niche") or "")
    about = str(data_dict.get("about") or data_dict.get("aboutBusiness") or data_dict.get("About Business") or "")

    try:
        service, spreadsheet_id = get_sheets_service()
        if not service or not spreadsheet_id: return None

        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range="A1:M1"
        ).execute()
        rows = result.get("values", [])
        if not rows: return None

        headers = [str(h).strip().lower() for h in rows[0]]

        def get_idx(col_name):
            try: return headers.index(col_name.lower())
            except ValueError: return -1

        def map_field(r, col_name, value):
            idx = get_idx(col_name)
            if idx != -1 and value is not None:
                is_status_or_link = "link" in col_name or "status" in col_name
                # Only overwrite if blank OR if it's a status/link field that needs updating
                if not r[idx] or is_status_or_link:
                    r[idx] = value
                    
        status_val = "Success" if drive_status == "Success" else "Processing"

        if target_row_idx:
            print(f"[*] Updating existing lead at Row {target_row_idx}. Updating fields...")
            update_res = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=f"A{target_row_idx}:M{target_row_idx}"
            ).execute()
            existing_rows = update_res.get("values", [])
            existing_row = existing_rows[0] if existing_rows else [""] * len(headers)
            
            while len(existing_row) < len(headers):
                existing_row.append("")
                
            map_field(existing_row, "name", name)
            map_field(existing_row, "email", email)
            map_field(existing_row, "phone number", phone)
            map_field(existing_row, "website url", url)
            map_field(existing_row, "brand name", brand_name)
            map_field(existing_row, "category or niche", category)
            map_field(existing_row, "about business", about)
            map_field(existing_row, "creative link", creative_link)
            map_field(existing_row, "drive status", drive_status)
            map_field(existing_row, "status", status_val)

            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"A{target_row_idx}:M{target_row_idx}",
                valueInputOption="USER_ENTERED",
                body={"values": [existing_row]}
            ).execute()
            print(f"[+] Google Sheet successfully updated at Row {target_row_idx} (Creative Link: '{creative_link}', Drive Status: '{drive_status}')")
            return target_row_idx
        else:
            print("[*] Appending new row to Google Sheet...")
            new_row = [""] * len(headers)
            map_field(new_row, "timestamp", datetime.now().strftime("%d/%m/%Y, %I:%M:%S %p"))
            map_field(new_row, "lead type", "Ad Creative")
            map_field(new_row, "name", name)
            map_field(new_row, "email", email)
            map_field(new_row, "phone number", phone)
            map_field(new_row, "website url", url)
            map_field(new_row, "brand name", brand_name)
            map_field(new_row, "category or niche", category)
            map_field(new_row, "about business", about)
            map_field(new_row, "creative link", creative_link)
            map_field(new_row, "drive status", drive_status)
            map_field(new_row, "status", status_val)
            
            append_res = service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range="A1:M1",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": [new_row]}
            ).execute()
            
            updated_range = append_res.get("updates", {}).get("updatedRange", "")
            if updated_range:
                import re
                match = re.search(r"[A-Z]+(\d+)", updated_range.split("!")[-1] if "!" in updated_range else updated_range)
                if match:
                    return int(match.group(1))
            return None

    except Exception as e:
        print(f"[-] Failed to update Google Sheet: {e}")
        return None


def append_debug_log(debug_data):
    """
    Appends raw LLM inputs, prompts, outputs, and image prompts to the 'Raw Debug Logs' tab.
    """
    if not isinstance(debug_data, dict):
        return False
        
    service, spreadsheet_id = get_sheets_service()
    if not service or not spreadsheet_id:
        print("[!] Could not initialize Google Sheets service for debug logging.")
        return False

    brand_name = str(debug_data.get("brand_name") or "")
    input_json_str = str(debug_data.get("input_json") or "{}")
    import json
    try:
        parsed_json = json.loads(input_json_str)
    except Exception:
        parsed_json = {}
        
    frontend_url = str(parsed_json.get("url") or "")
    frontend_niche = str(parsed_json.get("niche") or parsed_json.get("category") or "")
    frontend_about = str(parsed_json.get("about") or "")

    sys_prompt = str(debug_data.get("sys_prompt") or "")
    user_prompt = str(debug_data.get("user_prompt") or "")
    call_prompt_to_llm = f"--- SYSTEM PROMPT ---\n{sys_prompt}\n\n--- USER PROMPT ---\n{user_prompt}"

    raw_output = str(debug_data.get("raw_output") or "")
    image_prompt = str(debug_data.get("image_prompt") or "")
    raw_image_output = str(debug_data.get("raw_image_output") or "")
    drive_link = str(debug_data.get("drive_link") or "")
    screenshot_link = str(debug_data.get("screenshot_link") or "")

    print(f"[*] Appending Raw Debug Logs for Brand '{brand_name}'...")

    new_row = [
        datetime.now().strftime("%d/%m/%Y, %I:%M:%S %p"), # Col A: Timestamp
        brand_name,                                       # Col B: Brand Name
        frontend_url,                                     # Col C: Website URL
        frontend_niche,                                   # Col D: Category or Niche
        frontend_about,                                   # Col E: About Business
        call_prompt_to_llm,                               # Col F: Call prompt To LLM
        raw_output,                                       # Col G: LLM Output
        image_prompt,                                     # Col H: image prompt
        raw_image_output,                                 # Col I: Raw image Output Recieved By Image Model
        drive_link,                                       # Col J: Drive Link of that file
        screenshot_link                                   # Col K: Screenshot Link
    ]

    # NEW Dedicated Debug Spreadsheet ID from .env
    debug_spreadsheet_id = os.environ.get("DEBUG_GOOGLE_SHEET_ID", "1E6GkE6440JysCb1v-pvkSpTQCSBvvY-g_ubvkkJheMU")

    try:
        append_res = service.spreadsheets().values().append(
            spreadsheetId=debug_spreadsheet_id,
            range="A1:K1",
            valueInputOption="USER_ENTERED",
            body={"values": [new_row]}
        ).execute()
        print(f"[+] Raw Debug Logs successfully appended for '{brand_name}' to dedicated debug sheet!")
        return True
    except Exception as e:
        print(f"[-] Error appending to dedicated debug sheet: {e}")
        return False

if __name__ == "__main__":
    print("Testing sheet_updater...")
    test_lead = {
        "name": "mitali",
        "phone": "7987026230",
        "brandName": "Vedic Vastu Living",
        "category": "Vedic Vastu Consulting",
        "about": "Ancient Vastu principles for modern homes and offices."
    }
    # Test update on existing lead mitali (7987026230)
    update_lead_sheet(test_lead, creative_link="https://drive.google.com/file/d/test_id_here/view?usp=drive_link", drive_status="Success")
