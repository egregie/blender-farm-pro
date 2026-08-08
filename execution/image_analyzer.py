import os
import hashlib
from PIL import Image
import pytesseract

# Configure Tesseract binary path
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

def analyze_local_image(filepath):
    """
    Performs Optical Pass #2 on a local file on disk.
    Calculates exact bytes, sha256, dimensions, top 3 dominant colors, and OCR text.
    """
    filepath = os.path.abspath(filepath)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "rb") as f:
        file_bytes = f.read()

    byte_size = len(file_bytes)
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    with Image.open(filepath) as img:
        width, height = img.size
        mode = img.mode
        
        # Convert to RGB for color analysis
        rgb_img = img.convert("RGB")
        
        # Resize image for fast color quantization
        small_img = rgb_img.resize((150, 150))
        quantized = small_img.quantize(colors=16)
        palette = quantized.getpalette() # [r, g, b, r, g, b, ...]
        color_counts = quantized.getcolors() # [(count, index), ...]
        
        total_pixels = 150 * 150
        sorted_counts = sorted(color_counts, key=lambda x: x[0], reverse=True)
        
        dominant_colors = []
        for count, idx in sorted_counts[:3]:
            r = palette[idx * 3]
            g = palette[idx * 3 + 1]
            b = palette[idx * 3 + 2]
            hex_color = f"#{r:02X}{g:02X}{b:02X}"
            share_pct = round((count / total_pixels) * 100.0, 1)
            dominant_colors.append({"hex": hex_color, "share_pct": share_pct})

        # Run OCR with pytesseract (--psm 3 for sparse/full page text)
        ocr_text = ""
        try:
            ocr_text = pytesseract.image_to_string(rgb_img, config="--psm 3")
        except Exception as e:
            ocr_text = ""

    return {
        "sha256": sha256_hash,
        "bytes": byte_size,
        "width": width,
        "height": height,
        "dominant_colours": dominant_colors,
        "ocr_text": ocr_text
    }

if __name__ == "__main__":
    test_path = "Reference Templates/02_T1_SMALL_Cialis/raw_cialis_front.png"
    if os.path.exists(test_path):
        res = analyze_local_image(test_path)
        print("Analysis result for baseline Cialis image:")
        print(f"  SHA256: {res['sha256']}")
        print(f"  Bytes: {res['bytes']}")
        print(f"  Dimensions: {res['width']}x{res['height']}")
        print(f"  Colors: {res['dominant_colours']}")
        print(f"  OCR Sample: {res['ocr_text'][:100]!r}")
