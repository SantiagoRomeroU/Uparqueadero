from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# ─── Configuración de la aplicación ───────────────────────────────────────────

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parqueadero.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'parqueadero_universidad_2024'

db = SQLAlchemy(app)

# ─── MODELOS ──────────────────────────────────────────────────────────────────

class Usuario(db.Model):
    """Clase base que representa cualquier usuario del parqueadero"""
    __tablename__ = 'usuarios'

    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    documento      = db.Column(db.BigInteger, unique=True, nullable=False)
    nombre         = db.Column(db.String(100), nullable=False)
    correo         = db.Column(db.String(100), nullable=True)
    rol            = db.Column(db.Enum('Administrador', 'Empleado', 'Estudiante', 'Visitante'), nullable=False)
    tipo_vehiculo  = db.Column(db.Enum('carro', 'moto', 'bicicleta'), nullable=False)
    placa          = db.Column(db.String(20), nullable=False)
    hora_ingreso   = db.Column(db.DateTime, default=datetime.utcnow)
    hora_salida    = db.Column(db.DateTime, nullable=True)
    estado_pago    = db.Column(db.Enum('pendiente', 'pagado', 'exento'), default='pendiente')

    def calcular_estado_pago(self):
        """El estado de pago se calcula automáticamente según el tipo de vehículo"""
        if self.tipo_vehiculo == 'bicicleta':
            return 'exento'
        return 'pendiente'

    def calcular_cobro(self):
        """Calcula el cobro según el tiempo que estuvo en el parqueadero"""
        if not self.hora_salida or self.estado_pago == 'exento':
            return 0
        diferencia    = self.hora_salida - self.hora_ingreso
        minutos       = diferencia.total_seconds() / 60
        tarifa_minuto = 100  # pesos colombianos por minuto
        return round(minutos * tarifa_minuto, 2)

    def __repr__(self):
        return f'<Usuario {self.nombre} - {self.placa} - {self.rol}>'


class RegistroParqueo(db.Model):
    """Historial completo de entradas y salidas"""
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
    app.run(debug=True)
