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

    spreadsheet_id = os.environ.get("GOOGLE_SHEET_ID") or os.environ.get("SPREADSHEET_ID") or DEFAULT_SPREADSHEET_ID

    # Check Service Account credentials from .env first (verified and working reliably)
    client_email = os.environ.get("GOOGLE_CLIENT_EMAIL")
    pk = os.environ.get("GOOGLE_PRIVATE_KEY", "")
    if "\\n" in pk: pk = pk.replace("\\n", "\n")
    if "\\\\n" in pk: pk = pk.replace("\\\\n", "\n")

    if client_email and pk and "-----BEGIN" in pk:
        try:
            info = {
                "type": "service_account",
                "client_email": client_email,
                "private_key": pk,
                "token_uri": "https://oauth2.googleapis.com/token"
            }
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            service = build("sheets", "v4", credentials=creds)
            return service, spreadsheet_id
        except Exception as e_sa:
            print(f"[-] Service account sheets auth error: {e_sa}")

    return None, spreadsheet_id

def update_lead_sheet(lead_data, creative_link="", drive_status="Failure"):
    """
    Updates Google Sheet '1q15EEkyWa8xeURpUgXhpaoritMosRCD7F998z9lBJjU' based on frontend JSON.
    Finds existing lead by phone/name or appends a new row if not found.
    Updates Creative Link column and Drive Status (Success/Failure).
    """
    if not isinstance(lead_data, dict):
        return False

    service, spreadsheet_id = get_sheets_service()
    if not service or not spreadsheet_id:
        print("[!] Could not initialize Google Sheets service. Skipping sheet update.")
        return False

    name = str(lead_data.get("name") or lead_data.get("client_name") or "").strip()
    phone = str(lead_data.get("phone") or lead_data.get("client_phone") or lead_data.get("phone_no") or "").strip()
    url = str(lead_data.get("url") or "").strip()
    if url == "None" or url == "null": url = ""
    brand_name = str(lead_data.get("brandName") or lead_data.get("brand_name") or "").strip()
    category = str(lead_data.get("category") or lead_data.get("niche") or "").strip()
    about = str(lead_data.get("about") or "").strip()

    print(f"[*] Checking Google Sheet ({spreadsheet_id}) for lead: Name='{name}', Phone='{phone}'...")

    try:
        # Fetch existing rows
        res = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range="A1:M1000").execute()
        rows = res.get("values", [])

        target_row_idx = None
        for idx, row in enumerate(rows):
            if idx == 0: continue  # Skip header row
            row_name = str(row[2]).strip() if len(row) > 2 else ""
            row_phone = str(row[3]).strip() if len(row) > 3 else ""
            
            # Match strictly by exact phone number if available, or combined name+phone
            if phone and row_phone == phone:
                target_row_idx = idx + 1  # 1-indexed for Google Sheets API
                break
            elif name and phone and row_name.lower() == name.lower() and row_phone == phone:
                target_row_idx = idx + 1
                break

        if target_row_idx:
            print(f"[*] Found existing lead at Row {target_row_idx}. Updating fields...")
            existing_row = rows[target_row_idx - 1]
            # Pad row to 13 columns if needed
            while len(existing_row) < 13:
                existing_row.append("")

            if name and not existing_row[2]: existing_row[2] = name
            if phone and not existing_row[3]: existing_row[3] = phone
            if url and not existing_row[4]: existing_row[4] = url
            if brand_name: existing_row[6] = brand_name
            if category: existing_row[7] = category
            if about: existing_row[8] = about
            existing_row[10] = creative_link
            existing_row[11] = drive_status
            existing_row[12] = "Completed" if drive_status == "Success" else existing_row[12]

            update_res = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"A{target_row_idx}:M{target_row_idx}",
                valueInputOption="USER_ENTERED",
                body={"values": [existing_row[:13]]}
            ).execute()
            print(f"[+] Google Sheet successfully updated at Row {target_row_idx} (Creative Link: '{creative_link}', Drive Status: '{drive_status}')")
            return True
        else:
            print("[*] No existing lead row matched. Appending new row to Google Sheet...")
            new_row = [
                datetime.now().strftime("%d/%m/%Y, %I:%M:%S %p"), # Col A: Timestamp
                "Ad Creative",                                    # Col B: Lead Type
                name,                                             # Col C: Name
                phone,                                            # Col D: Phone Number
                url,                                              # Col E: Website URL
                "",                                               # Col F: Instagram URL
                brand_name,                                       # Col G: Brand Name
                category,                                         # Col H: Category or Niche
                about,                                            # Col I: About Business
                "",                                               # Col J: PDF Report Link
                creative_link,                                    # Col K: Creative Link
                drive_status,                                     # Col L: Drive Status
                "Completed" if drive_status == "Success" else ""  # Col M: Status
            ]
            append_res = service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range="A1:M1",
                valueInputOption="USER_ENTERED",
                body={"values": [new_row[:13]]}
            ).execute()
            print(f"[+] New lead successfully appended to Google Sheet! (Creative Link: '{creative_link}', Drive Status: '{drive_status}')")
            return True

    except Exception as e:
        print(f"[-] Error updating Google Sheet: {e}")
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
