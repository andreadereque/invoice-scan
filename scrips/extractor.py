import pytesseract
from PIL import Image
import pdfplumber
from pdf2image import convert_from_path
import re
import os

# OCR para imágenes
def ocr_from_image(path):
    image = Image.open(path)
    text = pytesseract.image_to_string(image, lang='spa+fra+eng+deu+nld+swe+ita+por')
    return text

# OCR para PDFs con OCR complementario
def ocr_from_pdf(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    images = convert_from_path(path)
    for image in images:
        text += pytesseract.image_to_string(image, lang='spa+fra+eng+deu+nld+swe+ita+por') + "\n"

    return text

# Normalizar números monetarios
def normalizar_numero(texto):
    if texto is None:
        return None
    if not isinstance(texto, str):
        texto = str(texto)

    texto = texto.strip().replace("−", "-")
    texto = texto.replace(" ", "").replace("€", "").replace("EUR", "").replace("PLN", "").replace("USD", "")

    if "." in texto and "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")

    try:
        return round(float(texto), 2)
    except:
        return None

# Extraer campos principales
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
            r"\d{1,2}\s+(de\s+)?[a-zA-Z]+\s+\d{4}", r"[A-Z][a-z]+\s\d{1,2},\s\d{4}",
            r"DATA FACTURA[:\s]*(\d{2}/\d{2}/\d{2,4})", r"Date[:\s]*(\d{4}[./-]\d{2}[./-]\d{2})"
        ],
        "proveedor": [
            r"NOM FISCAL[:\s]*(.+)", r"(?i)Nombre del proveedor[:\s]*(.+)",
            r"(?i)Vendido por[:\s]*(.+)", r"(?i)Sold By[:\s]*(.+)",
            r"(?i)Proveedor[:\s]*(.+)", r"(?i)Client[:\s]*(.+)"
        ],
        "total": [
            r"TOTAL FACTURA[:\s]*([\d.,]+)", r"(?i)Total[:\s€$]*([\-\d.,]+)",
            r"(?i)Importe Total[:\s€$]*([\-\d.,]+)", r"(?i)Amount Due[:\s€$]*([\-\d.,]+)",
            r"(?i)Grand Total[:\s€$]*([\-\d.,]+)", r"\$([\d.,]+)\s*(USD)?",
            r"Amount\s*\(USD\)[\s:]*\$?([\d.,]+)", r"Gesamtbetrag[:\s]*([\d.,\-]+)",
            r"Importo\s*totale[:\s]*([\d.,\-]+)", r"Totaalbedrag[:\s]*([\d.,\-]+)",
            r"Montant\s*total[:\s]*([\d.,\-]+)"
        ],
        "producto": [
            r"(?i)(ALTAVOZ|CASCO|AURICULARES|PIZARRA|BUFFET|COCACOLA|DETOX|CHAMP[ÚU]|SUSHI|ZAPATILLA|CAMISETA|LÁMPARA).*"
        ],
        "descripcion": [
            r"(?i)Descripción[:\s]*(.+)", r"(?i)CONCEPTE\s*(.*?)\n",
            r"(?i)Motif[:\s]*(.+)", r"(?i)Item[:\s]*(.+)", r"(?i)Servei.*?[\n:]",
            r"(?i)(Comisión.*?|Detox.*?|Auriculares.*?|Sushi.*?|Capsulas.*?)\n"
        ],
        "n_factura": [
            r"(?i)Factura[\s\-:]*[Nnº]*[:\s]*([\w\-\/]+)", r"(?i)NUMERO FACTURA[:\s]*([A-Z0-9\-\/]+)",
            r"(?i)Invoice (No\.?|number)?[:\s]*([A-Z0-9\-\/]+)", r"Nº[:\s]*([\w\-\/]+)",
            r"(?i)Reference[:\s]*([\w\-\/]+)", r"(?i)Rechnungsnummer[:\s]*([\w\-\/]+)",
            r"(?i)Fattura\s*n[oº]?[.:\s]*([A-Z0-9\-\/]+)", r"(?i)Factuur\s*nr[:.\s]*([A-Z0-9\-\/]+)",
            r"(?i)Order ID[:\s]*([A-Z0-9\-\/]+)", r"(?i)Order Number[:\s]*([A-Z0-9\-\/]+)",
            r"(?i)Transaction ID[:\s]*([A-Z0-9\-\/]+)"
        ]
    }

    campos = {campo: match(pats) for campo, pats in patterns.items()}

    if campos["total"] == "NaN":
        for line in text.splitlines():
            if re.search(r"(total|importe|amount due|totaal|montant|gesamt)", line, re.IGNORECASE):
                posibles = re.findall(r"[\-]?\d+[.,]\d{2}", line)
                if posibles:
                    campos["total"] = posibles[-1]
                    break

    if campos["total"] == "NaN":
        numeros = re.findall(r"[\-]?\d+[.,]\d{2}", text)
        posibles_totales = [normalizar_numero(n) for n in numeros]
        if posibles_totales:
            campos["total"] = max([x for x in posibles_totales if x is not None], default="NaN")

    if campos["n_factura"] == "NaN":
        match = re.search(r"\b\d{15,}\b", text)
        if match:
            campos["n_factura"] = match.group(0)

    if campos["proveedor"] == "NaN":
        if "Amazon" in text:
            campos["proveedor"] = "Amazon Services Europe S.à r.l."
        elif "Alibaba" in text:
            campos["proveedor"] = "Alibaba.com Singapore E-Commerce Private Ltd."
        elif "Temu" in text:
            campos["proveedor"] = "Whaleco Technology Limited"

    campos["total"] = normalizar_numero(campos["total"]) if campos["total"] != "NaN" else "NaN"
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
    campos.update({
        "archivo": os.path.basename(path),
        "fiabilidad": fiabilidad,
        "estado": estado
    })

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
   # Segunda pasada para completar campos vacíos

    # n_factura adicional
    if campos["n_factura"] == "NaN":
        match = re.search(r"Invoice No[:\s]*([A-Z0-9\-]+)", text, re.IGNORECASE)
        if match:
            campos["n_factura"] = match.group(1)

    # fecha adicional
    if campos["fecha"] == "NaN":
        match = re.search(r"Date[:\s]*(\d{4}[./-]\d{2}[./-]\d{2})", text, re.IGNORECASE)
        if match:
            campos["fecha"] = match.group(1)

    # total adicional (último valor en USD o monto mayor en dólares)
    if campos["total"] == "NaN":
        posibles = re.findall(r"\$([\d.,]+)", text)
        if posibles:
            try:
                convert = lambda x: float(x.replace(',', '').replace('.', '.', 1))
                campos["total"] = max(posibles, key=convert)
            except:
                pass

    # proveedor adicional
    if campos["proveedor"] == "NaN" and "Shantou Shuoyin Technology" in text:
        campos["proveedor"] = "Shantou Shuoyin Technology Co., Ltd"


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
    if texto is None:
        return None
    if not isinstance(texto, str):
        texto = str(texto)

    texto = texto.strip().replace("−", "-")
    texto = texto.replace(" ", "").replace("€", "").replace("EUR", "").replace("PLN", "").replace("USD", "")

    if "." in texto and "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto and not "." in texto:
        texto = texto.replace(",", ".")
    
    try:
        return round(float(texto), 2)
    except:
        return None

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
def es_formato_alibaba(path):
    try:
        text = ocr_from_pdf(path) if path.endswith('.pdf') else ocr_from_image(path)
        return "Alibaba.com Singapore E-Commerce" in text and "Invoice No." in text
    except:
        return False
def procesar_alibaba_factura(path):
    text = ocr_from_pdf(path) if path.endswith('.pdf') else ocr_from_image(path)

    # Número de factura
    match_n_factura = re.search(r"Invoice No\.?\s*[:：]?\s*([A-Z0-9_\-/]+)", text, re.IGNORECASE)
    n_factura = match_n_factura.group(1) if match_n_factura else "NaN"

    # Fecha
    match_fecha = re.search(r"Invoice Date\s*[:：]?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text)
    fecha = match_fecha.group(1) if match_fecha else "NaN"

    # Total
    match_total = re.search(r"Amount\s*Due\s*[:：]?\s*([\d.,]+)\s*USD", text)
    total_valor = normalizar_numero(match_total.group(1)) if match_total else "NaN"
    moneda = "USD"

    return {
        "archivo": os.path.basename(path),
        "fecha": fecha,
        "proveedor": "Alibaba.com Singapore E-Commerce Private Ltd.",
        "total": total_valor,
        "moneda": moneda,
        "producto": "NaN",
        "descripcion": "Servicio Alibaba",
        "n_factura": n_factura,
        "fiabilidad": 1.0,
        "estado": "OK"
    }

