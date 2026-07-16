---
name: ad-json-generator
description: Takes brand profiles, target audiences, and product image links, and generates a structured JSON payload for ad creatives matching the backend schema. Use this skill when mapping marketing concepts to structured JSON payloads.
---

# Ad JSON Generator

This skill is responsible for generating structured JSON configurations that outline the copy, colors, typography, layout style, and assets for an ad campaign.

---

## WORKFLOW

### Step 1: Brainstorm Marketing Angles
Formulate the copy and structure for the campaign using recognized marketing frameworks:
- **AIDA**: Attention hook, Interest builder, Desire booster, Call to Action.
- **PAS**: Problem identification, Agitate the problem, Solution presentation.
- **BAB**: Before state, After state, Bridge solution.
- **Social Proof**: Highlighting metrics, testimonials, or awards.
- **Feature Focus**: Deep-dive into materials, smart elements, or craftsmanship.

### Step 2: Assemble JSON Payload
Create a valid JSON object matching this exact schema:

```json
{
  "productImages": [
    "{{PRODUCT_IMAGE_1_URL}}",
    "{{PRODUCT_IMAGE_2_URL}}"
  ],
  "displayText": {
    "headline": "{{HEADLINE}}",
    "offer": "{{OFFER}}",
    "subheading": "{{SUBHEADING}}",
    "date": "{{DATE}}",
    "footer": "{{FOOTER_OR_T&C}}"
  },
  "brand": {
    "primaryColor": "{{PRIMARY_COLOR_HEX}}",
    "secondaryColor": "{{SECONDARY_COLOR_HEX}}",
    "accentColor": "{{ACCENT_COLOR_HEX}}",
    "fontSelection": {
      "headlineFont": "{{HEADLINE_FONT}}",
      "bodyFont": "{{BODY_FONT}}"
    }
  },
  "style": "{{STYLE_KEYWORDS}}",
  "description": "{{CAMPAIGN_DESCRIPTION_AND_PRODUCT_CONTEXT}}",
  "referenceImage": "{{REFERENCE_IMAGE_URL}}"
}
```
Ensure all color hex codes, font options, and image URLs are strictly populated from the upstream Analyzer and Extractor results.
