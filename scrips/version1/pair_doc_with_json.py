import os
import shutil
import json

# Rutas de tus carpetas

carpeta_docs = "scrips/facturas"      
carpeta_json = "output"
carpeta_destino = "data/labeled"
carpeta_rechazados= "data/unlabeled"
# Crear carpetas si no existen
os.makedirs(carpeta_destino, exist_ok=True)
os.makedirs(carpeta_rechazados, exist_ok=True)

# Listamos archivos
archivos_docs = os.listdir(carpeta_docs)
archivos_json = os.listdir(carpeta_json)

# Nombres sin extensión
nombres_docs = {os.path.splitext(f)[0]: f for f in archivos_docs if os.path.isfile(os.path.join(carpeta_docs, f))}
nombres_json = {os.path.splitext(f)[0]: f for f in archivos_json if os.path.isfile(os.path.join(carpeta_json, f))}

# Emparejamos nombres comunes
nombres_comunes = set(nombres_docs.keys()) & set(nombres_json.keys())
nombres_solo_docs = set(nombres_docs.keys()) - set(nombres_json.keys())

# Procesar los que tienen pareja JSON
for nombre in nombres_comunes:
    path_json = os.path.join(carpeta_json, nombres_json[nombre])
    path_doc = os.path.join(carpeta_docs, nombres_docs[nombre])

    try:
        with open(path_json, "r", encoding="utf-8") as f:
            datos = json.load(f)

        if all(datos.get(campo) not in [None, "", []] for campo in ["total_amount", "invoice_number", "date"]):
            # ✅ Copiar a carpeta destino si JSON válido
            shutil.copy(path_json, carpeta_destino)
            shutil.copy(path_doc, carpeta_destino)
        else:
            # ❌ JSON incompleto → solo copiar el documento a rechazados
            shutil.copy(path_doc, carpeta_rechazados)
            print(f"⚠️ Incompleto: {nombres_json[nombre]}")

    except Exception as e:
        print(f"❌ Error leyendo {nombres_json[nombre]}: {e}")
        shutil.copy(path_doc, carpeta_rechazados)

# Procesar los docs que no tienen pareja JSON
for nombre in nombres_solo_docs:
    path_doc = os.path.join(carpeta_docs, nombres_docs[nombre])
    shutil.copy(path_doc, carpeta_rechazados)
    print(f"📄 Sin JSON: {nombres_docs[nombre]}")