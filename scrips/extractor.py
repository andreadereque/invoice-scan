# extractor.py
import pytesseract
from PIL import Image
import pdfplumber
from pdf2image import convert_from_path
import re
import os

def ocr_from_image(path):
    image = Image.open(path)
    text = pytesseract.image_to_string(image, lang='spa+fra+eng+deu+nld+swe')
    return text

def ocr_from_pdf(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    if not text.strip():
        images = convert_from_path(path)
        for image in images:
            text += pytesseract.image_to_string(image, lang='spa+fra+eng+deu+nld+swe') + "\n"
    return text

def extract_fields(text):
    def match(patterns, multiple=False):
        matches = []
        for p in patterns:
            found = re.findall(p, text, re.IGNORECASE)
            if found:
                if multiple:
                    matches.extend(found)
                else:
                    return found[0] if isinstance(found[0], str) else found[0][-1]
        return matches if multiple else "NaN"

    patterns = {
        "fecha": [
            r"\d{2}[/-]\d{2}[/-]\d{4}", r"\d{2}[.\-]\d{2}[.\-]\d{2,4}",
            r"\d{1,2}\s+(de\s+)?[a-zA-Z]+\s+\d{4}", r"[A-Z][a-z]+\s\d{1,2},\s\d{4}"
        ],
        "proveedor": [
            r"(?i)Vendido por[:\s]*(.+)", r"(?i)Sold By[:\s]*(.+)",
            r"(?i)Nombre del proveedor[:\s]*(.+)", r"(?i)Proveedor[:\s]*(.+)",
            r"(?i)Nom du fournisseur[:\s]*(.+)", r"(?i)Client[:\s]*(.+)",
            r"(?i)Bill(?:ed)? to[:\s]*(.+)",
            r"(?i)Dienstverlener[:\s]*(.+)", r"(?i)Zakelijk adres[:\s]*(.+)",
            r"(?i)Leverant[öo]r[:\s]*(.+)", r"(?i)F[öo]retagsnamn[:\s]*(.+)"
        ],
        "total": [
            r"(?i)Total factura[:\s€]*([\-\d.,]+)", r"(?i)Amount Due[:\s€]*([\-\d.,]+)",
            r"(?i)Total[:\s€]*([\-\d.,]+)", r"(?i)Importe Total[:\s€]*([\-\d.,]+)",
            r"(?i)Total Due[:\s€]*([\-\d.,]+)", r"(?i)Grand Total[:\s€]*([\-\d.,]+)",
            r"(?i)VAT Total[:\s€]*([\-\d.,]+)", r"(?i)Amount Paid[:\s€]*([\-\d.,]+)",
            r"([\-\d]{1,3}(?:[.,][\-\d]{3})*[.,][\-\d]{2})\s*(EUR|€)?"
        ],
        "producto": [
            r"(?i)(ALTAVOZ|CASCO|AURICULARES|PIZARRA|BUFFET|COCACOLA|DETOX|CHAMP[ÚU]|SUSHI|ZAPATILLA|CAMISETA|LÁMPARA).*"
        ],
        "descripcion": [
            r"(?i)Descripción[:\s]*(.+)", r"(?i)Motif[:\s]*(.+)", r"(?i)Item[:\s]*(.+)",
            r"(?i)Remboursement frais", r"(?i)Omschrijving[:\s]*(.+)",
            r"(?i)(Comisión.*?|Detox.*?|Auriculares.*?|Sushi.*?|Capsulas.*?)\n"
        ],
        "n_factura": [
            r"(?i)Factura[\s\-:]*[Nnº]*[:\s]*([\w\-\/]+)",
            r"(?i)Invoice (No\.?|number)?[:\s]*([\w\-\/]+)",
            r"(?i)Número nota de crédito[:\s]*([\w\-\/]+)",
            r"(?i)Num[eé]ro de note de cr[eé]dit[:\s]*([\w\-\/]+)",
            r"(?i)Nº[:\s]*([\w\-\/]+)", r"(?i)Reference[:\s]*([\w\-\/]+)",
            r"(?i)Ref\.?[:\s]*([\w\-\/]+)", r"(?i)Rechnungsnummer[:\s]*([\w\-\/]+)",
            r"(?i)Fakturanummer[:\s]*([\w\-\/]+)"
        ]
    }

    campos = {campo: match(pats) for campo, pats in patterns.items()}

    if campos["total"] == "NaN":
        posibles_totales = match(patterns["total"], multiple=True)
        if posibles_totales:
            try:
                convert = lambda x: float(x.replace('.', '').replace(',', '.').replace('−', '-'))
                campos["total"] = max(posibles_totales, key=convert)
            except:
                pass

    return campos

def calcular_fiabilidad(campos):
    encontrados = sum(1 for v in campos.values() if v != "NaN")
    return round(encontrados / len(campos), 2)

def determinar_estado(fiabilidad, campos):
    vacios = sum(1 for v in campos.values() if v == "NaN")
    return "Revisión manual" if fiabilidad < 0.6 or vacios >= 2 else "OK"

def procesar_archivo(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png']:
        text = ocr_from_image(path)
    elif ext == '.pdf':
        text = ocr_from_pdf(path)
    else:
        return None
    campos = extract_fields(text)
    fiabilidad = calcular_fiabilidad(campos)
    estado = determinar_estado(fiabilidad, campos)
    campos["archivo"] = os.path.basename(path)
    campos["fiabilidad"] = fiabilidad
    campos["estado"] = estado
    return campos