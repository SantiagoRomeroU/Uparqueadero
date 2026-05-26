import pandas as pd
from App import app, db, Usuario
from datetime import datetime
import re

def parsear_fecha(valor):
    """Convierte cualquier formato de fecha a un objeto datetime"""
    if pd.isna(valor) or valor is None:
        return None
    
    if hasattr(valor, 'to_pydatetime'):
        return valor.to_pydatetime()
    
    if isinstance(valor, datetime):
        return valor
    
    valor_str = str(valor).strip()
    valor_str = valor_str.replace('\xa0', ' ')
    valor_str = re.sub(r'p\.\s*m\.', 'PM', valor_str, flags=re.IGNORECASE)
    valor_str = re.sub(r'a\.\s*m\.', 'AM', valor_str, flags=re.IGNORECASE)
    
    formatos = [
        '%d/%m/%Y %I:%M:%S %p',
        '%d/%m/%Y %H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%d/%m/%Y %H:%M',
        '%Y-%m-%d',
    ]
    
    for fmt in formatos:
        try:
            return datetime.strptime(valor_str, fmt)
        except ValueError:
            continue
    
    print(f"⚠️  No se pudo parsear la fecha: {valor_str}")
    return None


def migrar_excel(ruta_excel):
    """Lee el Excel y migra los datos a SQLite"""

    print("📂 Leyendo archivo Excel...")
    df = pd.read_excel(ruta_excel, header=0)
    df.columns = df.columns.str.strip()

    map_pago = {
        "gratis"      : "exento",
        "mensualidad" : "pagado",
        "pago"        : "pagado",
        "pendiente"   : "pendiente",
        "exento"      : "exento"
    }

    insertados = 0
    omitidos   = 0

    with app.app_context():
        for _, row in df.iterrows():
            documento = int(row["documento"])

            existente = Usuario.query.filter_by(documento=documento).first()
            if existente:
                print(f"⚠️  Ya existe: {documento}")
                omitidos += 1
                continue

            estado_pago = "pendiente"
            if pd.notna(row.get("estado_pago")):
                estado_pago = map_pago.get(
                    str(row["estado_pago"]).strip().lower(),
                    "pendiente"
                )

            tipo_vehiculo = str(row["tipo_vehiculo"]).strip().lower()
            if tipo_vehiculo == "bicicleta":
                estado_pago = "exento"

            correo = None
            if pd.notna(row.get("correo")):
                correo = str(row["correo"]).strip()

            hora_ingreso = parsear_fecha(row.get("hora_ingreso")) or datetime.utcnow()
            hora_salida  = parsear_fecha(row.get("hora_salida"))

            nuevo = Usuario(
                documento     = documento,
                nombre        = str(row["nombre"]).strip(),
                correo        = correo,
                rol           = str(row["rol"]).strip(),
                tipo_vehiculo = tipo_vehiculo,
                placa         = str(row["placa"]).strip().upper(),
                hora_ingreso  = hora_ingreso,
                hora_salida   = hora_salida,
                estado_pago   = estado_pago
            )

            db.session.add(nuevo)
            print(f"✅ Insertado: {documento} - {row['nombre']}")
            insertados += 1

        db.session.commit()
        print(f"\n🎉 Migración completada: {insertados} insertados, {omitidos} omitidos")


if __name__ == '__main__':
    ruta = input("📁 Escribe la ruta completa del archivo Excel: ")
    migrar_excel(ruta)
