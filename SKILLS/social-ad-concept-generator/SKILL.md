---
name: social-ad-concept-generator
description: Generates multiple social media ad concepts optimizing layout, margins, text sizes, and positions for different social aspect ratios (1:1, 4:5, 9:16, 16:9). Use this skill when adapting creative concepts to social media placements.
---

# Social Ad Concept Generator

This skill is responsible for adapting and optimizing layout, text sizing, and product placement coordinates for different social media ad sizes.

---

## WORKFLOW

### Step 1: Select Aspect Ratio
Identify the targeted social media placement format and apply the specific layout grid constraints:

#### 1. Square Format (1:1 / 1080×1080)
- **Use Case**: Feed placements (Instagram, Facebook).
- **Layout Grid**: Tight balanced vertical division.
  - Top 45%: Combined Headline & primary offer.
  - Bottom 55%: Centered product image cutout and light floor shadow.
- **Margins**: Moderate (10% padding).

#### 2. Portrait Format (4:5 / 1080×1350)
- **Use Case**: Instagram Feed / Reels preview.
- **Layout Grid**: Editorial spacing.
  - Top 40%: Bold left-aligned typography.
  - Bottom 60%: Central product stage with rich reflections.
- **Margins**: Generous (15% padding) to give breathing room.

#### 3. Story / Reel Format (9:16 / 1080×1920)
- **Use Case**: Instagram/Facebook Stories, TikTok.
- **Layout Grid**: Tall vertical stack.
  - Top 30%: Dominant Headline and offer.
  - Middle 55%: Large vertical product focus.
  - Bottom 15%: Clean Call to Action (CTA) button container and safety margins.
- **Margins**: High safety margins (15-20% padding at top and bottom to avoid interface UI overlap).

#### 4. Landscape Format (16:9 / 1920×1080)
- **Use Case**: YouTube, Web Banners, Desktop Feed.
- **Layout Grid**: Horizontal side-by-side division.
  - Left 50%: Clean typography alignment (Headline, offer, subhead).
  - Right 50%: Product showcase with organic elements and backgrounds.
- **Margins**: Left/Right margins at 12%.

### Step 2: Output Ratio-Specific Instructions
Adjust the `"style"` and `"description"` fields in the GPT Image 2 configuration payload to specify the targeted layout dimensions and spatial relationships explicitly.
