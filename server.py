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

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type, Authorization")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

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
                    
                print(f"[*] /api/generate called for target schema: {target_input} (Single Creative Mode: 1 Prompt, 1 Image)")
                
                # Retrieve API Key from environment or .env file
                load_env_file()
                api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
                if not api_key:
                    self.send_error_response("Error: OPENAI_API_KEY is not set in your .env file or environment.")
                    return

                # Send immediate 200 OK success response to frontend
                self.send_json_response(200, {"success": True, "message": "Ad Creative generation started in the background."})
                
                # Define background task
                def background_task(t_input, a_key):
                    try:
                        print("[*] Background task started...")
                        pipeline = AdGenerationPipeline(provider="openai", api_key=a_key)
                        manifest = pipeline.run(
                            url_or_data=t_input, 
                            bulk=False, 
                            output_dir=OUTPUT_DIR, 
                            limit=1, 
                            generate_image=True
                        )
                        print("[*] Background task completed. Manifest:", manifest)
                    except Exception as e:
                        print("Background task error:", e)
                        import traceback
                        traceback.print_exc()
                        
                import threading
                thread = threading.Thread(target=background_task, args=(target_input, api_key))
                thread.daemon = True
                thread.start()
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                if not self.headers_sent if hasattr(self, 'headers_sent') else True:
                    self.send_error_response(f"Server error during generation: {str(e)}")
        else:
            self.send_error(404, "Endpoint not found")

    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
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
