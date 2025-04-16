import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import fitz
import io
import re

def extract_text(file_bytes:bytes, file_type:str) ->str:
    images = []
    if file_type=="pdf":
        images=convert_from_bytes(file_bytes)
    else:
        image=Image.open(io.BytesIO(file_bytes))
        images=[image]
    text =""
    for img in images:
        ocr_result = pytesseract.image_to_string(img, lang='eng+spa')
        text+=ocr_result + "\n"
    fields = extract_fields_from_text(text)

    return {
        "raw_text": text,
        "extracted_fields": fields
    }


def extract_fields_from_text(text: str) -> dict:
    
    patterns = {
    "invoice_number": r"Número de la factura:\s*(ES-\d{10,}-\d{4}-\d)",
    "total_amount": r"TOTAL:\s*EUR\s*([\d.,]+)",
    "date": r"Fecha de la factura:\s*(\d{2}\.\d{2}\.\d{4})"
    }


    result = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        result[key] = match.group(1) if match else None

    return result
