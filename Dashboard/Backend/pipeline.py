import os
import re
import json
import argparse
from scraper import scrape_and_optimize
from creative_engine import CreativeEngine, load_env_file
from prompt_converter import json_to_design_brief

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

    def run(self, url, bulk=False, output_dir="output_creatives", limit=1, generate_image=True):
        """
        Runs the full end-to-end hybrid ad generation pipeline:
        1. Scrape & Optimize website assets (Deterministic Python).
        2. Generate structured JSON ad briefs in single-batch LLM calls (saves 90% quota).
        3. Convert JSON briefs into final GPT Image 2 prompts (Deterministic Python).
        4. Optionally generate real ad images using Imagen 3 / DALL-E 3.
        """
        print(f"[*] Step 1: Analyzing website structure & extracting assets via AI Web Search API: {url}")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        manifest = []

        # Slicing logic for limit option
        target_angles = self.angles
        target_layouts = self.layouts
        if not bulk and limit is None:
            limit = 1
        if limit is not None:
            print(f"[*] Limit parameter enabled. Restricting run to exactly {limit} creative(s) (1 prompt & 1 image).")
            target_angles = self.angles[:limit]
            target_layouts = self.layouts[:limit]

        # Batched run configurations (each batch is a single API call generating creatives)
        batches = []
        if bulk:
            print(f"[*] Bulk mode enabled. Scheduling batch calls to generate creatives matrix...")
            for l_idx, layout in enumerate(target_layouts, 1):
                batches.append((
                    target_angles, 
                    [layout] * len(target_angles),
                    [a_idx for a_idx in range(1, len(target_angles) + 1)],
                    [l_idx] * len(target_angles)
                ))
        else:
            print(f"[*] Standard mode enabled. Generating {len(target_angles)} paired ad creatives in 1 single API call...")
            batches.append((
                target_angles,
                target_layouts,
                [i for i in range(1, len(target_angles) + 1)],
                [i for i in range(1, len(target_layouts) + 1)]
            ))

        for b_num, (angles, layouts, angle_ids, layout_ids) in enumerate(batches, 1):
            print(f"[*] Executing LLM batch {b_num}/{len(batches)} via AI Web Search (generating {len(angles)} creatives)...")
            
            # Call LLM once using Web Search capabilities to generate all creatives for this batch
            response_json = self.engine.generate_ad_creatives(url, angles, layouts, use_search=True)
            
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
                
                clean_brand = re.sub(r'[\\/*?:"<>|]', "", creative.get("brand_name", "Brand")).strip()
                if not clean_brand or clean_brand.lower() == "brand":
                    # Try to deduce from URL if possible or fallback
                    clean_brand = "Brand"
                
                if len(creatives) == 1:
                    creative_id = f"{clean_brand} Ad Creative"
                else:
                    creative_id = f"{clean_brand} Ad Creative - Angle {a_idx} Layout {l_idx}"
                
                # Programmatically convert to GPT Image 2 prompt
                design_brief_prompt = json_to_design_brief(creative)
                
                # Setup structured output paths
                filename_base = os.path.join(output_dir, creative_id)
                
                # Save JSON
                with open(f"{filename_base}.json", "w", encoding="utf-8") as f:
                    json.dump(creative, f, indent=2)
                
                # Save Design Brief Text Prompt
                with open(f"{filename_base}.txt", "w", encoding="utf-8") as f:
                    f.write(design_brief_prompt)
                
                # Generate actual image using API if requested
                image_generated = False
                image_filename = f"{creative_id}.png"
                if generate_image:
                    image_path = os.path.join(output_dir, image_filename)
                    image_generated = self.engine.generate_image(design_brief_prompt, image_path)
                
                manifest_entry = {
                    "id": creative_id,
                    "angle_id": a_idx,
                    "angle_name": angle_name,
                    "layout_id": l_idx,
                    "layout_name": layout_name,
                    "json_file": f"{creative_id}.json",
                    "prompt_file": f"{creative_id}.txt",
                    "image_file": image_filename if image_generated else None,
                    "data": creative
                }
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
    parser.add_argument("--url", type=str, required=True, help="Brand website URL to analyze")
    parser.add_argument("--provider", type=str, default="openai", choices=["openai"], help="LLM API provider (OpenAI exclusively)")
    parser.add_argument("--bulk", action="store_true", help="Generate 100 creatives matrix (10 angles x 10 layouts)")
    parser.add_argument("--output", type=str, default="output_creatives", help="Directory to save generated creatives")
    parser.add_argument("--limit", type=int, default=1, help="Limit number of creatives to generate (defaults to 1)")
    parser.add_argument("--image", action="store_true", default=True, dest="image", help="Generate actual ad creative image (defaults to True)")
    parser.add_argument("--no-image", action="store_false", dest="image", help="Skip DALL-E image generation API (test Stage 1 & Stage 2 prompt compilation only)")
    
    args = parser.parse_args()
    
    # Retrieve API key from environment or .env
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
    if not api_key:
        print("[!] Error: OPENAI_API_KEY or LLM_API_KEY not set in .env file or environment.")
        exit(1)
        
    limit_val = None if args.bulk else args.limit
    pipeline = AdGenerationPipeline(provider="openai", api_key=api_key)
    pipeline.run(args.url, bulk=args.bulk, output_dir=args.output, limit=limit_val, generate_image=args.image)
