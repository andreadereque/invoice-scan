import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.extractors.extractor import extract_text
with open("scrips/facturas/ES-2191673415-2024-4.pdf", "rb") as f:
    data = f.read()
resultado = extract_text(data, "pdf")
print("Texto crudo:")
print(resultado["raw_text"])
print("\nCampos extraídos:")
print(resultado["extracted_fields"])