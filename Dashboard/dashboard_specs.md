# Frontend Requirements & Integration Guidelines
**Project**: BloomX ImaGEN Dashboard  
**Status**: Ready for Frontend Implementation  
**Backend Framework**: Python (Scraping + Creative LLM Engine)

---

## 1. Core API Schema Specifications

The frontend must support loading, editing, and exporting the following ad creative JSON structure containing a dedicated `"ingredients"` block for brand assets:

```json
{
  "ingredients": {
    "logoUrl": "https://example.com/logo.png",
    "brandColors": {
      "primaryColor": "#HEXVAL",
      "secondaryColor": "#HEXVAL",
      "accentColor": "#HEXVAL"
    },
    "fonts": {
      "headlineFont": "FontName",
      "bodyFont": "FontName"
    },
    "productImages": [
      "https://example.com/image1.jpg",
      "https://example.com/image2.jpg"
    ],
    "referenceImage": "https://example.com/ref.jpg"
  },
  "displayText": {
    "headline": "Campaign Main Title",
    "offer": "PRIMARY VALUE PROPOSITION",
    "subheading": "Supporting tagline text",
    "date": "Timeline/Availability",
    "footer": "Terms, conditions, or brand markers"
  },
  "style": "aesthetic keywords describing mood",
  "description": "Art direction details for the image generator"
}
```

---

## 2. Interactive Editing Requirements

1. **Brand Ingredients Section**: The dashboard must feature a dedicated panel allowing users to visually inspect and change the parsed website ingredients before or after creative generation:
   - **Logo Uploader**: A drag-and-drop uploader or URL input field to change `ingredients.logoUrl`.
   - **Color Pickers**: Visual color wheels mapped to `ingredients.brandColors.primaryColor`, `secondaryColor`, and `accentColor`.
   - **Font Selectors**: Dropdown menus to select standard fonts for `ingredients.fonts.headlineFont` and `bodyFont`.
   - **Product Image Gallery**: Interactive grid where users can delete, re-order, or upload new images to the `ingredients.productImages` array.
   - **Reference Image Selector**: Uploader or URL input field to edit the `ingredients.referenceImage`.
2. **Text In-Line Editing**: Users should be able to modify the fields inside `displayText` and see the visual preview update in real-time.
3. **Font Selection Dropdown**: Provide the user with options to change `fontSelection.headlineFont` and `fontSelection.bodyFont` from the standard list:
   - `Italiana` (Luxury Serif)
   - `Outfit` (Modern Sans-serif)
   - `Tektur` (Tech Geometric)
   - `BigShoulders` (Bold Condensed)
   - `Lora` / `WorkSans` / `GeistMono` (Body pairings)

---

## 3. Visual Rendering & Preview Canvas (Important)

Before calling the final GPT Image 2 API, the dashboard should show a **real-time HTML5 Canvas or CSS Mockup preview** of the ad:
- **Structure**: Render a container matching the targeted aspect ratio (1:1, 4:5, or 9:16).
- **Text Layout**:
  - The upper 40% of the box displays the `displayText.headline` (bold, dominant), `displayText.offer` (largest size), and `displayText.subheading` in the selected headline font.
  - The bottom 60% contains the product image cutouts positioned side-by-side or stacked over a clean background utilizing the extracted `brand.primaryColor` and subtle gradients.
- **Underlay/Negative Space**: Text must be overlayed on clean negative space to ensure contrast, with a minimum 15% padding from the canvas edges.

---

## 4. Bulk Generation & Export Action

- **100 Creatives Grid**: Render the generated ad configurations in a paginated card grid sorted by marketing angles (AIDA, PAS, BAB, Testimonial, etc.).
- **Copy Design Brief**: Provide a copy-to-clipboard action that converts the JSON to the formatted GPT Image 2 Text prompt using the endpoint or the `prompt_converter.js` translation library.
- **Export to CSV/Airtable**: A bulk export action that saves the selected ad configs for ad platform uploads.
