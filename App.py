from _future_ import annotations

from datetime import datetime
from math import ceil
from typing import Dict, List, Optional

from flask import Flask, jsonify, request

# ============================================================
#  Modelos (OOP) - solo 3 clases: User, Vehicle, ParkingRecord
# ============================================================


class User:
    """
    Representa un usuario del sistema de estacionamiento.
    En este ejemplo lo mantenemos simple: id, nombre, email y rol.
    """

    def _init_(self, user_id: int, name: str, email: str, role: str) -> None:
        self.user_id = user_id
        self.name = name.strip()
        self.email = email.strip().lower()
        self.role = role.strip().lower()  # admin, employee, student, visitor

    def to_dict(self) -> dict:
        return {
            "id": self.user_id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
        }


class Vehicle:
    """
    Representa un vehículo registrado.

    - plate: placa/patente (para bicicletas también puede ser un identificador simple).
    - owner_id: id del usuario dueño.
    - vehicle_type: "car", "motorcycle", "bicycle", etc.

    Requisito: bicycle es un tipo especial que NO requiere pago.
    """

    def _init_(self, plate: str, owner_id: int, vehicle_type: str) -> None:
        self.plate = plate.strip().upper()
        self.owner_id = owner_id
        self.vehicle_type = vehicle_type.strip().lower()

    def payment_required(self) -> bool:
        # Si es bicicleta, no se cobra.
        return self.vehicle_type != "bicycle"

    def to_dict(self) -> dict:
        return {
            "plate": self.plate,
            "owner_id": self.owner_id,
            "type": self.vehicle_type,
            "payment_required": self.payment_required(),
        }


class ParkingRecord:
    """
    Registro de entrada y salida del estacionamiento para un vehículo.

    - entry_time: fecha/hora cuando entra
    - exit_time: fecha/hora cuando sale (puede ser None si está dentro)
    - amount_due: monto simple calculado al salir
    """

    def _init_(self, record_id: int, plate: str, entry_time: datetime) -> None:
        self.record_id = record_id
        self.plate = plate.strip().upper()
        self.entry_time = entry_time
        self.exit_time: Optional[datetime] = None
        self.amount_due: float = 0.0

    def close(self, exit_time: datetime, amount_due: float) -> None:
        self.exit_time = exit_time
        self.amount_due = float(amount_due)

    def is_open(self) -> bool:
        return self.exit_time is None

    def to_dict(self) -> dict:
        return {
            "id": self.record_id,
            "plate": self.plate,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "amount_due": self.amount_due,
            "status": "inside" if self.is_open() else "outside",
        }


class ParkingSystem:
    """
    Clase principal del sistema.
    Guarda datos en memoria y maneja toda la lógica del negocio.
    """

    def _init_(self) -> None:
        self.users_by_id: Dict[int, User] = {}
        self.vehicles_by_plate: Dict[str, Vehicle] = {}
        self.records: List[ParkingRecord] = []
        self.next_user_id = 1
        self.next_record_id = 1

    def register_user(self, name: str, email: str, role: str) -> User:
        user = User(self.next_user_id, name, email, role)
        self.users_by_id[user.user_id] = user
        self.next_user_id += 1
        return user

    def register_vehicle(self, plate: str, owner_id: int, vehicle_type: str) -> Vehicle:
        vehicle = Vehicle(plate, owner_id, vehicle_type)
        self.vehicles_by_plate[vehicle.plate] = vehicle
        return vehicle

    def get_vehicle(self, plate: str) -> Optional[Vehicle]:
        return self.vehicles_by_plate.get(plate.strip().upper())

    def get_open_record(self, plate: str) -> Optional-[ParkingRecord]:
        plate_key = plate.strip().upper()
        for record in reversed(self.records):
            if record.plate == plate_key and record.is_open():
                return record
        return None

    def create_entry(self, plate: str) -> ParkingRecord:
        record = ParkingRecord(self.next_record_id, plate, datetime.now())
        self.records.append(record)
        self.next_record_id += 1
        return record

    def close_record(self, record: ParkingRecord, vehicle: Vehicle) -> ParkingRecord:
        now = datetime.now()
        record.close(now, self.calculate_amount(vehicle, record.entry_time, now))
        return record

    @staticmethod
    def calculate_amount(vehicle: Vehicle, entry_time: datetime, exit_time: datetime) -> float:
        # Bicicleta no paga. Otros pagan 1.50 por hora (redondeo hacia arriba).
        if not vehicle.payment_required():
            return 0.0

        hours = max(1, ceil((exit_time - entry_time).total_seconds() / 3600))
        return 1.50 * hours


# ============================================================
#  Endpoints requeridos (REST API básica)
# ============================================================

app = Flask(_name_)
system = ParkingSystem()


def _json_ok(data, status_code: int = 200):
    return jsonify({"success": True, "data": data}), status_code


def _json_error(message: str, status_code: int = 400):
    return jsonify({"success": False, "error": message}), status_code


def _get_json() -> dict:
    return request.get_json(silent=True) or {}


@app.get("/health")
def health():
    return _json_ok({"status": "ok"})


@app.post("/users")
def register_user():
    """
    Endpoint: registrar usuario
    Body JSON: { "name": "...", "email": "...", "role": "admin|employee|student|visitor" }
    """
    data = _get_json()
    name = data.get("name")
    email = data.get("email")
    role = data.get("role")

    if not name or not email or not role:
        return _json_error("Faltan campos: name, email, role", 400)

    role = str(role).strip().lower()
    if role not in {"admin", "employee", "student", "visitor"}:
        return _json_error("Rol inválido. Usa: admin, employee, student, visitor", 400)

    user = system.register_user(str(name), str(email), role)
    return _json_ok(user.to_dict(), 201)


@app.post("/vehicles")
def register_vehicle():
    """
    Endpoint: registrar vehículo
    Body JSON: { "plate": "...", "owner_id": 1, "type": "car|motorcycle|bicycle|..." }
    """
    data = _get_json()
    plate = data.get("plate")
    owner_id = data.get("owner_id")
    vehicle_type = data.get("type")

    if not plate or owner_id is None or not vehicle_type:
        return _json_error("Faltan campos: plate, owner_id, type", 400)

    try:
        owner_id_int = int(owner_id)
    except (TypeError, ValueError):
        return _json_error("owner_id debe ser un número entero", 400)

    if owner_id_int not in system.users_by_id:
        return _json_error("El owner_id no existe", 404)

    if system.get_vehicle(str(plate)):
        return _json_error("Ya existe un vehículo con esa placa", 409)

    vehicle = system.register_vehicle(str(plate), owner_id_int, str(vehicle_type))
    return _json_ok(vehicle.to_dict(), 201)


@app.post("/records/entry")
def entry_record():
    """
    Endpoint: registrar entrada
    Body JSON: { "plate": "ABC123" }
    """
    data = _get_json()
    plate = data.get("plate")
    if not plate:
        return _json_error("Falta el campo: plate", 400)

    plate_key = str(plate).strip().upper()
    vehicle = system.get_vehicle(plate_key)
    if not vehicle:
        return _json_error("Vehículo no registrado", 404)

    if system.get_open_record(plate_key):
        return _json_error("Ya existe una entrada activa para este vehículo", 409)

    record = system.create_entry(plate_key)
    return _json_ok(record.to_dict(), 201)


@app.post("/records/exit")
def exit_record():
    """
    Endpoint: registrar salida
    Body JSON: { "plate": "ABC123" }
    """
    data = _get_json()
    plate = data.get("plate")
    if not plate:
        return _json_error("Falta el campo: plate", 400)

    plate_key = str(plate).strip().upper()
    vehicle = system.get_vehicle(plate_key)
    if not vehicle:
        return _json_error("Vehículo no registrado", 404)

    record = system.get_open_record(plate_key)
    if not record:
        return _json_error("No hay un registro de entrada activo para este vehículo", 409)

    system.close_record(record, vehicle)
    return _json_ok(record.to_dict(), 200)


@app.get("/records")
def list_records():
    """
    Endpoint: listar registros de estacionamiento (todos)
    """
    return _json_ok([record.to_dict() for record in system.records])


if _name_ == "_main_":
    # debug=True es cómodo para aprender (auto-reload). En producción se recomienda desactivarlo.
    app.run(debug=True, host="0.0.0.0", port=5000)