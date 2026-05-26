from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import io
import re

# ─── Configuración ────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parqueadero.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'parqueadero_universidad_2024'

db = SQLAlchemy(app)


# ─── MODELOS ──────────────────────────────────────────────────────────────────

class Usuario(db.Model):
    """Representa cualquier usuario del parqueadero"""
    __tablename__ = 'usuarios'

    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    documento     = db.Column(db.BigInteger, unique=True, nullable=False)
    nombre        = db.Column(db.String(100), nullable=False)
    correo        = db.Column(db.String(100), nullable=True)
    rol           = db.Column(db.Enum('Administrador', 'Empleado', 'Estudiante', 'Visitante'), nullable=False)
    tipo_vehiculo = db.Column(db.Enum('carro', 'moto', 'bicicleta'), nullable=False)
    placa         = db.Column(db.String(20), nullable=False)
    hora_ingreso  = db.Column(db.DateTime, default=datetime.utcnow)
    hora_salida   = db.Column(db.DateTime, nullable=True)
    estado_pago   = db.Column(db.Enum('pendiente', 'pagado', 'exento'), default='pendiente')

    def calcular_estado_pago(self):
        """Estado de pago automático según tipo de vehículo"""
        if self.tipo_vehiculo == 'bicicleta':
            return 'exento'
        return 'pendiente'

    def calcular_cobro(self):
        """Calcula el cobro según el tiempo en el parqueadero"""
        if not self.hora_salida or self.estado_pago == 'exento':
            return 0
        diferencia    = self.hora_salida - self.hora_ingreso
        minutos       = diferencia.total_seconds() / 60
        tarifa_minuto = 100  # pesos colombianos por minuto
        return round(minutos * tarifa_minuto, 2)

    def to_dict(self):
        """Convierte el objeto a diccionario para respuestas JSON"""
        return {
            'id'           : self.id,
            'documento'    : self.documento,
            'nombre'       : self.nombre,
            'correo'       : self.correo,
            'rol'          : self.rol,
            'tipo_vehiculo': self.tipo_vehiculo,
            'placa'        : self.placa,
            'hora_ingreso' : self.hora_ingreso.strftime('%Y-%m-%d %H:%M:%S') if self.hora_ingreso else None,
            'hora_salida'  : self.hora_salida.strftime('%Y-%m-%d %H:%M:%S') if self.hora_salida else None,
            'estado_pago'  : self.estado_pago
        }

    def __repr__(self):
        return f'<Usuario {self.nombre} - {self.placa} - {self.rol}>'


class RegistroParqueo(db.Model):
    """Historial completo de entradas y salidas del parqueadero"""
    __tablename__ = 'registros_parqueo'

    id           = db.Column(db.Integer, primary_key=True)
    documento    = db.Column(db.BigInteger, nullable=False)
    placa        = db.Column(db.String(20), nullable=False)
    hora_entrada = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    hora_salida  = db.Column(db.DateTime, nullable=True)
    total_cobro  = db.Column(db.Float, nullable=True)
    estado_pago  = db.Column(db.String(20), default='pendiente')

    def __repr__(self):
        return f'<Registro {self.placa} - {self.hora_entrada}>'


# ─── Crear tablas ──────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()
    print("✅ Base de datos lista")


# ─── UTILIDAD: parsear fechas ─────────────────────────────────────────────────

def parsear_fecha(valor):
    """Convierte cualquier formato de fecha a un objeto datetime"""
    try:
        if pd.isna(valor) or valor is None:
            return None
    except Exception:
        pass
    if hasattr(valor, 'to_pydatetime'):
        return valor.to_pydatetime()
    if isinstance(valor, datetime):
        return valor
    valor_str = ' '.join(str(valor).strip().replace('\xa0', ' ').split())
    valor_str = re.sub(r'p\.\s*m\.', 'PM', valor_str, flags=re.IGNORECASE)
    valor_str = re.sub(r'a\.\s*m\.', 'AM', valor_str, flags=re.IGNORECASE)
    for fmt in ['%d/%m/%Y %I:%M:%S %p', '%d/%m/%Y %H:%M:%S',
                '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M', '%Y-%m-%d']:
        try:
            return datetime.strptime(valor_str, fmt)
        except ValueError:
            continue
    return None


# ─── RUTAS WEB ────────────────────────────────────────────────────────────────

@app.route('/')
def inicio():
    """Página de inicio, redirige al registro"""
    return redirect(url_for('registro'))


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    """Formulario de registro accesible por QR"""
    mensaje      = None
    tipo_mensaje = None

    if request.method == 'POST':
        nombre        = request.form.get('nombre', '').strip()
        documento     = request.form.get('documento', '').strip()
        placa         = request.form.get('placa', '').strip().upper()
        rol           = request.form.get('rol', '').strip()
        tipo_vehiculo = request.form.get('tipo_vehiculo', '').strip().lower()
        correo        = request.form.get('correo', '').strip() or None

        if not all([nombre, documento, placa, rol, tipo_vehiculo]):
            mensaje      = 'Por favor completa todos los campos obligatorios.'
            tipo_mensaje = 'error'
        else:
            existente = Usuario.query.filter_by(documento=int(documento)).first()
            if existente:
                mensaje      = f'El documento {documento} ya está registrado.'
                tipo_mensaje = 'error'
            else:
                estado_pago = 'exento' if tipo_vehiculo == 'bicicleta' else 'pendiente'
                nuevo = Usuario(
                    documento     = int(documento),
                    nombre        = nombre,
                    correo        = correo,
                    rol           = rol,
                    tipo_vehiculo = tipo_vehiculo,
                    placa         = placa,
                    estado_pago   = estado_pago
                )
                db.session.add(nuevo)
                db.session.commit()
                mensaje      = f'✅ ¡Bienvenido {nombre}! Vehículo {placa} registrado correctamente.'
                tipo_mensaje = 'exito'

    return render_template('registro.html', mensaje=mensaje, tipo_mensaje=tipo_mensaje)


@app.route('/admin')
def admin():
    """Panel de administración con todos los usuarios"""
    usuarios   = Usuario.query.all()
    pagados    = Usuario.query.filter_by(estado_pago='pagado').count()
    pendientes = Usuario.query.filter_by(estado_pago='pendiente').count()
    exentos    = Usuario.query.filter_by(estado_pago='exento').count()

    return render_template('admin.html',
        usuarios   = usuarios,
        pagados    = pagados,
        pendientes = pendientes,
        exentos    = exentos
    )


@app.route('/importar', methods=['GET', 'POST'])
def importar():
    """Sube un Excel y migra los datos directamente desde el navegador"""
    if request.method == 'GET':
        return render_template('importar.html')

    archivo = request.files.get('archivo')
    if not archivo:
        return jsonify({'error': 'No se recibió archivo'}), 400

    detalles   = []
    insertados = 0
    omitidos   = 0
    errores    = 0

    map_pago = {
        'gratis'      : 'exento',
        'mensualidad' : 'pagado',
        'pago'        : 'pagado',
        'pendiente'   : 'pendiente',
        'exento'      : 'exento'
    }

    try:
        df = pd.read_excel(io.BytesIO(archivo.read()), header=0)
        df.columns = df.columns.str.strip()

        for _, row in df.iterrows():
            try:
                documento     = int(row['documento'])
                existente     = Usuario.query.filter_by(documento=documento).first()

                if existente:
                    detalles.append({
                        'tipo'   : 'omitido',
                        'mensaje': f'⚠️ Ya existe: {documento} - {row["nombre"]}'
                    })
                    omitidos += 1
                    continue

                tipo_vehiculo = str(row['tipo_vehiculo']).strip().lower()
                estado_pago   = 'exento' if tipo_vehiculo == 'bicicleta' else map_pago.get(
                    str(row.get('estado_pago', 'pendiente')).strip().lower(), 'pendiente'
                )

                nuevo = Usuario(
                    documento     = documento,
                    nombre        = str(row['nombre']).strip(),
                    correo        = str(row['correo']).strip() if pd.notna(row.get('correo')) else None,
                    rol           = str(row['rol']).strip(),
                    tipo_vehiculo = tipo_vehiculo,
                    placa         = str(row['placa']).strip().upper(),
                    hora_ingreso  = parsear_fecha(row.get('hora_ingreso')) or datetime.utcnow(),
                    hora_salida   = parsear_fecha(row.get('hora_salida')),
                    estado_pago   = estado_pago
                )

                db.session.add(nuevo)
                db.session.commit()

                detalles.append({
                    'tipo'   : 'exito',
                    'mensaje': f'✅ Insertado: {documento} - {row["nombre"]}'
                })
                insertados += 1

            except Exception as e:
                db.session.rollback()
                detalles.append({
                    'tipo'   : 'error',
                    'mensaje': f'❌ Error en documento {row.get("documento", "?")}: {str(e)}'
                })
                errores += 1

    except Exception as e:
        return jsonify({'error': f'No se pudo leer el archivo: {str(e)}'}), 500

    return jsonify({
        'insertados': insertados,
        'omitidos'  : omitidos,
        'errores'   : errores,
        'detalles'  : detalles
    })


# ─── API REST ─────────────────────────────────────────────────────────────────

@app.route('/api/usuarios', methods=['POST'])
def api_registrar_usuario():
    """Registra un usuario nuevo o actualiza uno existente por documento"""
    data = request.json
    if not data:
        return jsonify({'error': 'No se recibieron datos'}), 400

    campos_requeridos = ['documento', 'nombre', 'rol', 'tipo_vehiculo', 'placa']
    for campo in campos_requeridos:
        if campo not in data:
            return jsonify({'error': f'Falta el campo: {campo}'}), 400

    tipo_vehiculo = str(data['tipo_vehiculo']).strip().lower()
    estado_pago   = 'exento' if tipo_vehiculo == 'bicicleta' else data.get('estado_pago', 'pendiente')
    existente     = Usuario.query.filter_by(documento=int(data['documento'])).first()

    if existente:
        existente.nombre        = data['nombre']
        existente.correo        = data.get('correo', None)
        existente.rol           = data['rol']
        existente.tipo_vehiculo = tipo_vehiculo
        existente.placa         = str(data['placa']).upper()
        existente.estado_pago   = estado_pago
        existente.hora_salida   = parsear_fecha(data.get('hora_salida'))
        db.session.commit()
        return jsonify({'mensaje': 'Usuario actualizado correctamente'}), 200
    else:
        nuevo = Usuario(
            documento     = int(data['documento']),
            nombre        = data['nombre'],
            correo        = data.get('correo', None),
            rol           = data['rol'],
            tipo_vehiculo = tipo_vehiculo,
            placa         = str(data['placa']).upper(),
            hora_ingreso  = parsear_fecha(data.get('hora_ingreso')) or datetime.utcnow(),
            hora_salida   = parsear_fecha(data.get('hora_salida')),
            estado_pago   = estado_pago
        )
        db.session.add(nuevo)
        db.session.commit()
        return jsonify({'mensaje': 'Usuario registrado correctamente'}), 201


@app.route('/api/usuarios', methods=['GET'])
def api_listar_usuarios():
    """Retorna todos los usuarios en formato JSON"""
    usuarios = Usuario.query.all()
    return jsonify([u.to_dict() for u in usuarios]), 200


@app.route('/api/usuarios/<int:documento>', methods=['GET'])
def api_obtener_usuario(documento):
    """Retorna un usuario específico por su documento"""
    u = Usuario.query.filter_by(documento=documento).first()
    if not u:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    return jsonify(u.to_dict()), 200


@app.route('/api/usuarios/<int:documento>', methods=['DELETE'])
def api_eliminar_usuario(documento):
    """Elimina un usuario por su documento"""
    u = Usuario.query.filter_by(documento=documento).first()
    if not u:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    db.session.delete(u)
    db.session.commit()
    return jsonify({'mensaje': f'Usuario {documento} eliminado correctamente'}), 200


@app.route('/api/usuarios/<int:documento>', methods=['PUT'])
def api_actualizar_pago(documento):
    """Actualiza el estado de pago de un usuario"""
    data = request.json
    u    = Usuario.query.filter_by(documento=documento).first()
    if not u:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    if u.tipo_vehiculo == 'bicicleta':
        return jsonify({'error': 'Las bicicletas son exentas, no requieren pago'}), 400
    nuevo_estado = data.get('estado_pago')
    if nuevo_estado not in ['pendiente', 'pagado']:
        return jsonify({'error': 'Estado de pago inválido'}), 400
    u.estado_pago = nuevo_estado
    db.session.commit()
    return jsonify({'mensaje': f'Estado de pago actualizado a {nuevo_estado}'}), 200


@app.route('/api/mensualidad/<int:documento>', methods=['GET'])
def api_verificar_mensualidad(documento):
    """Verifica si un miembro universitario tiene la mensualidad al día"""
    u = Usuario.query.filter_by(documento=documento).first()
    if not u:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    if u.rol == 'Visitante':
        return jsonify({'error': 'Los visitantes no tienen mensualidad'}), 400
    return jsonify({
        'documento' : u.documento,
        'nombre'    : u.nombre,
        'rol'       : u.rol,
        'estado_pago': u.estado_pago,
        'al_dia'    : u.estado_pago == 'pagado'
    }), 200


# ─── Punto de entrada ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
