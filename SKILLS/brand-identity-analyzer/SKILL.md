---
name: brand-identity-analyzer
description: Analyzes optimized text and style guides of a brand website to deduce brand colors, styling, tone of voice, and visual mood keywords. Use this skill when starting a new ad creative campaign for a website to set up standard brand guidelines.
---

# Brand Identity Analyzer

This skill is responsible for analyzing a brand's core identity (colors, fonts, tone of voice, and visual style keywords) based on optimized metadata or text content scraped from their website homepage.

---

## WORKFLOW

### Step 1: Analyze Website Content
Analyze the provided website summary, title, header tags, and styling configurations. Extract:
- **Brand Colors**: Find the dominant brand colors and determine the exact HEX values for:
  - `primaryColor` (dominant background or brand color)
  - `secondaryColor` (primary typography or high-contrast element)
  - `accentColor` (active buttons, highlights, or distinct markers)
- **Tone & Mood**: Delineate the brand's tone of voice (e.g. empathetic, aggressive, luxury, professional, corporate).
- **Core Value Proposition**: Identify the main services, products, or offers sold.

### Step 2: Determine Typography Rules
Examine the brand category and match it to a standard premium font pairing from our supported library:
- **Luxury / Premium Design / Editorial**: `Italiana` (Headline) paired with `Lora` (Body).
- **Modern E-Commerce / Consumer Goods**: `Outfit` (Headline) paired with `WorkSans` (Body).
- **High-Tech / Engineering / Security**: `Tektur` (Headline) paired with `GeistMono` (Body).
- **Bold Action / Clearance Campaigns**: `BigShoulders` (Headline) paired with `WorkSans` (Body).

### Step 3: Output Brand Profile
Format the output as a clean, structured Brand Profile (markdown format) that will feed into the downstream ad generators:

```markdown
# Brand Profile: [Brand Name]

- **Primary Color**: [HEX]
- **Secondary Color**: [HEX]
- **Accent Color**: [HEX]
- **Headline Font**: [Font Name]
- **Body Font**: [Font Name]
- **Brand Mood**: [Keywords]
- **Target Audience Description**: [Short summary]
```
