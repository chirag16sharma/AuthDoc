"""Quick CLI test: python test_ocr.py path/to/image.jpg [doc_type]"""
import sys
import json
from modules.ocr import extract_document

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python test_ocr.py <image_path> [doc_type: passport|visa|national_id|auto]")
        sys.exit(1)
    path = sys.argv[1]
    hint = sys.argv[2] if len(sys.argv) > 2 else "auto"
    result = extract_document(path, hint)
    print(json.dumps(result, indent=2))
