import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

image = Image.open("test_images/fictional_id.png")

text = pytesseract.image_to_string(image)

print("----- OCR RESULT -----")
print(text)
print("----------------------")