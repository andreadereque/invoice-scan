# main.py
import os
import pandas as pd
from extractor import procesar_archivo

# Ruta a la carpeta que contiene las facturas
RUTA_FACTURAS = "scrips/facturas"
SALIDA = "output/resultados.xlsx"

resultados = []

total_archivos = 0

for archivo in os.listdir(RUTA_FACTURAS):
    ruta_completa = os.path.join(RUTA_FACTURAS, archivo)
    if os.path.isfile(ruta_completa):
        total_archivos += 1
        resultado = procesar_archivo(ruta_completa)
        if resultado:
            resultados.append(resultado)

# Crear DataFrame y guardar Excel
if resultados:
    df = pd.DataFrame(resultados)
    os.makedirs("output", exist_ok=True)
    df.to_excel(SALIDA, index=False)

    # Contar valores numéricos válidos en la columna 'total'
    def es_numero(x):
        try:
            float(x.replace('.', '').replace(',', '.'))
            return True
        except:
            return False

    con_total_numerico = df['total'].apply(es_numero).sum()

    print(f"✅ Facturas procesadas. Archivo generado en: {SALIDA}")
    print(f"📊 {con_total_numerico} de {len(df)} filas tienen un valor numérico en la columna 'total'.")
else:
    print("⚠️ No se encontraron facturas válidas para procesar.")