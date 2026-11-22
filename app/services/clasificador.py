"""
Clasificador de estados del sistema (RF03).

Convierte un valor MQ-2 validado en uno de los 5 estados logicos.
Los umbrales se leen de la tabla Configuracion (no estan fijos en
el codigo), cumpliendo RF09 y la regla "valores simulados,
pendientes de calibracion real".
"""

from enum import Enum


class EstadoSistema(str, Enum):
    """Estados logicos del sistema (coinciden con el documento del proyecto)."""

    INICIALIZANDO = "INICIALIZANDO"
    NORMAL = "NORMAL"
    ADVERTENCIA = "ADVERTENCIA"
    PELIGRO = "PELIGRO"
    FALLO_SENSOR = "FALLO_SENSOR"


# Umbrales por defecto (se usan si no se encuentran en la BD).
UMBRAL_ADVERTENCIA_DEFECTO = 300.0
UMBRAL_PELIGRO_DEFECTO = 600.0


def leer_umbrales_desde_bd(db) -> tuple[float, float]:
    """
    Lee los umbrales configurados en la tabla Configuracion.
    Devuelve (umbral_advertencia, umbral_peligro).
    """
    filas = db.execute(
        "SELECT parametro, valor FROM Configuracion "
        "WHERE parametro IN ('mq2_umbral_advertencia', 'mq2_umbral_peligro')"
    ).fetchall()

    valores = {fila["parametro"]: fila["valor"] for fila in filas}

    try:
        advertencia = float(
            valores.get("mq2_umbral_advertencia", UMBRAL_ADVERTENCIA_DEFECTO)
        )
    except (TypeError, ValueError):
        advertencia = UMBRAL_ADVERTENCIA_DEFECTO

    try:
        peligro = float(valores.get("mq2_umbral_peligro", UMBRAL_PELIGRO_DEFECTO))
    except (TypeError, ValueError):
        peligro = UMBRAL_PELIGRO_DEFECTO

    # Sanidad: peligro siempre debe ser mayor que advertencia.
    if peligro <= advertencia:
        advertencia = UMBRAL_ADVERTENCIA_DEFECTO
        peligro = UMBRAL_PELIGRO_DEFECTO

    return advertencia, peligro


def clasificar_lectura(
    resultado_validacion: dict,
    umbral_advertencia: float = UMBRAL_ADVERTENCIA_DEFECTO,
    umbral_peligro: float = UMBRAL_PELIGRO_DEFECTO,
) -> EstadoSistema:
    """
    Clasifica una lectura validada en un estado del sistema.

    :param resultado_validacion: dict devuelto por ServicioLecturas
                                  (contiene "valida", "valor_mq2", "errores").
    :return: EstadoSistema
    """
    # Si la validacion fallo, el estado es FALLO_SENSOR.
    if not resultado_validacion.get("valida", False):
        return EstadoSistema.FALLO_SENSOR

    valor = resultado_validacion.get("valor_mq2")
    if valor is None:
        return EstadoSistema.FALLO_SENSOR

    valor = float(valor)
    if valor >= umbral_peligro:
        return EstadoSistema.PELIGRO
    if valor >= umbral_advertencia:
        return EstadoSistema.ADVERTENCIA
    return EstadoSistema.NORMAL


def clasificar_lectura_con_bd(resultado_validacion: dict, db) -> EstadoSistema:
    """
    Variante que lee los umbrales desde la base de datos.
    """
    advertencia, peligro = leer_umbrales_desde_bd(db)
    return clasificar_lectura(resultado_validacion, advertencia, peligro)