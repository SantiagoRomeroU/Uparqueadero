from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="parqueadero_unimonserrate"
    )

# Registrar usuario
@app.route('/usuarios', methods=['POST'])
def registrar_usuario():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    sql = """
    INSERT INTO usuarios (documento, nombre, correo, rol, tipo_vehiculo, placa, hora_ingreso, estado_pago, hora_salida)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON DUPLICATE KEY UPDATE
        nombre=VALUES(nombre),
        correo=VALUES(correo),
        rol=VALUES(rol),
        tipo_vehiculo=VALUES(tipo_vehiculo),
        placa=VALUES(placa),
        hora_ingreso=VALUES(hora_ingreso),
        estado_pago=VALUES(estado_pago),
        hora_salida=VALUES(hora_salida)
    """
    cursor.execute(sql, (
        data["documento"], data["nombre"], data.get("correo",""),
        data["rol"], data["tipo_vehiculo"], data["placa"],
        data["hora_ingreso"], data["estado_pago"], data.get("hora_salida", None)
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"mensaje": "Usuario registrado/actualizado correctamente"}), 201

# Consultar usuarios
@app.route('/usuarios', methods=['GET'])
def listar_usuarios():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios")
    usuarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(usuarios)

# Consultar por documento
@app.route('/usuarios/<int:documento>', methods=['GET'])
def obtener_usuario(documento):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE documento=%s", (documento,))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    if usuario:
        return jsonify(usuario)
    return jsonify({"error": "Usuario no encontrado"}), 404

# Eliminar usuario
@app.route('/usuarios/<int:documento>', methods=['DELETE'])
def eliminar_usuario(documento):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE documento=%s", (documento,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"mensaje": "Usuario eliminado"}), 200

if __name__ == '__main__':
    app.run(debug=True)

