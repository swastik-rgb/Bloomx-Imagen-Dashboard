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

    def call_llm(self, system_prompt, user_prompt, use_search=False):
        """Calls the OpenAI API with retry backoff and optional Web Search tool enabled."""
        import time
        max_retries = 6
        backoff_delay = 5
        
        for attempt in range(max_retries):
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                if use_search:
                    try:
                        # Try with OpenAI web_search tool enabled
                        response = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=messages,
                            tools=[{"type": "web_search"}]
                        )
                        return response.choices[0].message.content
                    except Exception:
                        # Fallback if model/key tier doesn't support tools flag
                        pass
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    response_format={"type": "json_object"},
                    messages=messages
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                print(f"    [!] OpenAI LLM Call failed (Attempt {attempt+1}/{max_retries}): {str(e)[:120]}. Retrying in {backoff_delay}s...")
                time.sleep(backoff_delay)
                backoff_delay *= 2

    def generate_image(self, prompt, output_path):
        """Generates an ad creative image via OpenAI DALL-E 3 / GPT Image 2."""
        print(f"[*] Generating visual creative via OPENAI API...")
        try:
            response = self.client.images.generate(
                model="gpt-image-2",
                prompt=prompt,
                n=1,
                size="1024x1024",
                quality="low"
            )
            
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
            print(f"[!] OpenAI Image generation failed: {e}")
            return False

    def generate_ad_creatives(self, target_url_or_data, angles_list, layouts_list, use_search=True):
        """
        Brainstorms ad copy, brand assets, and visual layout concepts using AI Web Search capabilities on the target URL.
        Programmatically parses the LLM output into our strict JSON structured schema containing ingredients and display text.
        """
        is_url = isinstance(target_url_or_data, str)
        target_url = target_url_or_data if is_url else target_url_or_data.get("url", "Brand Website")
        
        system_prompt = """
You are an expert commercial advertising designer, AI data analyst, and brand strategist.
Your task is to analyze the brand website URL provided by the user using your web search and knowledge capabilities to deeply inspect the website, understand the core services, products, value propositions, unique selling points (USPs), target audience, aesthetic, colors, and fonts.

INSTRUCTIONS:
1. Conduct a deep, thorough analysis of the target website URL (`{URL}`) and its core business model using your web search tools. Specifically explore:
   - What core service or product does this company provide?
   - What are their unique selling propositions (USPs) and primary benefits?
   - Who is their target audience or ideal customer?
   - What are their actual pricing plans, key features, or signature offerings?
2. Deduce the brand's exact color palette (`primaryColor`, `secondaryColor`, and `accentColor` in `#HEX` format).
3. Select a suitable font pairing from this expanded typography library based on brand personality and industry:
   - Luxury & High-End Fashion: Italiana (headline) + Lora (body) | Playfair Display (headline) + Montserrat (body) | Cormorant Garamond (headline) + Proza Libre (body)
   - Modern E-Commerce & Tech: Outfit (headline) + WorkSans (body) | Plus Jakarta Sans (headline) + Inter (body) | Syne (headline) + DM Sans (body)
   - Healthcare & Clean Clinical: Manrope (headline) + Open Sans (body) | Lexend (headline) + Nunito Sans (body) | Albert Sans (headline) + Public Sans (body)
   - High-Tech & Futuristic / Web3: Tektur (headline) + GeistMono (body) | Space Grotesk (headline) + JetBrains Mono (body) | Orbitron (headline) + Roboto Mono (body)
   - Bold Action & Fitness / Sports: BigShoulders Display (headline) + WorkSans (body) | Anton (headline) + Roboto (body) | Bebas Neue (headline) + Montserrat (body)
   - Organic, Natural & Eco-Friendly: Fraunces (headline) + Epilogue (body) | Libre Baskerville (headline) + Source Sans 3 (body) | Josefin Sans (headline) + Lato (body)
   - Playful & Youthful Food / Beverage: Fredoka (headline) + Quicksand (body) | Rubik (headline) + Karla (body) | Righteous (headline) + Poppins (body)
   - Classic Corporate & Professional: Cinzel (headline) + Raleway (body) | Prata (headline) + Lato (body) | Merriweather (headline) + Open Sans (body)
4. Generate exactly {NUM_CREATIVES} ad creative configuration(s), pairing Angle X with Layout X (for X from 1 to {NUM_CREATIVES}).
   - In `displayText`, craft a compelling, conversion-focused `headline` and `offer` directly based on the exact services, benefits, and value propositions you discovered about the company. Never use generic or placeholder copy.
   - In `description`, write a comprehensive, highly specific visual rendering prompt for DALL-E 3. Describe the physical scene, subject, environment, materials, lighting, and composition that directly illustrates the company's real service or product in action.

You MUST return a single, valid JSON object strictly adhering to the following schema:
{
  "brand_name": "Actual Brand Name Discovered",
  "service": "Concise summary of the core service or product offered by the company",
  "brand_style": {
    "primary": "#HEXCODE",
    "secondary": "#HEXCODE",
    "accent": "#HEXCODE",
    "fonts": {
      "headline": "HeadlineFontName",
      "body": "BodyFontName"
    }
  },
  "creatives": [
    {
      "angle_id": 1,
      "layout_id": 1,
      "brand_name": "Actual Brand Name Discovered",
      "service": "Concise summary of the core service or product offered by the company",
      "ingredients": {
        "brandColors": {
          "primaryColor": "#HEXCODE",
          "secondaryColor": "#HEXCODE",
          "accentColor": "#HEXCODE"
        },
        "fonts": {
          "headlineFont": "HeadlineFontName",
          "bodyFont": "BodyFontName"
        }
      },
      "displayText": {
        "headline": "Service/Product Specific Headline",
        "offer": "EXACT SERVICE OFFER OR VALUE PROPOSITION",
        "footer": "Brand website / Terms"
      },
      "style": "design styling keywords describing mood and lighting",
      "description": "Comprehensive visual scene description showcasing the exact service/product in action for DALL-E rendering"
    }
  ]
}
"""
        system_prompt = system_prompt.replace("{NUM_CREATIVES}", str(len(angles_list))).replace("{URL}", str(target_url))

        # Format angles and layouts list for prompt
        angles_formatted = "\n".join([f"Angle {i}: {angle}" for i, angle in enumerate(angles_list, 1)])
        layouts_formatted = "\n".join([f"Layout {i}: {layout}" for i, layout in enumerate(layouts_list, 1)])

        if is_url:
            user_prompt = f"""
TARGET BRAND WEBSITE URL TO ANALYZE AND SEARCH:
{target_url}

RUN CONFIGURATION:
Generate exactly {len(angles_list)} creative(s). Pair Angle X with Layout X (for X from 1 to {len(angles_list)}).
Use your intelligent web search API tools to inspect {target_url}. Explore and understand the exact services, product catalog, key benefits, target audience, and unique selling points (USPs) of this business.
Then, deduce its brand color palette (`brandColors`) and typography (`fonts`), and generate the ad creatives tailored precisely to what this company provides.

MARKETING ANGLES LIST:
{angles_formatted}

VISUAL LAYOUTS LIST:
{layouts_formatted}

Please output the complete, fully formed JSON adhering exactly to the schema instructed above.
"""
        else:
            user_prompt = f"""
WEBSITE DATA:
Title: {target_url_or_data.get('title')}
Optimized HTML Content:
{target_url_or_data.get('optimized_html')}

RUN CONFIGURATION:
Generate exactly {len(angles_list)} creative(s). Pair Angle X with Layout X (for X from 1 to {len(angles_list)}).
From the available data above, deeply analyze the company's core services, offerings, and value propositions. Populate the ingredients (`brandColors`, `fonts`) and tailor the `displayText` and visual `description` precisely to the business's actual services for every creative.

MARKETING ANGLES LIST:
{angles_formatted}

VISUAL LAYOUTS LIST:
{layouts_formatted}

Please output the complete, fully formed JSON adhering exactly to the schema instructed above.
"""

        raw_response = self.call_llm(system_prompt, user_prompt, use_search=use_search)
        
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
            for idx, item in enumerate(raw_list, 1):
                brand_name_val = item.get("brand_name") or top_brand or item.get("brand", {}).get("name", "Brand")
                service_val = item.get("service") or top_service or item.get("brand", {}).get("service", "Commercial product or service")
                headline = item.get("headline", item.get("displayText", {}).get("headline", ""))
                offer = item.get("offer", item.get("displayText", {}).get("offer", ""))
                footer = item.get("footer", item.get("displayText", {}).get("footer", "*Terms apply."))
                style = item.get("style", "minimal modern")
                description = item.get("description", "Product presentation design.")
                
                item_ingredients = item.get("ingredients", {})
                brand_style = item.get("brand_style", item.get("brand", {}).get("brandColors", item_ingredients.get("brandColors", {}))) or {}
                
                primary_color = brand_style.get("primary", brand_style.get("primaryColor", "#FFFFFF"))
                secondary_color = brand_style.get("secondary", brand_style.get("secondaryColor", "#000000"))
                accent_color = brand_style.get("accent", brand_style.get("accentColor", "#FF0000"))
                
                fonts = item.get("fonts", brand_style.get("fonts", item_ingredients.get("fonts", {}))) or {}
                headline_font = fonts.get("headline", fonts.get("headlineFont", "Outfit"))
                body_font = fonts.get("body", fonts.get("bodyFont", "WorkSans"))
                
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
                    "angle_id": idx,
                    "layout_id": idx,
                    "brand_name": brand_name_val,
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
                footer = get_val("FOOTER:") or "*Terms apply."
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
