import os
import json
from openai import OpenAI

def load_env_file(dotenv_path=None):
    """Zero-dependency helper to load environment variables from a local .env file."""
    if not dotenv_path:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        dotenv_path = os.path.join(base_dir, ".env")
    if not os.path.exists(dotenv_path):
        dotenv_path = ".env"
    if os.path.exists(dotenv_path):
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip("'").strip('"')

class CreativeEngine:
    def __init__(self, provider="openai", api_key=None):
        """
        OpenAI LLM interface supporting GPT models (`gpt-4o`, `gpt-image-2`).
        """
        load_env_file()
        self.provider = provider.lower()
        if self.provider != "openai":
            print(f"[*] Note: Provider '{provider}' ignored; exclusively using 'openai' as requested.")
            self.provider = "openai"
            
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY or LLM_API_KEY must be set in your .env file or environment.")

        self.client = OpenAI(api_key=self.api_key)
        self.model_name = "gpt-4o"

    def call_llm(self, system_prompt, user_prompt, use_search=True, screenshot_b64=None):
        """Calls OpenAI Chat Completion API with retry logic and optional multimodal screenshot vision check."""
        import time
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        self.last_raw_response = None
        max_retries = 3
        
        if screenshot_b64:
            print(f"[*] Attaching visual screenshot (`image_url`) to LLM prompt for multimodal cross-check...")
            user_msg_content = [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
            ]
        else:
            user_msg_content = user_prompt

        for attempt in range(max_retries):
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg_content}
                ]
                if use_search:
                    try:
                        # Try with OpenAI web_search tool enabled
                        response = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=messages,
                            tools=[{"type": "web_search"}]
                        )
                        self.last_raw_response = response.choices[0].message.content
                        return self.last_raw_response
                    except Exception:
                        # Fallback if model/key tier doesn't support tools flag
                        pass
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    response_format={"type": "json_object"},
                    messages=messages
                )
                self.last_raw_response = response.choices[0].message.content
                return self.last_raw_response
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                print(f"    [!] OpenAI LLM Call failed (Attempt {attempt+1}/{max_retries}): {str(e)[:120]}. Retrying in {backoff_delay}s...")
                time.sleep(backoff_delay)
                backoff_delay *= 2

    def generate_image(self, prompt, output_path):
        """Generates an ad creative image via OpenAI GPT Image 2 model."""
        self.last_image_raw_response = None
        print(f"[*] Generating visual creative via OPENAI API...")
        try:
            response = self.client.images.generate(
                model="gpt-image-2",
                prompt=prompt,
                n=1,
                size="1024x1024",
                quality="low"
            )
            
            # Store the exact raw JSON output from the image model
            if hasattr(response, "model_dump_json"):
                self.last_image_raw_response = response.model_dump_json()
            else:
                self.last_image_raw_response = str(response)
                
            b64_data = response.data[0].b64_json
            if b64_data:
                import base64
                img_data = base64.b64decode(b64_data)
                with open(output_path, "wb") as f:
                    f.write(img_data)
            else:
                image_url = response.data[0].url
                if not image_url:
                    raise ValueError("No image URL or Base64 data returned from OpenAI API.")
                import requests
                img_data = requests.get(image_url).content
                with open(output_path, "wb") as f:
                    f.write(img_data)
                    
            print(f"[+] Image successfully saved to: {output_path}")
            return True
        except Exception as e:
            print(f"[!] Error generating image via OpenAI API: {str(e)}")
            return False

    def generate_ad_creatives(self, target_url_or_data, angles_list, layouts_list, use_search=True, num_creatives=None, screenshot_b64=None):
        """
        Brainstorms ad copy, brand assets, and visual layout concepts using AI Web Search capabilities and optional multimodal screenshot cross-check on the target URL.
        Supports both Branch 1 (URL Scraping + Vision) and Branch 2 (Brand + Niche Competitor Analysis / Graphic Designer Mode).
        """
        has_url = isinstance(target_url_or_data, str) or (isinstance(target_url_or_data, dict) and bool(target_url_or_data.get("url")))
        is_branch_2 = isinstance(target_url_or_data, dict) and not bool(target_url_or_data.get("url")) and ("niche" in target_url_or_data or "category" in target_url_or_data)
        target_url = target_url_or_data if isinstance(target_url_or_data, str) else target_url_or_data.get("url", target_url_or_data.get("brandName", target_url_or_data.get("brand_name", "Brand Website")))
        if isinstance(target_url, str) and target_url and not target_url.startswith("http://") and not target_url.startswith("https://") and "." in target_url:
            target_url = f"https://{target_url}"
        if num_creatives is None:
            num_creatives = len(angles_list)
        
        system_prompt = """
You are an expert commercial advertising designer, AI data extraction specialist, and brand strategist.
Your task is to analyze the target website URL (`{URL}`) OR the provided Brand & Niche using your web search, DOM scraping, AND optional visual screenshot cross-checking to perform a deep-dive extraction of the brand identity, messaging, and visual design. 

Your ultimate goal is to design ad creatives optimized for "Cognitive Fluency"—ensuring the ad looks, sounds, and feels exactly like the brand identity or niche expectations so the user experiences zero friction when clicking through.

INSTRUCTIONS:

1. DOM & FULL-PAGE SCREENSHOT EXTRACTION (PRIORITIZE IMAGE DATA ANALYSIS):
   - You are provided with both DOM/text scraping data AND the attached full-page visual screenshot (`screenshot_b64`).
   - COMPARE BOTH & PRIORITIZE IMAGE DATA: Carefully cross-check the DOM/text data against the actual visual screenshot. The full-page screenshot is your authoritative 100% ground-truth. If there is any discrepancy or conflict between the DOM/text copy and what is physically rendered on the image (e.g., `#HEX` button colors, header layout, font aesthetic, or review badges), THE IMAGE DATA TAKES STRICT PRIORITY AND OVERRIDES DOM TEXT!
   - Visual Color Palette: Define `primary`, `secondary`, `accent_cta`, and `background` strictly in `#HEX` format by directly sampling visible elements on the screenshot.
   - Analyze Website Typography Feel: Observe the font vibe and personality physically shown on the screenshot and select the single best matching Font Pairing specifically from our curated TYPOGRAPHY LIBRARY below that evokes that exact same aesthetic!

2. TYPOGRAPHY LIBRARY (Select One Matching Vibe):
   Review the categories below and choose the best matching font pair (`heading_font` + `body_font`) tailored to the website's aesthetic and feel:
   - Luxury & High-End Fashion: Italiana (headline) + Lora (body) | Playfair Display (headline) + Montserrat (body) | Cormorant Garamond (headline) + Proza Libre (body)
   - Modern E-Commerce & Tech: Outfit (headline) + WorkSans (body) | Plus Jakarta Sans (headline) + Inter (body) | Syne (headline) + DM Sans (body)
   - Healthcare & Clean Clinical: Manrope (headline) + Open Sans (body) | Lexend (headline) + Nunito Sans (body) | Albert Sans (headline) + Public Sans (body)
   - High-Tech & Futuristic / Web3: Tektur (headline) + GeistMono (body) | Space Grotesk (headline) + JetBrains Mono (body) | Orbitron (headline) + Roboto Mono (body)
   - Bold Action & Fitness / Sports: BigShoulders Display (headline) + WorkSans (body) | Anton (headline) + Roboto (body) | Bebas Neue (headline) + Montserrat (body)
   - Organic, Natural & Eco-Friendly: Fraunces (headline) + Epilogue (body) | Libre Baskerville (headline) + Source Sans 3 (body) | Josefin Sans (headline) + Lato (body)
   - Playful & Youthful Food / Beverage: Fredoka (headline) + Quicksand (body) | Rubik (headline) + Karla (body) | Righteous (headline) + Poppins (body)
   - Classic Corporate & Professional: Cinzel (headline) + Raleway (body) | Prata (headline) + Lato (body) | Merriweather (headline) + Open Sans (body)

3. HTML, METADATA & FULL-PAGE SCREENSHOT AUDIT (MESSAGING & TRUST - PRIORITIZE IMAGE):
   - Core Messaging: Extract the Hero Headline (H1) and Offer sub-headline by comparing DOM text against what is prominently displayed at the top of the full-page screenshot. Prioritize the visual text hierarchy shown on the image.
   - CTA Mechanics: Identify the exact button text visually displayed on primary conversion CTA buttons inside the screenshot (`e.g., "Start Free Trial", "Get a Quote"`).
   - Trust Signals (100% IMAGE DATA PRIORITY - ZERO ASSUMPTIONS): Carefully inspect the full-page screenshot alongside DOM data. Look for review scores, star icons, rating counts, or "Trusted By" client lists explicitly rendered on the page. Because Image Data takes priority, if the website does NOT explicitly and physically display a numeric star rating on screen, you MUST output `null` or `[]` for those fields (`"rating_score": null`, `"review_count": null`, `"key_client_names": []`). Do NOT invent, assume, or output placeholder numbers like 4.9 or 1000! Only include details that are physically verified on the full-page screenshot!

4. MARKETING ANGLES DIRECTORY (Select One):
   Review all 10 Angles and select the single best `angle_id` (1-10) tailored to the extracted H1 and core service:
   1: AIDA (Attention, Interest, Desire, Action) - Brand Story
   2: PAS (Problem, Agitate, Solution) - Core Pain Point
   3: BAB (Before-After-Bridge) - Transformation
   4: Social Proof & Trust (Testimonials / Metrics)
   5: Product Feature Highlight (Materials & Craftsmanship)
   6: Innovation & Smart Elements
   7: The Explorer / Prestige (Psychological Luxury Appeal)
   8: Minimalist / Contemporary Integration
   9: Emotional Welcome (Festive / Hospitality / Cultural Richness)
   10: Legacy & Long-Term Investment Value

5. VISUAL LAYOUTS DIRECTORY (Select One):
   Review all 10 Layouts and select the single best `layout_id` (1-10) tailored to the brand aesthetic:
   1: Swiss Grid (Asymmetric left-aligned text layout, minimal background)
   2: Marble Pedestal (Centered text, products balanced on a white marble platform)
   3: Linear Gradient Float (Glow effects, products suspended mid-air with soft shadows)
   4: Diagonal Split-Screen (Two-tone background dividing text and product zones)
   5: Studio Reflective (Deep charcoal background, products placed on reflective black glass)
   6: Botanical Minimalist (Overcast natural daylight, soft leaf shadows on concrete walls)
   7: Monolith Frame (Large geometric backing blocks behind the main product)
   8: Warm Editorial (Beige paper textures, classic serif margins, clinical markers)
   9: High-Contrast Spotlight (Dramatic low-key spotlight beam highlighting the product)
   10: Minimal Collage (Overlaying multiple product angles, staggered offsets)

6. CREATIVE BRIEF GENERATION:
   - Generate exactly {NUM_CREATIVES} ad creative configuration(s).
   - `headline`: Must be derived directly from the extracted H1 to ensure cognitive fluency.
   - `offer`: The core value proposition or sub-headline.
   - `cta_text`: The exact text from the website's primary button.
   - `description`: A highly specific visual rendering prompt for GPT Image 2. Describe the physical scene, subject, environment, lighting, and layout based EXACTLY on the chosen layout_id, incorporating the brand colors and trust signals. Do NOT reference or ask for external product/reference image files. Do NOT tell GPT Image 2 to render star ratings or reviews unless they exist in `trust_signals`.

OUTPUT FORMAT:
You MUST return a single, valid JSON object strictly adhering to the following schema. Do NOT wrap the JSON in markdown blocks if it breaks your API parser.

{
  "brand_name": "Extracted from <title> or Open Graph",
  "visual_identity": {
    "colors": {
      "primary": "#HEXCODE",
      "secondary": "#HEXCODE",
      "accent_cta": "#HEXCODE",
      "background": "#HEXCODE"
    },
    "typography": {
      "heading_font": "Selected Headline Font from Library",
      "body_font": "Selected Body Font from Library",
      "vibe_feel": "Brief description of why this font pair matches the website feel"
    }
  },
  "messaging": {
    "value_proposition": "Extracted from <h1>",
    "sub_headline": "Extracted from <h2>",
    "primary_cta_text": "Extracted from <button> or <a>"
  },
  "trust_signals": {
    "rating_score": null,
    "review_count": null,
    "key_client_names": []
  },
  "creatives": [
    {
      "angle_id": 6,
      "layout_id": 9,
      "displayText": {
        "headline": "Derived from H1",
        "offer": "Derived from value proposition",
        "cta_text": "Exact CTA from website",
        "footer": null
      },
      "style": "Keywords describing mood, lighting, and the selected layout style",
      "description": "Comprehensive visual scene description showcasing the exact service/product in action for GPT Image 2 rendering. Incorporate layout instructions and exact hex codes. If footer is null or not analyzing a website URL, do not instruct rendering of a footer or brand URL."
    }
  ]
}
"""
        system_prompt = system_prompt.replace("{NUM_CREATIVES}", str(num_creatives)).replace("{URL}", str(target_url))

        if is_branch_2:
            brand_name = target_url_or_data.get("brandName") or target_url_or_data.get("brand_name", "Brand")
            niche = target_url_or_data.get("category") or target_url_or_data.get("niche", "Service")
            about = target_url_or_data.get("about", "")
            about_str = f"\nAbout / Description: {about}\n" if about else "\n"
            user_prompt = f"""
BRANCH 2 - GRAPHIC DESIGNER & COMPETITOR ANALYSIS MODE:
Target Brand Name: {brand_name}
Target Niche / Industry: {niche}{about_str}
RUN CONFIGURATION:
Generate exactly {num_creatives} creative(s).
You are acting as an agency Creative Director and Lead Graphic Designer for `{brand_name}` inside the `{niche}` industry.
Use your intelligent Web Search API tools to analyze top-performing competitor websites and visual design leaders inside the `{niche}` niche.
1. Color & Vibe: Based on color psychology and competitor standards in `{niche}`, select a high-converting `#HEX` color palette and the best matching font pair from our TYPOGRAPHY LIBRARY.
2. Messaging, Zero-Assumption Trust & Footer: Brainstorm high-converting H1/H2 copy tailored to `{brand_name}` and `{niche}`. Since no explicit review metrics or target website URL were supplied, force `rating_score: null`, `review_count: null`, and strictly set `displayText.footer: null`.
3. Select the best `angle_id` and `layout_id` for `{niche}` and output the complete JSON adhering exactly to the schema instructed above.
"""
        elif has_url:
            extra_meta = ""
            b_name = ""
            if isinstance(target_url_or_data, dict):
                b_name = target_url_or_data.get("brandName") or target_url_or_data.get("brand_name", "")
                b_cat = target_url_or_data.get("category") or target_url_or_data.get("niche", "")
                b_about = target_url_or_data.get("about", "")
                meta_parts = []
                if b_name: meta_parts.append(f"Authoritative Brand Name (Direct from Frontend JSON): {b_name}")
                if b_cat: meta_parts.append(f"Category / Niche: {b_cat}")
                if b_about: meta_parts.append(f"About / Description: {b_about}")
                if meta_parts:
                    extra_meta = "\nSUPPLEMENTAL BRAND METADATA FROM FRONTEND:\n" + "\n".join(meta_parts) + "\n"

            brand_header = f"TARGET BRAND NAME: {b_name}\n" if b_name else ""
            user_prompt = f"""
TARGET BRAND WEBSITE URL TO ANALYZE AND SEARCH:
{target_url}
{brand_header}{extra_meta}
RUN CONFIGURATION:
Generate exactly {num_creatives} creative(s).
We have attached the Full-Page Screenshot (`screenshot_b64`) alongside DOM/text data for `{target_url}`.
CRITICAL MANDATE: Compare both the DOM/metadata and the Full-Page Screenshot, but strictly PRIORITIZE IMAGE DATA ANALYSIS over text/DOM across all visual elements, #HEX colors, button copy, and trust metrics! If any DOM text conflicts with what is physically visible on the screenshot, the visual image data always overrides!
Use your intelligent web search API tools AND visually inspect the full-page screenshot (plus any supplemental metadata) to understand the exact services, catalog, key benefits, target audience, and unique selling points (USPs).
If an Authoritative Brand Name (`{b_name if b_name else 'Brand'}`) is provided above directly from the frontend JSON, you MUST use that exact Brand Name across your copy and JSON structure!
Then, deduce its brand color palette (`brandColors`) and typography (`fonts`) from the image/metadata, intelligently select the single best Marketing Angle (`angle_id` 1-10) and Visual Layout (`layout_id` 1-10) directly from the authoritative directories in your System Prompt based on the discovered brand service, and output the complete JSON.

Please output the complete, fully formed JSON adhering exactly to the schema instructed above.
"""
        else:
            b_name = target_url_or_data.get('brandName') or target_url_or_data.get('brand_name', '') if isinstance(target_url_or_data, dict) else ''
            b_header = f"TARGET BRAND NAME (Direct from Frontend JSON): {b_name}\n" if b_name else ""
            user_prompt = f"""
WEBSITE DATA:
Title: {target_url_or_data.get('title') if isinstance(target_url_or_data, dict) else ''}
{b_header}Optimized HTML Content:
{target_url_or_data.get('optimized_html') if isinstance(target_url_or_data, dict) else ''}

RUN CONFIGURATION:
Generate exactly {num_creatives} creative(s).
We have attached the Full-Page Screenshot alongside the DOM data above.
CRITICAL MANDATE: Compare both the DOM and the Full-Page Screenshot, but strictly PRIORITIZE IMAGE DATA ANALYSIS over text/DOM across all visual elements, #HEX colors, button copy, and trust metrics! If any DOM text conflicts with what is physically visible on the screenshot, the visual image data always overrides!
From the available data AND the attached full-page screenshot, deeply analyze the company's core services, offerings, and value propositions.
If an Authoritative Brand Name (`{b_name if b_name else 'Brand'}`) is provided above directly from the frontend JSON, you MUST use that exact Brand Name across your copy and JSON structure!
Populate the ingredients (`brandColors`, `fonts`), intelligently select the single best Marketing Angle (`angle_id` 1-10) and Visual Layout (`layout_id` 1-10) directly from the directories in your System Prompt based on the brand service, and output the complete JSON.

Please output the complete, fully formed JSON adhering exactly to the schema instructed above.
"""

        raw_response = self.call_llm(system_prompt, user_prompt, use_search=use_search, screenshot_b64=screenshot_b64)
        
        # Programmatic Parsing Pipeline (Robust to LLM format errors)
        import re
        
        # Programmatic Parsing Pipeline (Robust to LLM format errors)
        import re
        from datetime import datetime
        
        # Safely determine scraped dictionary or empty dictionary when target_url_or_data is a URL string
        scraped_dict = target_url_or_data if isinstance(target_url_or_data, dict) else {}
        
        # Save raw output cleanly to a local backup logs folder (`Dashboard/logs/`) for inspection
        try:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            logs_dir = os.path.join(base_dir, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            ts_filepath = os.path.join(logs_dir, f"llm_output_{ts}.txt")
            latest_filepath = os.path.join(logs_dir, "last_llm_raw_output.txt")
            
            with open(latest_filepath, "w", encoding="utf-8") as f:
                f.write(raw_response)
            with open(ts_filepath, "w", encoding="utf-8") as f:
                f.write(raw_response)
            print(f"[+] Stored raw LLM response cleanly to logs folder: {ts_filepath}")
        except Exception as e_log:
            print(f"[!] Warning: Failed to store LLM log output: {e_log}")

        # Cleanup Markdown JSON wrapper code fences
        json_clean = raw_response.strip()
        json_clean = re.sub(r"```(?:json)?\s*([\s\S]*?)\s*```", r"\1", json_clean).strip()
        
        first_brace = json_clean.find("{")
        first_bracket = json_clean.find("[")
        
        # Decide which boundary indicator comes first
        start_idx = min(first_brace, first_bracket) if (first_brace != -1 and first_bracket != -1) else (first_brace if first_brace != -1 else first_bracket)
        last_brace = json_clean.rfind("}")
        last_bracket = json_clean.rfind("]")
        end_idx = max(last_brace, last_bracket)
        
        is_json_parsed = False
        parsed_obj = None
        
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_candidate = json_clean[start_idx:end_idx+1]
            try:
                parsed_obj = json.loads(json_candidate)
                is_json_parsed = True
            except json.JSONDecodeError:
                try:
                    # Strip trailing commas
                    parsed_obj = json.loads(re.sub(r",\s*([}\]])", r"\1", json_candidate))
                    is_json_parsed = True
                except json.JSONDecodeError:
                    pass
                    
        product_images = scraped_dict.get("products", [])
        if not product_images:
            product_images = ["https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&q=80&w=800"]
        logo_url = scraped_dict.get("logos")[0] if scraped_dict.get("logos") else (product_images[0] if len(product_images) > 0 else "")
        ref_image = product_images[0] if len(product_images) > 0 else ""

        creatives = []

        # Case 1: Successfully parsed as JSON
        if is_json_parsed and parsed_obj:
            # Store parsed JSON cleanly in logs as well
            try:
                ts_json_path = os.path.join(logs_dir, f"llm_parsed_{ts}.json")
                with open(ts_json_path, "w", encoding="utf-8") as jf:
                    json.dump(parsed_obj, jf, indent=2)
            except Exception:
                pass

            raw_list = []
            if isinstance(parsed_obj, list):
                raw_list = parsed_obj
            elif isinstance(parsed_obj, dict):
                raw_list = parsed_obj.get("creatives", [])
                if not raw_list:
                    for k, v in parsed_obj.items():
                        if isinstance(v, list):
                            raw_list = v
                            break
                            
            top_brand = parsed_obj.get("brand_name", "") if isinstance(parsed_obj, dict) else ""
            top_service = parsed_obj.get("service", "") if isinstance(parsed_obj, dict) else ""
            top_visual_id = parsed_obj.get("visual_identity", {}) if isinstance(parsed_obj, dict) else {}
            top_messaging = parsed_obj.get("messaging", {}) if isinstance(parsed_obj, dict) else {}
            top_trust = parsed_obj.get("trust_signals", {}) if isinstance(parsed_obj, dict) else {}

            for idx, item in enumerate(raw_list, 1):
                brand_name_val = item.get("brand_name") or top_brand or item.get("brand", {}).get("name", "Brand")
                service_val = item.get("service") or top_service or item.get("brand", {}).get("service", "Commercial product or service")
                headline = item.get("headline", item.get("displayText", {}).get("headline", top_messaging.get("value_proposition", "")))
                offer = item.get("offer", item.get("displayText", {}).get("offer", top_messaging.get("sub_headline", "")))
                cta_text = item.get("cta_text", item.get("displayText", {}).get("cta_text", top_messaging.get("primary_cta_text", "Learn More")))
                raw_footer = item.get("footer", item.get("displayText", {}).get("footer"))
                if not has_url or is_branch_2 or raw_footer in [None, "None", "null", ""]:
                    footer = None
                else:
                    footer = raw_footer
                style = item.get("style", "minimal modern")
                description = item.get("description", "Product presentation design.")
                
                item_ingredients = item.get("ingredients", {})
                brand_style = item.get("brand_style", item.get("brand", {}).get("brandColors", item_ingredients.get("brandColors", {}))) or {}
                
                colors_dict = top_visual_id.get("colors", {}) if isinstance(top_visual_id, dict) else {}
                primary_color = colors_dict.get("primary") or brand_style.get("primary", brand_style.get("primaryColor", "#FFFFFF"))
                secondary_color = colors_dict.get("secondary") or brand_style.get("secondary", brand_style.get("secondaryColor", "#000000"))
                accent_color = colors_dict.get("accent_cta") or colors_dict.get("accent") or brand_style.get("accent", brand_style.get("accentColor", "#FF0000"))
                background_color = colors_dict.get("background", "#F4F4F4")
                
                fonts = item.get("fonts", brand_style.get("fonts", item_ingredients.get("fonts", {}))) or {}
                typography_dict = top_visual_id.get("typography", {}) if isinstance(top_visual_id, dict) else {}
                headline_font = typography_dict.get("heading_font") or fonts.get("headline", fonts.get("headlineFont", "Outfit"))
                body_font = typography_dict.get("body_font") or fonts.get("body", fonts.get("bodyFont", "WorkSans"))
                
                # Prioritize product images discovered directly by LLM Web Search API
                selected_imgs = item_ingredients.get("productImages") or item.get("productImages") or []
                if isinstance(selected_imgs, str):
                    selected_imgs = [selected_imgs]
                if not selected_imgs:
                    selected_imgs = []
                    if len(product_images) > 0:
                        selected_imgs.append(product_images[(idx - 1) % len(product_images)])
                    if len(product_images) > 1:
                        selected_imgs.append(product_images[idx % len(product_images)])
                        
                logo_url_final = item_ingredients.get("logoUrl") or item.get("logoUrl") or logo_url
                ref_image_final = item_ingredients.get("referenceImage") or item.get("referenceImage") or ref_image or (selected_imgs[0] if selected_imgs else "")
                    
                data = {
                    "angle_id": item.get("angle_id", idx),
                    "layout_id": item.get("layout_id", idx),
                    "brand_name": brand_name_val,
                    "service": service_val,
                    "visual_identity": top_visual_id or {
                        "colors": {
                            "primary": primary_color,
                            "secondary": secondary_color,
                            "accent_cta": accent_color,
                            "background": background_color
                        },
                        "typography": {
                            "heading_font": headline_font,
                            "body_font": body_font
                        }
                    },
                    "messaging": top_messaging or {
                        "value_proposition": headline,
                        "sub_headline": offer,
                        "primary_cta_text": cta_text
                    },
                    "trust_signals": top_trust or {
                        "rating_score": None,
                        "review_count": None,
                        "key_client_names": []
                    },
                    "ingredients": {
                        "brandColors": {
                            "primaryColor": primary_color,
                            "secondaryColor": secondary_color,
                            "accentColor": accent_color
                        },
                        "fonts": {
                            "headlineFont": headline_font,
                            "bodyFont": body_font
                        }
                    },
                    "displayText": {
                        "headline": headline,
                        "offer": offer,
                        "cta_text": cta_text,
                        "footer": footer
                    },
                    "style": style,
                    "description": description
                }
                creatives.append(data)
                
        # Case 2: Fallback to Flat-Text parsing
        if not creatives:
            primary_color = "#FFFFFF"
            secondary_color = "#000000"
            accent_color = "#FF0000"
            headline_font = "Outfit"
            body_font = "WorkSans"
            
            color_match = re.search(r"PRIMARY:\s*(#[0-9a-fA-F]{6})", raw_response, re.IGNORECASE)
            if color_match:
                primary_color = color_match.group(1)
            sec_match = re.search(r"SECONDARY:\s*(#[0-9a-fA-F]{6})", raw_response, re.IGNORECASE)
            if sec_match:
                secondary_color = sec_match.group(1)
            acc_match = re.search(r"ACCENT:\s*(#[0-9a-fA-F]{6})", raw_response, re.IGNORECASE)
            if acc_match:
                accent_color = acc_match.group(1)
                
            font_match = re.search(r"FONTS:\s*([\w\s-]+)\s*,\s*([\w\s-]+)", raw_response)
            if font_match:
                headline_font = font_match.group(1).strip()
                body_font = font_match.group(2).strip()

            sections = re.split(r"===\s*AD CREATIVE \d+\s*===", raw_response)
            for idx, sec in enumerate(sections[1:], 1):
                lines = sec.strip().splitlines()
                
                def get_val(prefix):
                    for line in lines:
                        if line.strip().upper().startswith(prefix.upper()):
                            return line.strip()[len(prefix):].strip()
                    return ""
                    
                headline = get_val("HEADLINE:")
                brand_val = get_val("BRAND NAME:") or get_val("BRAND:") or "Brand"
                service_val = get_val("SERVICE:") or "Commercial product or service"
                offer = get_val("OFFER:")
                raw_footer = get_val("FOOTER:")
                if not is_url or is_branch_2 or raw_footer in [None, "None", "null", ""]:
                    footer = None
                else:
                    footer = raw_footer
                style = get_val("STYLE:") or "minimal modern"
                description = get_val("DESCRIPTION:") or "Product creative presentation."
                    
                data = {
                    "angle_id": idx,
                    "layout_id": idx,
                    "brand_name": brand_val,
                    "service": service_val,
                    "ingredients": {
                        "brandColors": {
                            "primaryColor": primary_color,
                            "secondaryColor": secondary_color,
                            "accentColor": accent_color
                        },
                        "fonts": {
                            "headlineFont": headline_font,
                            "bodyFont": body_font
                        }
                    },
                    "displayText": {
                        "headline": headline,
                        "offer": offer,
                        "footer": footer
                    },
                    "style": style,
                    "description": description
                }
                creatives.append(data)
                
        return {"creatives": creatives}

if __name__ == "__main__":
    # Test stub
    print("Testing CreativeEngine Module...")
    # To run this test, set environment variable: export LLM_API_KEY="your-key"
    mock_data = {
        "title": "Timex Ceramic",
        "images": ["https://www.timexceramic.com/wp-content/uploads/2026/06/AMBIENTE-DELORMO-Adrien-1.webp"],
        "optimized_html": "<body><h1>Timex Ceramic</h1><p>Premium imported designer wall and floor tiles in Mumbai, India.</p></body>"
    }
    
    # Example usage:
    # engine = CreativeEngine(provider="openai", api_key="sk-...")
    # results = engine.generate_ad_creatives(mock_data, "AIDA (Attention, Interest, Desire, Action)")
    # print(json.dumps(results, indent=2))
