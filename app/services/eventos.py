"""
Registro de eventos del sistema (RF08, RNF08).

Reglas estrictas:
  - Solo se registra un evento cuando el estado CAMBIA.
  - Si no hay transiciones, la tabla Evento queda vacia
    (el historial no se inventa).
  - Cada evento lleva fecha, hora, estado y descripcion.
"""

from datetime import datetime, timezone

from app.models.db import get_db
from .clasificador import EstadoSistema


def _ahora_iso() -> str:
    """Fecha y hora actual en formato ISO-8601 (UTC)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def obtener_ultimo_estado(db) -> EstadoSistema | None:
    """Devuelve el ultimo estado registrado en la tabla Evento, o None."""
    fila = db.execute(
        "SELECT estado FROM Evento ORDER BY id_evento DESC LIMIT 1"
    ).fetchone()
    if fila is None:
        return None
    try:
        return EstadoSistema(fila["estado"])
    except ValueError:
        return None


def registrar_evento(db, estado: EstadoSistema, descripcion: str) -> int:
    """Inserta un evento en la tabla Evento y devuelve su id."""
    cursor = db.execute(
        "INSERT INTO Evento (fecha_hora, estado, descripcion) "
        "VALUES (?, ?, ?)",
        (_ahora_iso(), estado.value, descripcion),
    )
    db.commit()
    return cursor.lastrowid


def registrar_transicion_si_corresponde(
    db, nuevo_estado: EstadoSistema, descripcion: str
) -> bool:
    """Registra el evento solo si el nuevo estado difiere del ultimo."""
    ultimo = obtener_ultimo_estado(db)
    if ultimo == nuevo_estado:
        return False
    registrar_evento(db, nuevo_estado, descripcion)
    return True


def listar_eventos(db, limite: int = 100) -> list[dict]:
    """
    Devuelve los ultimos N eventos ordenados del mas reciente al mas antiguo.
    Si la tabla esta vacia, devuelve [] (no inventa filas).
    """
    filas = db.execute(
        "SELECT id_evento, fecha_hora, estado, descripcion "
        "FROM Evento ORDER BY id_evento DESC LIMIT ?",
        (limite,),
    ).fetchall()
    return [dict(fila) for fila in filas]


def listar_eventos_filtrados(
    db,
    desde: str | None = None,
    hasta: str | None = None,
    estado: str | None = None,
    limite: int = 100,
) -> list[dict]:
    """
    Devuelve los eventos aplicando filtros opcionales.

    :param desde: fecha/hora ISO-8601 minima (inclusive).
    :param hasta: fecha/hora ISO-8601 maxima (inclusive).
    :param estado: valor exacto del estado (NORMAL, ADVERTENCIA, PELIGRO...).
    :param limite: maximo de filas.
    """
    sql = (
        "SELECT id_evento, fecha_hora, estado, descripcion "
        "FROM Evento WHERE 1=1"
    )
    parametros: list = []
    if desde:
        sql += " AND fecha_hora >= ?"
        parametros.append(desde)
    if hasta:
        sql += " AND fecha_hora <= ?"
        parametros.append(hasta)
    if estado:
        sql += " AND estado = ?"
        parametros.append(estado)
    sql += " ORDER BY id_evento DESC LIMIT ?"
    parametros.append(limite)

    filas = db.execute(sql, parametros).fetchall()
    return [dict(fila) for fila in filas]


def contar_eventos_filtrados(
    db,
    desde: str | None = None,
    hasta: str | None = None,
    estado: str | None = None,
) -> int:
    """Cuenta cuantos eventos cumplen los filtros (sin limite)."""
    sql = "SELECT COUNT(*) AS total FROM Evento WHERE 1=1"
    parametros: list = []
    if desde:
        sql += " AND fecha_hora >= ?"
        parametros.append(desde)
    if hasta:
        sql += " AND fecha_hora <= ?"
        parametros.append(hasta)
    if estado:
        sql += " AND estado = ?"
        parametros.append(estado)
    return db.execute(sql, parametros).fetchone()["total"]