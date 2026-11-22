"""Rutas del panel web."""

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    render_template,
    request,
)
import csv
import io

from app.models.db import get_db
from app.services.auth import login_required, role_required, usuario_actual
from app.services.configuracion import listar_configuracion
from app.services.eventos import (
    contar_eventos_filtrados,
    listar_eventos_filtrados,
)

bp = Blueprint("main", __name__)

ESTADOS_VALIDOS = {"NORMAL", "ADVERTENCIA", "PELIGRO", "FALLO_SENSOR", "INICIALIZANDO"}


def _filtros_desde_request() -> dict:
    """Normaliza los filtros de la query string."""
    desde = (request.args.get("desde") or "").strip() or None
    hasta = (request.args.get("hasta") or "").strip() or None
    estado = (request.args.get("estado") or "").strip().upper() or None
    if estado and estado not in ESTADOS_VALIDOS:
        estado = None
    try:
        limite = int(request.args.get("limite", "100"))
    except ValueError:
        limite = 100
    limite = max(1, min(limite, 500))
    return {"desde": desde, "hasta": hasta, "estado": estado, "limite": limite}


@bp.route("/")
@login_required
def index():
    usuario = usuario_actual()
    return render_template(
        "index.html",
        titulo=current_app.config["TITULO_SISTEMA"],
        modo_simulacion=current_app.config["MODO_SIMULACION"],
        usuario=usuario,
        es_admin=(usuario or {}).get("rol") == "ADMINISTRADOR",
    )


@bp.route("/configuracion")
@role_required("ADMINISTRADOR")
def configuracion():
    usuario = usuario_actual()
    db = get_db()
    return render_template(
        "configuracion.html",
        titulo=current_app.config["TITULO_SISTEMA"],
        usuario=usuario,
        configuracion=listar_configuracion(db),
    )


@bp.route("/historial")
@role_required("ADMINISTRADOR")
def historial():
    usuario = usuario_actual()
    filtros = _filtros_desde_request()
    db = get_db()
    eventos = listar_eventos_filtrados(
        db,
        desde=filtros["desde"],
        hasta=filtros["hasta"],
        estado=filtros["estado"],
        limite=filtros["limite"],
    )
    total = contar_eventos_filtrados(
        db,
        desde=filtros["desde"],
        hasta=filtros["hasta"],
        estado=filtros["estado"],
    )
    return render_template(
        "historial.html",
        titulo=current_app.config["TITULO_SISTEMA"],
        usuario=usuario,
        eventos=eventos,
        total=total,
        filtros=filtros,
        estados=sorted(ESTADOS_VALIDOS),
    )


@bp.route("/historial/export.csv")
@role_required("ADMINISTRADOR")
def historial_export_csv():
    filtros = _filtros_desde_request()
    db = get_db()
    eventos = listar_eventos_filtrados(
        db,
        desde=filtros["desde"],
        hasta=filtros["hasta"],
        estado=filtros["estado"],
        limite=filtros["limite"],
    )

    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=",", quoting=csv.QUOTE_MINIMAL)
    escritor.writerow(["id_evento", "fecha_hora", "estado", "descripcion"])
    for evento in eventos:
        escritor.writerow([
            evento["id_evento"],
            evento["fecha_hora"],
            evento["estado"],
            evento["descripcion"],
        ])

    return Response(
        salida.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=historial_eventos.csv"},
    )


@bp.route("/health")
def health():
    try:
        get_db().execute("SELECT 1").fetchone()
        estado_bd = "ok"
    except Exception as error:
        estado_bd = f"error: {error}"
    return jsonify({
        "estado": "ok" if estado_bd == "ok" else "error",
        "base_de_datos": estado_bd,
        "modo_simulacion": current_app.config["MODO_SIMULACION"],
        "version": "1.0-M8",
    })