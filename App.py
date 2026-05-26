from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# ─── Configuración de la aplicación ───────────────────────────────────────────

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parqueadero.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'parqueadero_universidad_2024'

db = SQLAlchemy(app)


# ─── MODELOS (clases que representan las tablas de la base de datos) ───────────

class Vehiculo(db.Model):
    """Clase base que representa cualquier vehículo en el sistema"""
    __tablename__ = 'vehiculos'

    id             = db.Column(db.Integer, primary_key=True)
    placa          = db.Column(db.String(10), unique=True, nullable=False)
    tipo_usuario   = db.Column(db.String(20), nullable=False)  # 'visitante', 'estudiante', 'profesor', 'funcionario'
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación: un vehículo puede tener muchos registros de parqueo
    registros = db.relationship('RegistroParqueo', backref='vehiculo', lazy=True)

    def __repr__(self):
        return f'<Vehiculo {self.placa} - {self.tipo_usuario}>'


class Visitante(db.Model):
    """Visitante externo a la universidad — solo necesita nombre y placa"""
    __tablename__ = 'visitantes'

    id         = db.Column(db.Integer, primary_key=True)
    nombre     = db.Column(db.String(100), nullable=False)
    placa      = db.Column(db.String(10), unique=True, nullable=False)

    def __repr__(self):
        return f'<Visitante {self.nombre} - {self.placa}>'


class MiembroUniversidad(db.Model):
    """Estudiante, profesor o funcionario de la universidad"""
    __tablename__ = 'miembros'

    id              = db.Column(db.Integer, primary_key=True)
    nombre          = db.Column(db.String(100), nullable=False)
    placa           = db.Column(db.String(10), unique=True, nullable=False)
    codigo          = db.Column(db.String(20), unique=True, nullable=False)  # código universitario
    tipo            = db.Column(db.String(20), nullable=False)  # 'estudiante', 'profesor', 'funcionario'
    correo          = db.Column(db.String(100), nullable=False)
    telefono        = db.Column(db.String(20))

    def __repr__(self):
        return f'<Miembro {self.nombre} - {self.tipo}>'


class RegistroParqueo(db.Model):
    """Representa una entrada y salida del parqueadero"""
    __tablename__ = 'registros_parqueo'

    id           = db.Column(db.Integer, primary_key=True)
    placa        = db.Column(db.String(10), nullable=False)
    hora_entrada = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    hora_salida  = db.Column(db.DateTime, nullable=True)   # None = sigue adentro
    total_cobro  = db.Column(db.Float, nullable=True)      # None = aún no se calcula
    vehiculo_id  = db.Column(db.Integer, db.ForeignKey('vehiculos.id'), nullable=False)

    def calcular_cobro(self):
        """Calcula cuánto debe pagar según el tiempo que estuvo"""
        if not self.hora_salida:
            return None
        diferencia    = self.hora_salida - self.hora_entrada
        minutos       = diferencia.total_seconds() / 60
        tarifa_minuto = 100  # pesos colombianos por minuto
        return round(minutos * tarifa_minuto, 2)

    def __repr__(self):
        return f'<Registro {self.placa} - Entrada: {self.hora_entrada}>'


class PagoMensualidad(db.Model):
    """Registra si un miembro universitario pagó su mensualidad"""
    __tablename__ = 'pagos_mensualidad'

    id             = db.Column(db.Integer, primary_key=True)
    codigo_miembro = db.Column(db.String(20), nullable=False)
    mes            = db.Column(db.String(7), nullable=False)   # formato: '2024-05'
    pagado         = db.Column(db.Boolean, default=False)
    fecha_pago     = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Pago {self.codigo_miembro} - {self.mes} - Pagado: {self.pagado}>'


# ─── Crear las tablas al iniciar ───────────────────────────────────────────────

with app.app_context():
    db.create_all()
    print("✅ Base de datos lista")


# ─── RUTAS ────────────────────────────────────────────────────────────────────

from flask import render_template, request, redirect, url_for

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    """Muestra el formulario de registro y procesa los datos enviados"""
    mensaje      = None
    tipo_mensaje = None

    if request.method == 'POST':
        tipo_usuario = request.form.get('tipo_usuario')

        if tipo_usuario == 'visitante':
            nombre = request.form.get('nombre_visitante', '').strip()
            placa  = request.form.get('placa_visitante', '').strip().upper()

            if not nombre or not placa:
                mensaje      = 'Por favor completa todos los campos.'
                tipo_mensaje = 'error'
            else:
                # Verificar si la placa ya existe
                existente = Visitante.query.filter_by(placa=placa).first()
                if existente:
                    mensaje      = f'La placa {placa} ya está registrada.'
                    tipo_mensaje = 'error'
                else:
                    nuevo = Visitante(nombre=nombre, placa=placa)
                    # También registrar en la tabla general de vehículos
                    vehiculo = Vehiculo(placa=placa, tipo_usuario='visitante')
                    db.session.add(nuevo)
                    db.session.add(vehiculo)
                    db.session.commit()
                    mensaje      = f'✅ ¡Bienvenido {nombre}! Vehículo {placa} registrado.'
                    tipo_mensaje = 'exito'

        elif tipo_usuario == 'miembro':
            nombre   = request.form.get('nombre_miembro', '').strip()
            placa    = request.form.get('placa_miembro', '').strip().upper()
            codigo   = request.form.get('codigo', '').strip()
            tipo     = request.form.get('tipo_miembro', '').strip()
            correo   = request.form.get('correo', '').strip()
            telefono = request.form.get('telefono', '').strip()

            if not all([nombre, placa, codigo, tipo, correo]):
                mensaje      = 'Por favor completa todos los campos obligatorios.'
                tipo_mensaje = 'error'
            else:
                existente = MiembroUniversidad.query.filter_by(placa=placa).first()
                if existente:
                    mensaje      = f'La placa {placa} ya está registrada.'
                    tipo_mensaje = 'error'
                else:
                    nuevo    = MiembroUniversidad(
                                    nombre=nombre, placa=placa, codigo=codigo,
                                    tipo=tipo, correo=correo, telefono=telefono)
                    vehiculo = Vehiculo(placa=placa, tipo_usuario=tipo)
                    db.session.add(nuevo)
                    db.session.add(vehiculo)
                    db.session.commit()
                    mensaje      = f'✅ ¡Bienvenido {nombre}! Vehículo {placa} registrado.'
                    tipo_mensaje = 'exito'

    return render_template('registro.html', mensaje=mensaje, tipo_mensaje=tipo_mensaje)


# ─── Punto de entrada ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
