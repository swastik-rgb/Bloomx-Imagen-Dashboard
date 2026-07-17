def json_to_design_brief(json_data):
    """
    Converts a structured JSON payload into the final formatted text design brief
    matching the Cognitive Fluency Prompt Architecture.
    """
    creative_data = json_data
    typography = json_data.get("visual_identity", {}).get("typography", {})
    heading_font = typography.get("heading_font", "Outfit")
    body_font = typography.get("body_font", "WorkSans")
    vibe_feel = typography.get("vibe_feel", "Modern and clean aesthetic aligning with website feel")

    trust = json_data.get("trust_signals", {})
    rating = trust.get("rating_score") if isinstance(trust, dict) else None
    reviews = trust.get("review_count") if isinstance(trust, dict) else None
    clients = trust.get("key_client_names") if isinstance(trust, dict) else []

    trust_items = []
    if rating is not None and reviews is not None and rating != "null" and reviews != "null" and str(rating).strip() != "" and str(reviews).strip() != "":
        trust_items.append(f"{rating} Stars | {reviews} Reviews")
    elif rating is not None and rating != "null" and str(rating).strip() != "":
        trust_items.append(f"{rating} Stars")
    
    clean_clients = [str(c) for c in clients if c and str(c) not in ("Client 1", "Client 2", "null", "None")] if isinstance(clients, list) else []
    if clean_clients:
        trust_items.append("Trusted by: " + ", ".join(clean_clients))

    trust_str = " | ".join(trust_items) if trust_items else "No numeric ratings or review counts listed explicitly on website (STRICT FACTUALITY: DO NOT hallucinate, invent, or draw any star ratings, review numbers, or fake badges anywhere on the image)."

    display_text = creative_data.get('displayText', {})
    headline_txt = display_text.get('headline', '')
    offer_txt = display_text.get('offer', '')
    cta_txt = display_text.get('cta_text', '')
    footer_txt = display_text.get('footer')
    if footer_txt in [None, "None", "null", ""]:
        footer_line = "Footer / Trust: None (Do not render any footer text or website URL)"
    else:
        footer_line = f"Footer / Trust: {footer_txt}"

    brief_template = f"""Create a brand-new image from scratch. Do not edit, modify, or use any existing image.

You are an expert commercial advertising designer. Your objective is to create a professional marketing creative that achieves perfect "Cognitive Fluency"—meaning this ad must look, feel, and read exactly like the brand's landing page to ensure zero friction when a user clicks through.

--------------------------------------------------
BRAND IDENTITY & VISUAL FEEL
--------------------------------------------------
Brand Name: {json_data.get('brand_name', 'Brand')}
Core Value Proposition: {json_data.get('messaging', {}).get('value_proposition', 'Premium Service')}
Trust Signals: {trust_str}

Brand Color Palette (EXACT CSS MATCH):
Primary Color: {json_data.get('visual_identity', {}).get('colors', {}).get('primary', '#FFFFFF')}
Secondary Color: {json_data.get('visual_identity', {}).get('colors', {}).get('secondary', '#000000')}
Accent/CTA Color: {json_data.get('visual_identity', {}).get('colors', {}).get('accent_cta', '#FF0000')}
Background Color: {json_data.get('visual_identity', {}).get('colors', {}).get('background', '#F4F4F4')}

Typography & Vibe Match (Feel Continuity):
Headline Font Style: {heading_font}
Body Font Style: {body_font}
Website Typography Feel: {vibe_feel}
(Render the typography strictly simulating this exact font personality and vibe so it feels identical to the website experience).

Art Direction & Scene:
{creative_data.get('description', '')}

--------------------------------------------------
TEXT TO DISPLAY (COGNITIVE FLUENCY RULES)
--------------------------------------------------
Display the following text EXACTLY as provided. It was extracted directly from the website's DOM to ensure landing page continuity. Do not rewrite or hallucinate additional copy.

Headline (H1 Match): {headline_txt}
Offer Subtext: {offer_txt}
Button Text (CTA): {cta_txt}
{footer_line}

--------------------------------------------------
LAYOUT & COMPOSITION RULES
--------------------------------------------------
1. Maintain strong visual hierarchy using a clean modern design grid.
2. Separate layout zones:
   - Top 40% of the canvas: Exclusively reserved for Headline, Offer, and brand metadata.
   - Bottom 60% of the canvas: Reserved for clean staging surfaces, product representations, and shadows.
3. Call-To-Action (CTA) Mechanics: The Button Text must be placed in a distinct, high-contrast button shape at the bottom of the creative, utilizing the EXACT Accent/CTA Hex Color provided above. 
4. Trust Signals (STRICT ZERO ASSUMPTIONS): Only render numeric star ratings or review numbers if factual metrics are explicitly listed above in "Trust Signals:". If none are explicitly listed (`No numeric ratings...`), DO NOT invent, assume, or draw any fake stars, review counts, or badges on the image canvas!
5. Text and visual elements must occupy separate, distinct negative space zones. Do not overlap text onto complex background details.

--------------------------------------------------
VISUAL STYLE & MOOD
--------------------------------------------------
Overall Mood: {creative_data.get('style', 'Premium, Commercial')}
- Commercial advertising aesthetic.
- Studio lighting with soft realistic shadows.
- Utilize the extracted Background Color to establish the environment.
- High realism, crisp edges, accurate colors, and photorealistic materials.

--------------------------------------------------
CONSTRAINTS & NEGATIVE PROMPT
--------------------------------------------------
Do NOT:
- change branding or invent logos.
- use random fonts; strictly mirror the Typography Vibe & Font Style specified (`{heading_font}` + `{body_font}`).
- hallucinate extra packaging, random icons, or decorative elements.
- misspell any text (Check the Headline and CTA twice).
- crowd the image; leave ample breathing room (15% padding).

SUCCESS CRITERIA:
The final image must look like a high-converting, agency-grade social media ad that flawlessly matches the visual and tonal identity of the original website.
"""
    return brief_template.strip()

if __name__ == "__main__":
    test_json = {
        "productImages": ["img1.jpg"],
        "displayText": {"headline": "Hello", "offer": "Buy"},
        "brand": {
            "primaryColor": "#111111", 
            "secondaryColor": "#FFFFFF", 
            "accentColor": "#FF0000",
            "fontSelection": {"headlineFont": "Outfit", "bodyFont": "WorkSans"}
        },
        "style": "Minimal",
        "description": "A clean test ad",
        "referenceImage": "ref.jpg"
    }
    print(json_to_design_brief(test_json))
