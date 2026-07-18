import os
import sys

sys.path.insert(0, 'Backend')
from server import load_env_file
from google.oauth2 import service_account
from googleapiclient.discovery import build

def format_debug_sheet():
    load_env_file()
    pk = os.environ.get('GOOGLE_PRIVATE_KEY', '')
    if '\\n' in pk: pk = pk.replace('\\n', '\n')
    if '\\\\n' in pk: pk = pk.replace('\\\\n', '\n')

    info = {
        'type': 'service_account',
        'client_email': os.environ.get('GOOGLE_CLIENT_EMAIL'),
        'private_key': pk,
        'token_uri': 'https://oauth2.googleapis.com/token'
    }
    creds = service_account.Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)
    
    # Read the Debug Sheet ID from environment or fallback to hardcoded
    SPREADSHEET_ID = os.environ.get("DEBUG_GOOGLE_SHEET_ID", "1E6GkE6440JysCb1v-pvkSpTQCSBvvY-g_ubvkkJheMU")
    
    # Get the sheet metadata
    sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets = sheet_metadata.get('sheets', [])
    
    requests = []
    headers = [
        "Timestamp", "Brand Name", "Website URL", "Category or Niche", "About Business",
        "Call prompt To LLM", "LLM Output", 
        "image prompt", "Raw image Output Recieved By Image Model", "Drive Link of that file", "Screenshot (Drive Link)"
    ]
    
    for sheet in sheets:
        sheet_id = sheet.get("properties", {}).get("sheetId", 0)
        sheet_title = sheet.get("properties", {}).get("title", "")
        
        # 0. Insert Headers via update
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_title}!A1:K1",
            valueInputOption="USER_ENTERED",
            body={"values": [headers]}
        ).execute()
        
        # 1. Format the Header Row (Bold, Dark Blue Background, White Text, Center Align)
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 8
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.3},
                        "textFormat": {"bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}},
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
            }
        })
        
        # 2. Freeze the first row
        requests.append({
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1}
                },
                "fields": "gridProperties.frozenRowCount"
            }
        })
        
        # 3. Set specific column widths for massive text blocks (Cols C, D, E, F, G) to be wider (e.g., 400 pixels)
        requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 2, # C
                    "endIndex": 7  # G (up to H)
                },
                "properties": {"pixelSize": 400},
                "fields": "pixelSize"
            }
        })
        
        # 4. Set wrap strategy to WRAP for all cells so JSON doesn't spill over
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "startColumnIndex": 2,
                    "endColumnIndex": 7
                },
                "cell": {
                    "userEnteredFormat": {
                        "wrapStrategy": "WRAP",
                        "verticalAlignment": "TOP"
                    }
                },
                "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"
            }
        })
    
    try:
        body = {'requests': requests}
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
        print("[+] Successfully formatted the Raw Debug Sheet!")
    except Exception as e:
        print(f"[-] Error formatting sheet: {e}")

if __name__ == "__main__":
    format_debug_sheet()
