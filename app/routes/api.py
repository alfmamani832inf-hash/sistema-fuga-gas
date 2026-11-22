"""
API REST del sistema (RF06, RF09).

Protege los endpoints sensibles con login y rol ADMINISTRADOR.
"""

from flask import Blueprint, current_app, jsonify, request

from app.models.db import get_db
from app.services.auth import login_required, role_required
from app.services.configuracion import (
    actualizar_configuracion,
    listar_configuracion,
)
from app.services.estado_sistema import ServicioEstado
from app.services.eventos import listar_eventos
from app.services.instancia_simulador import obtener_simulador
from app.services.valvula import (
    reabrir_valvula_manual,
    estado_reportado_actual,
)

bp = Blueprint("api", __name__, url_prefix="/api")


def _simulador():
    return obtener_simulador(current_app)


def _guardar_lectura_en_bd(resultado: dict) -> None:
    db = get_db()
    sensor = db.execute(
        "SELECT id_sensor FROM Sensor WHERE tipo = 'MQ-2' LIMIT 1"
    ).fetchone()
    if sensor is None:
        return
    db.execute(
        "INSERT INTO Lectura (id_sensor, fecha_hora, valor, unidad) "
        "VALUES (?, ?, ?, 'ppm_simulado')",
        (sensor["id_sensor"], resultado["timestamp"], resultado["valor_mq2"]),
    )
    db.commit()


# ---------------------------------------------------------------------------
# Endpoints publicos (cualquier usuario logueado)
# ---------------------------------------------------------------------------

@bp.route("/estado")
@login_required
def estado():
    sim = _simulador()
    servicio = ServicioEstado(sim)
    resultado = servicio.estado_actual()
    _guardar_lectura_en_bd(resultado)
    return jsonify(resultado)


@bp.route("/valvula")
@login_required
def estado_valvula():
    db = get_db()
    return jsonify({"estado_reportado": estado_reportado_actual(db)})


@bp.route("/eventos")
@login_required
def eventos():
    try:
        limite = int(request.args.get("limite", "20"))
    except ValueError:
        limite = 20
    limite = max(1, min(limite, 200))
    db = get_db()
    eventos_lista = listar_eventos(db, limite)
    return jsonify({"total": len(eventos_lista), "eventos": eventos_lista})


@bp.route("/salud")
@login_required
def salud():
    try:
        get_db().execute("SELECT 1").fetchone()
        estado_bd = "ok"
    except Exception as error:  # pragma: no cover
        estado_bd = f"error: {error}"

    return jsonify({
        "estado": "ok" if estado_bd == "ok" else "error",
        "base_de_datos": estado_bd,
        "modo_simulacion": current_app.config.get("MODO_SIMULACION", True),
        "escenario_actual": _simulador().escenario_actual(),
        "version": "1.0-M7",
    })


@bp.route("/configuracion", methods=["GET"])
@login_required
def obtener_configuracion():
    db = get_db()
    return jsonify(listar_configuracion(db))


# ---------------------------------------------------------------------------
# Endpoints solo ADMINISTRADOR
# ---------------------------------------------------------------------------

@bp.route("/escenario", methods=["POST"])
@role_required("ADMINISTRADOR")
def forzar_escenario():
    if not current_app.config.get("MODO_SIMULACION", True):
        return jsonify({"error": "Solo disponible en MODO_SIMULACION"}), 400

    datos = request.get_json(silent=True) or {}
    nombre = (datos.get("escenario") or "").strip().lower()
    if not nombre:
        return jsonify({"error": "Falta el campo 'escenario'"}), 400

    try:
        _simulador().forzar_escenario(nombre)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"ok": True, "escenario": _simulador().escenario_actual()})


@bp.route("/valvula/reabrir", methods=["POST"])
@role_required("ADMINISTRADOR")
def reabrir_valvula():
    db = get_db()
    return jsonify(reabrir_valvula_manual(db))


@bp.route("/configuracion", methods=["POST"])
@role_required("ADMINISTRADOR")
def cambiar_configuracion():
    datos = request.get_json(silent=True) or {}
    if not isinstance(datos, dict) or not datos:
        return jsonify({"error": "Debe enviar al menos un parametro"}), 400
    try:
        db = get_db()
        resultado = actualizar_configuracion(db, datos)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"ok": True, "configuracion": resultado})