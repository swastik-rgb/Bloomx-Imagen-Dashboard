---
name: brand-asset-extractor
description: Identifies, scrapes, filters, and catalogs high-quality product and service image URLs from a target brand website. Use this skill to gather product photos and reference images for ad creatives.
---

# Brand Asset Extractor

This skill is responsible for discovering, filtering, and organizing product/service image URLs from a brand's website.

---

## WORKFLOW

### Step 1: Execute Python Scraping Utility
Rather than parsing raw HTML manually (saving token usage), utilize programmatic scripts (like `scraper.py`) or inspect the DOM structure. Discover image tags:
- `<img>` sources
- `srcset` high-resolution links
- Open Graph image metadata tags (`meta property="og:image"`)
- CDN links (e.g. Shopify, WordPress upload directories)

### Step 2: Programmatic Filtering & Cleanup
Apply deterministic filters to remove background noise and assets:
- **Discard Banners & UI Icons**: Ignore any images containing keywords like `logo`, `banner`, `arrow`, `cart`, `icon`, `loader`, `avatar`, or `badge` in their source paths or alt descriptions.
- **Filter Inline base64**: Remove raw base64 data URIs (`data:image/...;base64,...`) and mark them as placeholders.
- **Convert Relative Links**: Ensure all relative paths (e.g. `/uploads/image.jpg`) are joined with the website's base domain to create absolute, copy-pasteable URLs (e.g. `https://brand.com/uploads/image.jpg`).

### Step 3: Output Assets List
Generate a clean markdown list of verified absolute product images and a primary reference image:

```markdown
# Extracted Assets: [Brand Name]

## Product Images:
- [Absolute URL 1]
- [Absolute URL 2]

## Reference Image:
- [Absolute URL]
```
