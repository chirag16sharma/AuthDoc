from PIL import Image, ImageDraw, ImageFont

image = Image.new("RGB", (1200, 700), "white")
draw = ImageDraw.Draw(image)

font = ImageFont.truetype("arial.ttf", 42)
small_font = ImageFont.truetype("arial.ttf", 30)

draw.text((80, 70), "FICTIONAL IDENTITY DOCUMENT", fill="black", font=font)

draw.text((100, 180), "Name: Ava Mehta", fill="black", font=small_font)
draw.text((100, 250), "DOB: 18 Aug 2005", fill="black", font=small_font)
draw.text((100, 320), "Document No: DEMO-AV-48291", fill="black", font=small_font)
draw.text((100, 390), "Valid Until: 18 Aug 2030", fill="black", font=small_font)

draw.text(
    (100, 500),
    "SYNTHETIC TEST DOCUMENT - NOT A REAL ID",
    fill="black",
    font=small_font
)

image.save("test_images/fictional_id.png")

print("Test document created successfully!")