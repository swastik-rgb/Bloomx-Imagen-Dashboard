import re
import urllib.parse
from bs4 import BeautifulSoup
import requests

def scrape_and_optimize(url):
    """
    Scrapes the target URL, extracts absolute image URLs, and optimizes the HTML
    content by removing scripts, styling, base64 images, and unnecessary attributes
    to dramatically reduce token usage for LLM input.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=15)
        
        # Fallback if first request is forbidden (some CDNs require a simpler GET request first)
        if response.status_code == 403:
            simple_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = session.get(url, headers=simple_headers, timeout=15)
            
        response.raise_for_status()
        html = response.text
    except Exception as e:
        return {"error": f"Failed to retrieve website: {str(e)}", "images": [], "optimized_html": ""}

    soup = BeautifulSoup(html, "html.parser")
    base_url = response.url

    # 1. Extract and Classify Images before stripping elements
    logos = []
    products = []
    icons = []
    
    # Check open graph image
    og_img = soup.find("meta", property="og:image")
    if og_img and og_img.get("content"):
        products.append(urllib.parse.urljoin(base_url, og_img["content"]))

    # Find standard images in body
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if src:
            if src.startswith("data:image/"):
                continue
            
            absolute_url = urllib.parse.urljoin(base_url, src)
            src_lower = absolute_url.lower()
            alt = (img.get("alt") or "").lower()
            
            # Classification rules:
            # A. Brand Logo Checks
            if "logo" in src_lower or "logo" in alt or "brand" in src_lower:
                if absolute_url not in logos:
                    logos.append(absolute_url)
            # B. Small UI Icons / Social Indicators / Badges
            elif any(term in src_lower for term in ["icon", "arrow", "badge", "cart", "button", "loader", "close", "scan", "search", "star", "menu", "social", "facebook", "instagram", "twitter", "youtube", "play", "plus", "minus", "avatar", "check"]) or absolute_url.endswith(".svg"):
                if absolute_url not in icons:
                    icons.append(absolute_url)
            # C. Real Product / Showroom Content Images
            else:
                if any(ext in src_lower for ext in [".jpg", ".png", ".webp", ".jpeg"]):
                    if absolute_url not in products:
                        products.append(absolute_url)

    # 2. Token Optimization: Remove unnecessary tags
    for tag in soup(["script", "style", "iframe", "noscript", "svg"]):
        tag.decompose()

    # 3. Clean attributes to save token space
    allowed_attributes = ["src", "alt", "href"]
    for tag in soup.find_all(True):
        if tag.name == "img" and tag.get("src") and tag["src"].startswith("data:image/"):
            tag["src"] = "[base64-image-placeholder]"
        
        attrs = dict(tag.attrs)
        tag.attrs = {k: v for k, v in attrs.items() if k in allowed_attributes}

    # 4. Remove comments and collapse whitespaces
    optimized_text = soup.prettify()
    optimized_text = re.sub(r'<!--.*?-->', '', optimized_text, flags=re.DOTALL)
    optimized_text = "\n".join([line.strip() for line in optimized_text.splitlines() if line.strip()])

    return {
        "title": soup.title.string.strip() if (soup.title and soup.title.string) else "",
        "logos": logos[:5],
        "products": products[:15],
        "icons": icons[:10],
        "optimized_html": optimized_text[:12000]
    }

if __name__ == "__main__":
    test_url = "https://krishnafurniture.com/"
    print(f"Testing Scraper on: {test_url}")
    result = scrape_and_optimize(test_url)
    print(f"Title: {result.get('title')}")
    print(f"Found {len(result.get('images', []))} images.")
    print("Preview of optimized HTML:")
    print(result.get("optimized_html", "")[:500])
