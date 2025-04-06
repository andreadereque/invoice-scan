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
def es_formato_amazon(path):
    try:
        text = ocr_from_pdf(path) if path.endswith('.pdf') else ocr_from_image(path)
        return "Amazon Services Europe" in text and bool(re.search(
            r"\b(Total|TOTAAL|TOTAL|GESAMT|Łączna)\b", text, re.IGNORECASE
        ))
    except:
        return False

def procesar_amazon_factura(path):
    text = ocr_from_pdf(path) if path.endswith('.pdf') else ocr_from_image(path)

    # Número de factura o nota de crédito
    match_n_factura = re.search(
        r"(?:N[úu]mero de (?:nota de cr[eé]dito|factura)|Factuurnummer|Invoice No\.?|Num[eé]ro de facture|"
        r"Fattura n[°º]:?|Rechnungsnr|numer faktury)[:\s]*([A-Z0-9\-\/]+)",
        text, re.IGNORECASE)
    n_factura = match_n_factura.group(1) if match_n_factura else "NaN"

    # Fecha de emisión
    match_fecha = re.search(
        r"(?:Fecha de la factura|Fecha de emisión de la nota de crédito|Factuurdatum|Date de la facture|"
        r"Data fattura|Rechnungsdatum|data faktury)[:\s]*(\d{2}/\d{2}/\d{4})",
        text, re.IGNORECASE)
    fecha = match_fecha.group(1) if match_fecha else "NaN"

    # Capturar todos los valores que podrían ser totales
    posibles_totales = re.findall(
        r"(-?\s*(?:EUR|PLN|€)?\s*[\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))", text, re.IGNORECASE)

    total_valor = "NaN"
    moneda = "NaN"

    if posibles_totales:
        # Elegimos el total más al final (el último en aparecer)
        raw_total = posibles_totales[-1]
        moneda_match = re.search(r"(EUR|PLN|€)", raw_total)
        moneda = moneda_match.group(1) if moneda_match else "EUR"
        total_valor = normalizar_numero(raw_total)


    return {
        "archivo": os.path.basename(path),
        "fecha": fecha,
        "proveedor": "Amazon Services Europe S.à r.l.",
        "total": total_valor,
        "moneda": moneda,
        "producto": "NaN",
        "descripcion": "Factura o nota de crédito Amazon",
        "n_factura": n_factura,
        "fiabilidad": 1.0,
        "estado": "OK"
    }
def normalizar_numero(texto):
    texto = texto.strip().replace("−", "-")
    texto = texto.replace(" ", "").replace("€", "").replace("EUR", "").replace("PLN", "")

    if "." in texto and "," in texto:
        # 1.234,56 → 1234.56
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto and not "." in texto:
        # 123,45 → 123.45
        texto = texto.replace(",", ".")
    # else: 1234.56 → se queda igual

    try:
        return round(float(texto), 2)
    except:
        return "NaN"
def es_formato_openai(path):
    try:
        text = ocr_from_pdf(path) if path.endswith('.pdf') else ocr_from_image(path)
        return "OpenAI" in text and "ChatGPT Plus" in text
    except:
        return False

def procesar_openai_factura(path):
    text = ocr_from_pdf(path) if path.endswith('.pdf') else ocr_from_image(path)

    # Número de factura
    match_n_factura = re.search(r"Invoice number[:\s]*([A-Z0-9\-]+)", text, re.IGNORECASE)
    n_factura = match_n_factura.group(1) if match_n_factura else "NaN"

    # Fecha de emisión
    match_fecha = re.search(r"Date of issue[:\s]*(\w+\s\d{1,2},\s\d{4})", text, re.IGNORECASE)
    fecha = match_fecha.group(1) if match_fecha else "NaN"

    # Total
    match_total = re.search(r"Total[:\s]*\$([\d.,]+)", text)
    total_valor = normalizar_numero(match_total.group(1)) if match_total else "NaN"
    moneda = "USD"

    return {
        "archivo": os.path.basename(path),
        "fecha": fecha,
        "proveedor": "OpenAI, LLC",
        "total": total_valor,
        "moneda": moneda,
        "producto": "ChatGPT Plus",
        "descripcion": "Suscripción mensual",
        "n_factura": n_factura,
        "fiabilidad": 1.0,
        "estado": "OK"
    }
