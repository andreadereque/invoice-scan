# main.py
import os
import pandas as pd
from tqdm import tqdm
from extractor import (
    procesar_amazon_factura,
    procesar_openai_factura,
    procesar_alibaba_factura,
    procesar_archivo,
    es_formato_amazon,
    es_formato_openai,
    es_formato_alibaba,
    normalizar_numero
)

# Ruta a la carpeta que contiene las facturas
RUTA_FACTURAS = "scrips/facturas"
SALIDA = "output/resultados.xlsx"
LOG_ERROR = "output/errores.txt"

# Crear carpeta de salida si no existe
os.makedirs("output", exist_ok=True)
if os.path.exists(LOG_ERROR):
    os.remove(LOG_ERROR)

# Listar archivos
archivos = [f for f in os.listdir(RUTA_FACTURAS) if os.path.isfile(os.path.join(RUTA_FACTURAS, f))]
print(f"🔍 Procesando {len(archivos)} archivos...")

resultados = []
for archivo in tqdm(archivos, desc="📄 Facturas"):
    ruta_completa = os.path.join(RUTA_FACTURAS, archivo)

    try:
        if es_formato_amazon(ruta_completa):
            resultado = procesar_amazon_factura(ruta_completa)
        elif es_formato_openai(ruta_completa):
            resultado = procesar_openai_factura(ruta_completa)
        elif es_formato_alibaba(ruta_completa):
            resultado = procesar_alibaba_factura(ruta_completa)
        else:
            resultado = procesar_archivo(ruta_completa)

        if resultado:
            resultados.append(resultado)
    except Exception as e:
        with open(LOG_ERROR, "a") as f:
            f.write(f"Error procesando {archivo}: {str(e)}\n")

# Crear DataFrame y guardar Excel
if resultados:
    df = pd.DataFrame(resultados)
    df["total"] = df["total"].apply(normalizar_numero)
    df.to_excel(SALIDA, index=False)

    # Métricas
    num_validos_total = df['total'].notnull().sum()
    num_validos_factura = df['n_factura'].apply(lambda x: x != "NaN").sum()
    num_validos_ambos = df[(df['total'].notnull()) & (df['n_factura'] != "NaN")].shape[0]

    porcentaje_total = (num_validos_total / len(df)) * 100
    porcentaje_factura = (num_validos_factura / len(df)) * 100
    porcentaje_ambos = (num_validos_ambos / len(df)) * 100
    suma_total = df['total'].sum()

    print(f"\n✅ Facturas procesadas. Archivo generado en: {SALIDA}")
    print(f"💰 Suma total de importes: {suma_total:.2f}")
    print(f"\n📋 RESUMEN DE EXTRACCIÓN:")
    print(f"🔢 Total archivos procesados: {len(df)}")
    print(f"💰 Con total válido: {num_validos_total} ({porcentaje_total:.1f}%)")
    print(f"🧾 Con número de factura: {num_validos_factura} ({porcentaje_factura:.1f}%)")
    print(f"✅ Con ambos (total + nº factura): {num_validos_ambos} ({porcentaje_ambos:.1f}%)")
else:
    print("⚠️ No se encontraron facturas válidas para procesar.")