"""
Control logico de la electrovalvula (RF05).

Reglas:
  - En estado PELIGRO la valvula se CIERRA automaticamente.
  - En estados seguros permanece ABIERTA (salvo que ya estuviera cerrada
    por una emergencia previa, en cuyo caso requiere reapertura manual).
  - Cada cambio se registra en la tabla Actuador con la orden y el
    estado reportado.
  - REGLA DE ORO: si el actuador reporta fallo, el sistema NO afirma
    que la valvula actuo. Devuelve confirmado=False y estado_reportado='FALLO'.
"""

from datetime import datetime, timezone

from app.models.db import get_db
from .clasificador import EstadoSistema


# Estados de la valvula.
VALVULA_ABIERTA = "ABIERTA"
VALVULA_CERRADA = "CERRADA"
VALVULA_FALLO = "FALLO"
VALVULA_DESCONOCIDO = "DESCONOCIDO"

# Tipo de actuador en la tabla Actuador.
TIPO_ELECTROVALVULA = "ELECTROVALVULA"


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def obtener_actuador_valvula(db) -> dict | None:
    """Devuelve la fila del actuador electrovalvula o None si no existe."""
    fila = db.execute(
        "SELECT id_actuador, tipo, estado_reportado FROM Actuador "
        "WHERE tipo = ? LIMIT 1",
        (TIPO_ELECTROVALVULA,),
    ).fetchone()
    return dict(fila) if fila else None


def estado_reportado_actual(db) -> str:
    """Devuelve el estado reportado actual de la valvula."""
    actuador = obtener_actuador_valvula(db)
    if actuador is None:
        return VALVULA_DESCONOCIDO
    return actuador["estado_reportado"]


def _actualizar_estado_reportado(db, nuevo_estado: str) -> None:
    """Actualiza el estado reportado en la tabla Actuador."""
    db.execute(
        "UPDATE Actuador SET estado_reportado = ? WHERE tipo = ?",
        (nuevo_estado, TIPO_ELECTROVALVULA),
    )
    db.commit()


def _escenario_simulado_fallo_valvula(lectura_cruda: dict) -> bool:
    """Detecta si el escenario simulado es fallo_valvula."""
    return (lectura_cruda or {}).get("escenario") == "fallo_valvula"


def decidir_accion_valvula(
    estado: EstadoSistema,
    estado_reportado: str,
    escenario_fallo: bool = False,
) -> dict:
    """
    Decide la accion a ejecutar sobre la valvula segun el estado del sistema
    y su estado reportado actual.

    :param estado: estado clasificado del sistema.
    :param estado_reportado: estado actual reportado de la valvula
                             (ABIERTA, CERRADA, FALLO, DESCONOCIDO).
    :param escenario_fallo: True si el escenario simulado es fallo_valvula.
    :return: dict con:
        {
            "orden": "ABRIR" | "CERRAR" | "MANTENER",
            "estado_esperado": "ABIERTA" | "CERRADA",
            "razon": str
        }
    """
    # --- PELIGRO: orden de cerrar ---
    if estado == EstadoSistema.PELIGRO:
        if estado_reportado == VALVULA_CERRADA:
            return {
                "orden": "MANTENER",
                "estado_esperado": VALVULA_CERRADA,
                "razon": "PELIGRO. Valvula ya cerrada; se mantiene.",
            }
        return {
            "orden": "CERRAR",
            "estado_esperado": VALVULA_CERRADA,
            "razon": "PELIGRO. Cierre automatico por seguridad.",
        }

    # --- Estados seguros ---
    # Si la valvula ya esta cerrada por una emergencia previa, NO se reabre
    # automaticamente: requiere accion manual del administrador (M7).
    if estado_reportado == VALVULA_CERRADA:
        return {
            "orden": "MANTENER",
            "estado_esperado": VALVULA_CERRADA,
            "razon": "Valvula cerrada por emergencia previa. Reapertura manual requerida.",
        }

    if estado_reportado == VALVULA_FALLO:
        return {
            "orden": "MANTENER",
            "estado_esperado": VALVULA_FALLO,
            "razon": "Valvula en fallo. Revisar actuador antes de operar.",
        }

    # Estado seguro y valvula no cerrada: asegurar que este abierta.
    if estado_reportado == VALVULA_ABIERTA:
        return {
            "orden": "MANTENER",
            "estado_esperado": VALVULA_ABIERTA,
            "razon": "Estado seguro. Valvula ya abierta.",
        }

    # Estado desconocido: abrir por defecto (posicion segura del prototipo).
    return {
        "orden": "ABRIR",
        "estado_esperado": VALVULA_ABIERTA,
        "razon": "Estado seguro. Apertura por defecto.",
    }


def ejecutar_accion_valvula(
    db,
    accion: dict,
    escenario_fallo: bool = False,
) -> dict:
    """
    Ejecuta la accion decidida y actualiza la tabla Actuador.

    :return: dict con:
        {
            "orden": "ABRIR" | "CERRAR" | "MANTENER",
            "estado_esperado": ...,
            "estado_reportado": ...,
            "confirmado": bool,
            "razon": str,
            "timestamp": "...Z"
        }
    """
    orden = accion["orden"]
    esperado = accion["estado_esperado"]

    # Si la orden es MANTENER, no se ejecuta nada fisico.
    if orden == "MANTENER":
        return {
            "orden": orden,
            "estado_esperado": esperado,
            "estado_reportado": estado_reportado_actual(db),
            "confirmado": True,
            "razon": accion["razon"],
            "timestamp": _ahora_iso(),
        }

    # Simulamos la ejecucion. En hardware real, aqui se activaria el rele.
    if escenario_fallo:
        # REGLA DE ORO: el actuador reporta fallo.
        # El sistema NO debe afirmar que la valvula actuo.
        _actualizar_estado_reportado(db, VALVULA_FALLO)
        return {
            "orden": orden,
            "estado_esperado": esperado,
            "estado_reportado": VALVULA_FALLO,
            "confirmado": False,
            "razon": (
                f"Se envio orden {orden} pero el actuador reporta FALLO. "
                "NO se confirma que la valvula haya actuado."
            ),
            "timestamp": _ahora_iso(),
        }

    # Ejecucion exitosa.
    _actualizar_estado_reportado(db, esperado)
    return {
        "orden": orden,
        "estado_esperado": esperado,
        "estado_reportado": esperado,
        "confirmado": True,
        "razon": accion["razon"],
        "timestamp": _ahora_iso(),
    }


def controlar_valvula(
    db,
    estado: EstadoSistema,
    lectura_cruda: dict,
) -> dict:
    """
    Punto de entrada principal: decide y ejecuta la accion sobre la valvula.

    :return: dict con el resultado completo de la operacion.
    """
    escenario_fallo = _escenario_simulado_fallo_valvula(lectura_cruda)
    estado_reportado = estado_reportado_actual(db)
    accion = decidir_accion_valvula(estado, estado_reportado, escenario_fallo)
    return ejecutar_accion_valvula(db, accion, escenario_fallo)


def reabrir_valvula_manual(db) -> dict:
    """
    Reapertura manual de la valvula. Solo debe llamarse desde el rol
    ADMINISTRADOR (lo implementaremos en M7).

    NO se reabre si la valvula esta en FALLO.
    """
    actual = estado_reportado_actual(db)
    if actual == VALVULA_FALLO:
        return {
            "orden": "REABRIR",
            "estado_reportado": VALVULA_FALLO,
            "confirmado": False,
            "razon": "No se puede reabrir: actuador en fallo.",
            "timestamp": _ahora_iso(),
        }
    _actualizar_estado_reportado(db, VALVULA_ABIERTA)
    return {
        "orden": "REABRIR",
        "estado_reportado": VALVULA_ABIERTA,
        "confirmado": True,
        "razon": "Reapertura manual autorizada.",
        "timestamp": _ahora_iso(),
    }