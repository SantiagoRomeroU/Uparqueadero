import pandas as pd
import mysql.connector

# Leer Excel
df = pd.read_excel("datos.xlsx")

# Conectar a MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="tu_password",
    database="parqueadero_unimonserrate"
)
cursor = conn.cursor()

# Mapeo de valores de Excel a ENUM de MySQL
map_pago = {
    "gratis": "exento",
    "mensualidad": "pagado",
    "pago": "pagado",
    "pendiente": "pendiente"
}

# Insertar registros
for _, row in df.iterrows():
    estado_pago = map_pago.get(str(row["Estado_pago"]).lower(), "pendiente")
    cursor.execute("""
        INSERT INTO usuarios (documento, nombre, correo, rol, tipo_vehiculo, placa, hora_ingreso, estado_pago, hora_salida)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        row["Documento"], row["Nombre"], row.get("Correo",""),
        row["Rol"], row["Tipo_vehículo"], row["Placa"],
        row["Hora_ingreso"], estado_pago, row.get("Hora de salida", None)
    ))

conn.commit()
cursor.close()
conn.close()

