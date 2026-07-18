import os
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pipeline import AdGenerationPipeline
from creative_engine import load_env_file

# Load .env file automatically on server startup
load_env_file()

# Set base paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_creatives")

class DashboardRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        # Serve index.html for root path
        if self.path == "/" or self.path == "/index.html":
            self.path = "/index.html"
            return super().do_GET()
            
        # Handle static files in output_creatives
        if self.path.startswith("/output_creatives/"):
            return super().do_GET()
            
        return super().do_GET()

    def do_POST(self):
        if self.path in ("/api/generate", "/api/mock_generate", "/api/analyze", "/api/mock_analyze"):
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode("utf-8"))
                url = payload.get("url")
                if url and isinstance(url, str):
                    url = url.strip()
                    if url and not url.startswith("http://") and not url.startswith("https://"):
                        url = f"https://{url}"

                brand_name = payload.get("brandName") or payload.get("brand_name") or payload.get("brand") or ""
                niche = payload.get("category") or payload.get("niche") or ""
                about = payload.get("about") or payload.get("description") or ""
                client_name = payload.get("name") or payload.get("client_name") or ""
                client_phone = payload.get("phone") or payload.get("client_phone") or payload.get("phone_no") or ""
                req_type = payload.get("type", "creative_ad")
                
                if not url and not (brand_name and niche):
                    self.send_error_response("Please specify either a Brand Website URL (Branch 1) OR both Brand Name & Category/Niche (Branch 2).")
                    return
                
                target_input = {
                    "type": req_type,
                    "url": url,
                    "brand_name": brand_name,
                    "brandName": brand_name,
                    "niche": niche,
                    "category": niche,
                    "about": about,
                    "name": client_name,
                    "phone": client_phone
                }
                target_input = {k: v for k, v in target_input.items() if v is not None and str(v).strip() != ""}
                    
                if "mock" in self.path:
                    import time
                    print(f"[*] /api/mock_generate called for target schema: {target_input}")
                    print(f"[*] Simulating API generation delay (3 seconds)...")
                    
                    real_screenshot_link = "https://drive.google.com/file/d/MOCK_SCREENSHOT/view"
                    if url:
                        print("[*] Mock Mode: Initiating REAL Screenshot Capture...")
                        try:
                            from screenshot_engine import capture_or_load_screenshot
                            import os
                            output_dir = "output_creatives"
                            os.makedirs(output_dir, exist_ok=True)
                            
                            scr_path = os.path.join(output_dir, "mock_landing_page_screenshot.png")
                            if capture_or_load_screenshot(url, scr_path):
                                from drive_uploader import upload_to_gdrive
                                base_filename = f"{client_name}##{client_phone}" if client_name and client_phone else "Mock_Creative"
                                scr_res = upload_to_gdrive(
                                    scr_path, 
                                    filename=f"Screenshot_{base_filename}.png",
                                    folder_id=os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
                                )
                                if scr_res and isinstance(scr_res, dict):
                                    real_screenshot_link = scr_res.get("webViewLink") or f"https://drive.google.com/file/d/{scr_res.get('id')}/view?usp=drive_link"
                        except Exception as e_scr:
                            print(f"[-] MOCK: Failed to capture/upload real screenshot: {e_scr}")
                    else:
                        time.sleep(3)
                    
                    try:
                        from sheet_updater import update_lead_sheet, append_debug_log
                        update_lead_sheet(target_input, creative_link="https://drive.google.com/file/d/MOCK_ID/view", drive_status="Success")
                        
                        append_debug_log({
                            "brand_name": brand_name,
                            "input_json": json.dumps(target_input),
                            "sys_prompt": "MOCK_SYSTEM_PROMPT: You are an expert designer...",
                            "user_prompt": "MOCK_USER_PROMPT: Analyze this brand...",
                            "raw_output": '{"mock_json": "Testing raw output extraction"}',
                            "image_prompt": "MOCKED PROMPT: This is a mocked generated brief to save API credits.",
                            "raw_image_output": '{"created": 172000000, "data": [{"url": "mock_image_url"}]}',
                            "drive_link": "https://drive.google.com/file/d/MOCK_ID/view",
                            "screenshot_link": real_screenshot_link
                        })
                    except Exception as e:
                        print(f"[-] MOCK: Failed to update sheet: {e}")

                    fake_manifest = [{
                        "id": "Mock_Creative_123",
                        "brand": brand_name,
                        "image_file": "BloomX Business Solutions Ad Creative02.png",
                        "prompt_file": "BloomX Business Solutions Ad Creative02.txt"
                    }]
                    self.send_json_response(200, {
                        "success": True,
                        "manifest": fake_manifest,
                        "creative": fake_manifest[0],
                        "image_url": "/output_creatives/BloomX Business Solutions Ad Creative02.png",
                        "prompt_url": "/output_creatives/BloomX Business Solutions Ad Creative02.txt",
                        "prompt_text": "MOCKED PROMPT: This is a mocked generated brief to save API credits."
                    })
                    return

                print(f"[*] /api/generate called for target schema: {target_input} (Single Creative Mode: 1 Prompt, 1 Image)")
                
                # Retrieve API Key from environment or .env file
                load_env_file()
                api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
                if not api_key:
                    self.send_error_response("Error: OPENAI_API_KEY is not set in your .env file or environment.")
                    return

                # Run Ad Generation Pipeline using OpenAI API with limit=1 and generate_image=True
                pipeline = AdGenerationPipeline(provider="openai", api_key=api_key)
                manifest = pipeline.run(
                    url_or_data=target_input, 
                    bulk=False, 
                    output_dir=OUTPUT_DIR, 
                    limit=1, 
                    generate_image=True
                )
                
                if not manifest or len(manifest) == 0:
                    self.send_error_response("Failed to generate ad creative. Please check your inputs and API key.")
                    return
                
                creative = manifest[0]
                creative_id = creative.get("id", "creative")
                
                # Read generated prompt text
                prompt_path = os.path.join(OUTPUT_DIR, creative["prompt_file"])
                prompt_text = ""
                if os.path.exists(prompt_path):
                    with open(prompt_path, "r", encoding="utf-8") as pf:
                        prompt_text = pf.read()
                
                # Prepare clean response
                response_data = {
                    "success": True,
                    "manifest": manifest,
                    "creative": creative,
                    "image_url": f"/output_creatives/{creative.get('image_file') or f'{creative_id}.png'}",
                    "prompt_url": f"/output_creatives/{creative['prompt_file']}",
                    "prompt_text": prompt_text
                }
                
                self.send_json_response(200, response_data)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_error_response(f"Server error during generation: {str(e)}")
        else:
            self.send_error(404, "Endpoint not found")

    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def send_error_response(self, message):
        self.send_json_response(400, {"success": False, "error": message})

def run_server(port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, DashboardRequestHandler)
    print("=" * 60)
    print(f"[+] BloomX ImaGEN Dashboard Server running on port {port}")
    print(f"[+] Open browser to: http://localhost:{port}/")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped by user.")
        httpd.server_close()

if __name__ == "__main__":
    run_server(port=8000)
