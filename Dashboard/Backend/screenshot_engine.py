import os
import base64
import requests
import subprocess
import urllib.parse

def capture_or_load_screenshot(url_or_path, output_path="output_creatives/latest_screenshot.png"):
    """
    Captures a screenshot of the target web URL OR loads an existing image file,
    returns the Base64-encoded PNG string suitable for OpenAI Vision API.
    Also saves the screenshot to output_path for human inspection.
    """
    # 1. Check if input is a local file path
    if os.path.exists(url_or_path) and os.path.isfile(url_or_path):
        print(f"[*] Loading existing screenshot file: {url_or_path}")
        try:
            with open(url_or_path, "rb") as f:
                img_bytes = f.read()
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            if os.path.abspath(url_or_path) != os.path.abspath(output_path):
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
            return base64.b64encode(img_bytes).decode('utf-8')
        except Exception as e:
            print(f"[!] Error reading local screenshot file '{url_or_path}': {e}")
            return None

    # 2. If it's a URL, attempt live screenshot capture
    if not (url_or_path.startswith("http://") or url_or_path.startswith("https://")):
        url_or_path = "https://" + url_or_path

    print(f"[*] Capturing live visual screenshot of landing page: {url_or_path} ...")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Method 1: Attempt local Headless Chrome or Microsoft Edge capture (Fastest, 100% reliable, zero API limits)
    abs_output_path = os.path.abspath(output_path)
    browser_binaries = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    for binary_path in browser_binaries:
        if os.path.exists(binary_path):
            try:
                cmd = [
                    binary_path,
                    "--headless=new",
                    f"--screenshot={abs_output_path}",
                    "--window-size=1440,4500",
                    "--virtual-time-budget=4000",
                    "--hide-scrollbars",
                    url_or_path
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
                if os.path.exists(abs_output_path) and os.path.getsize(abs_output_path) > 1000:
                    print(f"[+] Full-Page Screenshot captured via local Headless Browser ({os.path.basename(binary_path)}) and saved to: {output_path} (Size: {os.path.getsize(abs_output_path):,} bytes)")
                    with open(abs_output_path, "rb") as f:
                        img_bytes = f.read()
                    return base64.b64encode(img_bytes).decode('utf-8')
            except Exception as e_browser:
                print(f"[-] Local browser ({os.path.basename(binary_path)}) capture warning: {e_browser}")

    # Method 2: Attempt Microlink API endpoint (Fallback if local browser not available)
    try:
        encoded_url = urllib.parse.quote(url_or_path, safe='')
        api_url = f"https://api.microlink.io/?url={encoded_url}&screenshot=true&fullPage=true&meta=false&viewport.width=1440"
        response = requests.get(api_url, timeout=20)
        if response.status_code == 200:
            data = response.json()
            screenshot_url = data.get("data", {}).get("screenshot", {}).get("url")
            if screenshot_url:
                img_res = requests.get(screenshot_url, timeout=15)
                if img_res.status_code == 200 and len(img_res.content) > 1000:
                    with open(output_path, "wb") as f:
                        f.write(img_res.content)
                    print(f"[+] Screenshot captured via Microlink API and saved to: {output_path}")
                    return base64.b64encode(img_res.content).decode('utf-8')
    except Exception as e:
        print(f"[-] Microlink API fallback error: {e}")

    # Method 3: Attempt Google Pagespeed Insights API fallback
    try:
        pagespeed_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={urllib.parse.quote(url_or_path)}&category=BEST_PRACTICES&strategy=DESKTOP"
        res = requests.get(pagespeed_url, timeout=25)
        if res.status_code == 200:
            data = res.json()
            screenshot_data = data.get("lighthouseResult", {}).get("audits", {}).get("final-screenshot", {}).get("details", {}).get("data", "")
            if screenshot_data and "base64," in screenshot_data:
                b64_str = screenshot_data.split("base64,")[1]
                img_bytes = base64.b64decode(b64_str)
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                print(f"[+] Screenshot captured via Pagespeed API and saved to: {output_path}")
                return b64_str
    except Exception as e:
        print(f"[-] Pagespeed API fallback error: {e}")

    print("[!] Could not capture live web screenshot automatically. Proceeding with DOM/text analysis only.")
    return None

if __name__ == "__main__":
    test_url = "https://bloomxsolutions.com/"
    b64 = capture_or_load_screenshot(test_url, "output_creatives/test_screenshot.png")
    if b64:
        print(f"[+] Successfully captured screenshot! Base64 length: {len(b64)}")
    else:
        print("[-] Screenshot capture returned None.")
