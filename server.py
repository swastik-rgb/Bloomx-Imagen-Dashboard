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
