import os
import re
import json
import argparse

from creative_engine import CreativeEngine, load_env_file
from prompt_converter import json_to_design_brief
from screenshot_engine import capture_or_load_screenshot

class AdGenerationPipeline:
    def __init__(self, provider="openai", api_key=None):
        """
        Initializes the pipeline with a configured OpenAI Creative Engine.
        """
        load_env_file()
        self.engine = CreativeEngine(provider="openai", api_key=api_key)
        
        # Standard 10 Marketing Angles/Hooks to run
        self.angles = [
            "AIDA (Attention, Interest, Desire, Action) - Brand Story",
            "PAS (Problem, Agitate, Solution) - Core Pain Point",
            "BAB (Before-After-Bridge) - Transformation",
            "Social Proof & Trust (Testimonials/Metrics)",
            "Product Feature Highlight (Materials & Craftsmanship)",
            "Innovation & Smart Elements",
            "The Explorer/Prestige (Psychological luxury appeal)",
            "Minimalist/Contemporary Integration",
            "Emotional Welcome (Festive/Hospitality)",
            "Legacy & Long-Term Investment Value"
        ]

        # Standard 10 Visual Layouts
        self.layouts = [
            "Swiss Grid (Asymmetric left-aligned text layout, minimal background)",
            "Marble Pedestal (Centered text, products balanced on a white marble platform)",
            "Linear Gradient Float (Glow effects, products suspended mid-air with soft shadows)",
            "Diagonal Split-Screen (Two-tone background dividing text and product zones)",
            "Studio Reflective (Deep charcoal background, products placed on reflective black glass)",
            "Botanical Minimalist (Overcast natural daylight, soft leaf shadows on concrete walls)",
            "Monolith Frame (Large geometric backing blocks behind the main product)",
            "Warm Editorial (Beige paper textures, classic serif margins, clinical markers)",
            "High-Contrast Spotlight (Dramatic low-key spotlight beam highlighting the product)",
            "Minimal Collage (Overlaying multiple product angles, staggered offsets)"
        ]

    def run(self, url_or_data, bulk=False, output_dir="output_creatives", limit=1, generate_image=True, screenshot_path=None, use_vision=True):
        """
        Runs the full end-to-end hybrid ad generation pipeline:
        Branch 1 (URL Mode): Scrape & capture visual screenshot for multimodal cross-check.
        Branch 2 (Brand & Niche Mode): AI acts as Graphic Designer, analyzes competitor websites via Web Search API.
        Generates structured JSON ad briefs, converts into GPT Image 2 prompts, and renders actual images.
        """
        is_branch_2 = isinstance(url_or_data, dict) and not bool(url_or_data.get("url")) and ("niche" in url_or_data or "category" in url_or_data)
        brand_name_disp = url_or_data.get('brand_name') or url_or_data.get('brandName', 'Brand') if isinstance(url_or_data, dict) else url_or_data
        niche_disp = url_or_data.get('niche') or url_or_data.get('category', 'Category') if isinstance(url_or_data, dict) else ''
        target_display = f"Brand: {brand_name_disp} | Niche: {niche_disp}" if is_branch_2 else url_or_data
        print(f"[*] Step 1: Analyzing target via AI Web Search & Vision API ({'Branch 2: Competitor Analysis & Graphic Designer Mode' if is_branch_2 else 'Branch 1: URL Scraping & Vision Mode'}): {target_display}")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        manifest = []

        screenshot_b64 = None
        if use_vision and not is_branch_2:
            try:
                target_url_str = url_or_data.get("url", str(url_or_data)) if isinstance(url_or_data, dict) else url_or_data
                if isinstance(target_url_str, str) and target_url_str and not target_url_str.startswith("http://") and not target_url_str.startswith("https://") and "." in target_url_str:
                    target_url_str = f"https://{target_url_str}"
                screenshot_target = screenshot_path if screenshot_path else target_url_str
                screenshot_b64 = capture_or_load_screenshot(screenshot_target, os.path.join(output_dir, "landing_page_screenshot.png"))
                if screenshot_b64:
                    print(f"[+] Multimodal Vision Cross-Check enabled (Screenshot Base64 loaded).")
                else:
                    print(f"[-] Vision Cross-Check fallback to text/DOM scraping only.")
            except Exception as e_scr:
                print(f"[-] Screenshot capture warning: {e_scr}")

        # Slicing logic for limit option
        if not bulk and limit is None:
            limit = 1
        if limit is not None:
            print(f"[*] Limit parameter enabled. Restricting run to exactly {limit} creative(s) (1 prompt & 1 image).")

        # Batched run configurations (each batch is a single API call generating creatives)
        batches = []
        if bulk:
            target_angles = self.angles[:limit] if limit is not None else self.angles
            target_layouts = self.layouts[:limit] if limit is not None else self.layouts
            print(f"[*] Bulk mode enabled. Scheduling batch calls to generate creatives matrix...")
            for l_idx, layout in enumerate(target_layouts, 1):
                batches.append((
                    target_angles, 
                    [layout] * len(target_angles),
                    [a_idx for a_idx in range(1, len(target_angles) + 1)],
                    [l_idx] * len(target_angles),
                    len(target_angles)
                ))
        else:
            print(f"[*] Standard mode enabled. AI will intelligently select best angle & layout from all {len(self.angles)} options...")
            batches.append((
                self.angles,
                self.layouts,
                [i for i in range(1, len(self.angles) + 1)],
                [i for i in range(1, len(self.layouts) + 1)],
                limit if limit is not None else 1
            ))

        for b_num, (angles, layouts, angle_ids, layout_ids, num_creatives) in enumerate(batches, 1):
            print(f"[*] Executing LLM batch {b_num}/{len(batches)} via AI Web Search & Vision (generating {num_creatives} creatives)...")
            
            # Call LLM once using Web Search & Vision capabilities to generate all creatives for this batch
            response_json = self.engine.generate_ad_creatives(url_or_data, angles, layouts, use_search=True, num_creatives=num_creatives, screenshot_b64=screenshot_b64)
            
            if "error" in response_json:
                print(f"    [!] Error generating batch: {response_json['error']}")
                continue
                
            creatives = response_json.get("creatives", [])
            for idx, creative in enumerate(creatives):
                # Resolve IDs (fallback if LLM misses matching properties)
                a_idx = creative.get("angle_id", angle_ids[idx] if idx < len(angle_ids) else idx + 1)
                l_idx = creative.get("layout_id", layout_ids[idx] if idx < len(layout_ids) else idx + 1)
                
                angle_name = self.angles[a_idx - 1] if 0 < a_idx <= len(self.angles) else "Custom Angle"
                layout_name = self.layouts[l_idx - 1] if 0 < l_idx <= len(self.layouts) else "Custom Layout"
                
                # Enrich creative data with full context for converter
                creative["angle_name"] = angle_name
                creative["layout_name"] = layout_name
                
                # Populate top-level visual identity & messaging if returned
                if "visual_identity" in response_json:
                    creative["visual_identity"] = response_json["visual_identity"]
                if "messaging" in response_json:
                    creative["messaging"] = response_json["messaging"]
                if "trust_signals" in response_json:
                    creative["trust_signals"] = response_json["trust_signals"]
                if "brand_name" in response_json and response_json["brand_name"]:
                    creative["brand_name"] = response_json["brand_name"]
                elif is_branch_2:
                    creative["brand_name"] = url_or_data.get("brand_name", "Brand")

                # Convert to design brief prompt
                brief_prompt = json_to_design_brief(creative)
                
                # Naming and saving
                brand_str = creative.get("brand_name", "").strip() or (url_or_data.get("brand_name") or url_or_data.get("brandName") if isinstance(url_or_data, dict) else "Brand")
                clean_brand = re.sub(r'[^a-zA-Z0-9_-]', ' ', brand_str).strip() or "Brand"
                clean_brand = " ".join(clean_brand.split()[:3])
                
                # Check for Frontend Client Name & Phone No for exact "Name##PhoneNo.png" naming
                client_name = ""
                client_phone = ""
                if isinstance(url_or_data, dict):
                    client_name = str(url_or_data.get("client_name") or url_or_data.get("name") or "").strip()
                    client_phone = str(url_or_data.get("client_phone") or url_or_data.get("phone") or url_or_data.get("phone_no") or "").strip()

                if client_name or client_phone:
                    clean_name = re.sub(r'[\\/*?:"<>|]', '', client_name or "Client").strip()
                    clean_phone = re.sub(r'[\\/*?:"<>|]', '', client_phone or "0000000000").strip()
                    base_filename = f"{clean_name}##{clean_phone}"
                elif bulk or (limit is not None and limit > 1):
                    base_filename = f"{clean_brand} Angle_{a_idx} Layout_{l_idx}"
                else:
                    base_filename = f"{clean_brand} Ad Creative"
                    
                json_path = os.path.join(output_dir, f"{base_filename}.json")
                txt_path = os.path.join(output_dir, f"{base_filename}.txt")
                img_path = os.path.join(output_dir, f"{base_filename}.png")
                
                # Save JSON brief
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(creative, f, indent=2)
                print(f"    [+] Saved structured brief: {json_path}")
                
                # Save TXT prompt
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(brief_prompt)
                print(f"    [+] Saved design prompt: {txt_path}")
                
                manifest_entry = {
                    "id": base_filename,
                    "brand": brand_str,
                    "angle": angle_name,
                    "layout": layout_name,
                    "json_path": json_path,
                    "prompt_path": txt_path,
                    "image_path": None,
                    "json_file": f"{base_filename}.json",
                    "prompt_file": f"{base_filename}.txt",
                    "image_file": None,
                    "data": creative
                }

                # Generate Actual Image using GPT Image 2 model
                if generate_image:
                    img_success = self.engine.generate_image(brief_prompt, img_path)
                    drive_status = "Failure"
                    creative_link = ""
                    if img_success:
                        manifest_entry["image_path"] = img_path
                        manifest_entry["image_file"] = f"{base_filename}.png"
                        
                        # Upload exact Name##PhoneNo.png directly to Google Drive
                        try:
                            from drive_uploader import upload_to_gdrive
                            gdrive_res = upload_to_gdrive(img_path, filename=f"{base_filename}.png")
                            if gdrive_res and isinstance(gdrive_res, dict):
                                manifest_entry["gdrive_id"] = gdrive_res.get("id")
                                g_link = f"https://drive.google.com/uc?export=download&id={gdrive_res.get('id')}"
                                manifest_entry["gdrive_link"] = g_link
                                creative_link = g_link
                                drive_status = "Success"
                        except Exception as e_drive:
                            print(f"[-] Google Drive upload hook error: {e_drive}")
                            
                    # Automatically update Google Sheet (Creative Link & Drive Status)
                    try:
                        from sheet_updater import update_lead_sheet, append_debug_log
                        if isinstance(url_or_data, dict):
                            update_lead_sheet(url_or_data, creative_link=creative_link, drive_status=drive_status)
                            
                            # Upload Screenshot if available
                            screenshot_link = ""
                            # Screenshot upload disabled per user request

                            # Append to Raw Debug Logs Tab
                            debug_data = {
                                "brand_name": url_or_data.get("brandName") or url_or_data.get("brand_name") or "",
                                "input_json": json.dumps(url_or_data),
                                "sys_prompt": getattr(self.engine, "last_system_prompt", ""),
                                "user_prompt": getattr(self.engine, "last_user_prompt", ""),
                                "raw_output": getattr(self.engine, "last_raw_response", ""),
                                "image_prompt": brief_prompt,
                                "raw_image_output": getattr(self.engine, "last_image_raw_response", ""),
                                "drive_link": creative_link,
                                "screenshot_link": screenshot_link
                            }
                            append_debug_log(debug_data)
                    except Exception as e_sheet:
                        print(f"[-] Google Sheet update hook error: {e_sheet}")
                
                manifest.append(manifest_entry)

        # Save unified manifest of all creatives
        manifest_path = os.path.join(output_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
            
        print(f"[+] Pipeline execution complete. {len(manifest)} creatives saved to '{output_dir}/'")
        return manifest

if __name__ == "__main__":
    load_env_file()
    parser = argparse.ArgumentParser(description="BloomX Ad Creative Generation Pipeline (OpenAI API)")
    parser.add_argument("--url", type=str, required=False, default=None, help="Brand website URL to analyze (Branch 1 Mode)")
    parser.add_argument("--brand", type=str, required=False, default=None, help="Brand name to analyze via competitor design standards (Branch 2 Mode)")
    parser.add_argument("--niche", type=str, required=False, default=None, help="Brand service/niche to analyze top competitors (Branch 2 Mode)")
    parser.add_argument("--provider", type=str, default="openai", choices=["openai"], help="LLM API provider (OpenAI exclusively)")
    parser.add_argument("--bulk", action="store_true", help="Generate 100 creatives matrix (10 angles x 10 layouts)")
    parser.add_argument("--output", type=str, default="output_creatives", help="Directory to save generated creatives")
    parser.add_argument("--limit", type=int, default=1, help="Limit number of creatives to generate (defaults to 1)")
    parser.add_argument("--image", action="store_true", default=True, dest="image", help="Generate actual ad creative image (defaults to True)")
    parser.add_argument("--no-image", action="store_false", dest="image", help="Skip GPT Image 2 API (test Stage 1 & Stage 2 prompt compilation only)")
    parser.add_argument("--screenshot", type=str, default=None, help="Optional path to local screenshot image to pass for vision cross-check")
    parser.add_argument("--no-vision", action="store_false", dest="use_vision", default=True, help="Disable multimodal screenshot cross-checking")
    
    args = parser.parse_args()
    
    if not args.url and not (args.brand and args.niche):
        parser.error("You must specify either --url (Branch 1: URL Mode) OR both --brand and --niche (Branch 2: Graphic Designer Mode).")
        
    # Retrieve API key from environment or .env
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
    if not api_key:
        print("[!] Error: OPENAI_API_KEY or LLM_API_KEY not set in .env file or environment.")
        exit(1)
        
    limit_val = None if args.bulk else args.limit
    pipeline = AdGenerationPipeline(provider="openai", api_key=api_key)
    
    if args.url:
        pipeline.run(args.url, bulk=args.bulk, output_dir=args.output, limit=limit_val, generate_image=args.image, screenshot_path=args.screenshot, use_vision=args.use_vision)
    else:
        pipeline.run({"brand_name": args.brand, "niche": args.niche}, bulk=args.bulk, output_dir=args.output, limit=limit_val, generate_image=args.image, screenshot_path=args.screenshot, use_vision=args.use_vision)
