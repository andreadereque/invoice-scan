import os
import json
from pathlib import Path
from time import sleep
from mindee import Client, product, PredictResponse

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ⚠️ Pega aquí tu API Key de Mindee
MINDEE_API_KEY = "24bd3a80bc82cba22803a4d6ece958c3"

# 📂 Directorios
INPUT_FOLDER = "scrips/facturas"
OUTPUT_FOLDER = "output"

# ✅ Inicializa cliente Mindee
client = Client(api_key=MINDEE_API_KEY)

# 🛠 Crea carpeta de salida si no existe
Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

# 🗂 Tipos de archivo válidos
VALID_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"]

# 🔄 Recorre todos los archivos
for filename in os.listdir(INPUT_FOLDER):
    if not any(filename.lower().endswith(ext) for ext in VALID_EXTENSIONS):
        continue

    filepath = os.path.join(INPUT_FOLDER, filename)
    print(f"📄 Procesando: {filename}...")

    try:
        input_doc = client.source_from_path(filepath)
        result: PredictResponse = client.parse(product.InvoiceV4, input_doc)

        # ✅ Extrae solo los valores simples
        prediction = result.document.inference.prediction
        fields = {
            field_name: field.value if hasattr(field, "value") else None
            for field_name, field in prediction.__dict__.items()
        }

        # 📝 Guarda el JSON anotado
        json_filename = os.path.splitext(filename)[0] + ".json"
        json_path = os.path.join(OUTPUT_FOLDER, json_filename)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(fields, f, indent=2, ensure_ascii=False)

        print(f"✅ Guardado → {json_filename}")

    except Exception as e:
        print(f"❌ Error procesando {filename}: {e}")

    sleep(1)