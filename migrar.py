import pandas as pd
import mysql.connector

df = pd.read_excel(
    "C:/Users/USUARIO/OneDrive/Documentos/Proyecto Final sistemas operativos/datos.xlsx",
    header=0
)

df.columns = df.columns.str.strip()

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="parqueadero_unimonserrate"
)

cursor = conn.cursor()

cursor.execute("SELECT documento FROM usuarios")

documentos_existentes = [
    fila[0] for fila in cursor.fetchall()
]

map_pago = {
    "gratis": "exento",
    "mensualidad": "pagado",
    "pago": "pagado",
    "pendiente": "pendiente"
}

for _, row in df.iterrows():

    documento = int(row["documento"])

    if documento in documentos_existentes:

        print(f"Documento ya existe: {documento}")

        continue

    estado_pago = "pendiente"

    if pd.notna(row["estado_pago"]):

        estado_pago = map_pago.get(
            str(row["estado_pago"]).strip().lower(),
            "pendiente"
        )

    correo = "sin_correo@unimonserrate.edu.co"

    if pd.notna(row["correo"]):

        correo = str(row["correo"]).strip()

    hora_salida = None

    if pd.notna(row["hora_salida"]):

        hora_salida = row["hora_salida"]

    cursor.execute("""

        INSERT INTO usuarios (

            documento,
            nombre,
            correo,
            rol,
            tipo_vehiculo,
            placa,
            hora_ingreso,
            estado_pago,
            hora_salida

        )

        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)

    """, (

        documento,

        str(row["nombre"]).strip(),

        correo,

        str(row["rol"]).strip(),

        str(row["tipo_vehiculo"]).strip(),

        str(row["placa"]).strip().upper(),

        row["hora_ingreso"],

        estado_pago,

        hora_salida

    ))

    print(f"Usuario insertado: {documento}")

conn.commit()

cursor.close()
conn.close()

print("Migración completada correctamente")
