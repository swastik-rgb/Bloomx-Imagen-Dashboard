def json_to_design_brief(json_data):
    """
    Converts a structured JSON payload into the final formatted text design brief
    matching the GPT Image 2 Prompt Architecture.
    """
    display_text = json_data.get("displayText", {})
    ingredients = json_data.get("ingredients", {})
    brand_colors = ingredients.get("brandColors", {})
    fonts = ingredients.get("fonts", {})
    
    product_images_str = "\n".join([f"- {url}" for url in ingredients.get("productImages", [])])
    ref_image_str = f"- {ingredients.get('referenceImage')}" if ingredients.get("referenceImage") else "None provided"

    brief_template = f"""You are an expert commercial advertising designer specializing in premium Interior Design, textile, Furniture, Floor Tiles, Hospitals, Resorts, and consumer product advertisements.

Your objective is to create a professional marketing creative suitable for social media advertising, Amazon listings, websites, and paid campaigns.

--------------------------------------------------
INPUT ASSETS
--------------------------------------------------

Product Images
{product_images_str}

Reference Image
{ref_image_str}

Brand Identity
Brand Name: {json_data.get('brand_name', 'Brand')}
Core Service/Offering: {json_data.get('service', 'Commercial product or service')}

Brand Color Palette
Primary Color: {brand_colors.get('primaryColor', '#FFFFFF')}
Secondary Color: {brand_colors.get('secondaryColor', '#000000')}
Accent Color: {brand_colors.get('accentColor', '#FF0000')}

User Description
{json_data.get('description', '')}

--------------------------------------------------
TEXT TO DISPLAY
--------------------------------------------------

Display the following text EXACTLY as provided.

Headline: {display_text.get('headline', '')}
Offer: {display_text.get('offer', '')}
Footer: {display_text.get('footer', '')}

Do not rewrite.
Do not summarize.
Do not translate.
Do not add promotional text.

--------------------------------------------------
BRAND GUIDELINES
--------------------------------------------------

Primary Color: {brand_colors.get('primaryColor', '#FFFFFF')}
Secondary Color: {brand_colors.get('secondaryColor', '#000000')}
Accent Color: {brand_colors.get('accentColor', '#FF0000')}

Typography Style:
Headline Font: {fonts.get('headlineFont', 'Outfit')}
Body Font: {fonts.get('bodyFont', 'WorkSans')}
Style: Modern, Premium, Clean, Bold hierarchy

Overall Mood:
{json_data.get('style', 'Premium')}

--------------------------------------------------
PRODUCT RULES
--------------------------------------------------

Always use the provided product images.
Never redesign the packaging.
Never modify labels.
Never crop important product details.
Keep products sharp and realistic.
Use realistic reflections and shadows.
Maintain accurate proportions.
Products should remain the visual focus.

--------------------------------------------------
LAYOUT RULES
--------------------------------------------------

Maintain strong visual hierarchy using a clean modern design grid.
Separate layout zones:
- Top 40% of the canvas: Exclusively reserved for Headline, Offer, and brand metadata.
- Bottom 60% of the canvas: Reserved for product images, clean staging surfaces, and shadows.
Never overlap text elements with the product images.
Text and products must occupy separate, distinct negative space zones.
Provide ample breathing room (at least 15% margin padding on all edges).
Maintain stable, balanced composition without visual clutter.

--------------------------------------------------
TEXT LAYOUT
--------------------------------------------------

Follow these strict typography layout rules:
All text must be perfectly aligned (either clean left-alignment along a single vertical axis, or centered).
Headline must be bold and dominant.
Primary Offer must be the largest, most eye-catching text on the page.
Supporting copy must be set in a smaller, lighter font weight.
Place text only on clean, flat negative space or solid/subtle gradient backing blocks to guarantee maximum contrast and readability.
CTA (Call to Action) must be isolated at the bottom in a visible, clean rectangular container or standalone block.
Respect letter-spacing (kerning) and line-height (leading). Never warp, stretch, or distort the typography.

--------------------------------------------------
VISUAL STYLE
--------------------------------------------------

Commercial product photography
Studio lighting
Luxury advertising
Minimal composition
Soft realistic shadows
Premium gradients
Modern geometric composition
Clean negative space
High-end e-commerce aesthetic

--------------------------------------------------
BACKGROUND
--------------------------------------------------

Create a clean premium background.
Use the supplied brand colors.
Use subtle gradients.
Add depth without distracting from products.

--------------------------------------------------
REFERENCE IMAGE
--------------------------------------------------

If a reference image is supplied:
Match overall composition, visual balance, style, lighting, spacing, and graphic language.
Do NOT copy.
Do NOT recreate.
Do NOT duplicate.
Only use it as inspiration.

--------------------------------------------------
IMAGE QUALITY
--------------------------------------------------

Ultra clean
Commercial quality
High realism
Crisp edges
Accurate colors
Premium lighting
Photorealistic materials

--------------------------------------------------
CONSTRAINTS
--------------------------------------------------

Do NOT:
- change branding
- invent offers
- change product labels
- invent logos
- add watermarks
- add random icons
- add decorative elements unrelated to the product
- misspell any text
- hallucinate extra packaging

--------------------------------------------------
SUCCESS CRITERIA
--------------------------------------------------

The final creative should look like it was designed by a professional advertising agency for a premium consumer brand.
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
