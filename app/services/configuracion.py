"""
Configuracion de parametros del sistema (RF09).

Lee y escribe la tabla Configuracion. Los umbrales son
valores SIMULADOS pendientes de calibracion real; el panel
debe mostrar ese aviso.
"""

from datetime import datetime, timezone

from app.models.db import get_db


PARAMETROS_VALIDOS = {
    "mq2_umbral_advertencia",
    "mq2_umbral_peligro",
    "mq2_rango_min",
    "mq2_rango_max",
    "intervalo_lectura_seg",
    "calibracion_estado",
}

# Valores por defecto (los mismos que la semilla del M1).
VALORES_DEFECTO = {
    "mq2_umbral_advertencia": "300",
    "mq2_umbral_peligro": "600",
    "mq2_rango_min": "0",
    "mq2_rango_max": "1000",
    "intervalo_lectura_seg": "2",
    "calibracion_estado": "VALORES SIMULADOS - PENDIENTES DE CALIBRACION REAL",
}


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def listar_configuracion(db) -> dict:
    """
    Devuelve un dict {parametro: {valor, fecha_actualizacion}}.
    Si la tabla esta vacia, devuelve los valores por defecto sin inventar filas.
    """
    filas = db.execute(
        "SELECT parametro, valor, fecha_actualizacion FROM Configuracion"
    ).fetchall()
    resultado = {}
    for fila in filas:
        resultado[fila["parametro"]] = {
            "valor": fila["valor"],
            "fecha_actualizacion": fila["fecha_actualizacion"],
        }
    # Rellenamos los faltantes con defaults (solo en memoria).
    for parametro, valor in VALORES_DEFECTO.items():
        if parametro not in resultado:
            resultado[parametro] = {
                "valor": valor,
                "fecha_actualizacion": None,
            }
    return resultado


def actualizar_configuracion(db, cambios: dict) -> dict:
    """
    Actualiza uno o varios parametros. Devuelve el estado final.

    :param cambios: dict {parametro: nuevo_valor}
    :raises ValueError: si un parametro no es valido o el valor no es numerico.
    """
    # Validaciones previas
    for parametro, valor in cambios.items():
        if parametro not in PARAMETROS_VALIDOS:
            raise ValueError(f"Parametro no autorizado: {parametro}")
        if parametro.startswith("mq2_") and parametro != "calibracion_estado":
            try:
                float(valor)
            except (TypeError, ValueError):
                raise ValueError(
                    f"El parametro {parametro} debe ser numerico (recibi {valor!r})"
                )

    # Sanidad: umbral de advertencia < umbral de peligro
    advertencia = cambios.get("mq2_umbral_advertencia")
    peligro = cambios.get("mq2_umbral_peligro")
    if advertencia is not None and peligro is not None:
        if float(advertencia) >= float(peligro):
            raise ValueError(
                "El umbral de advertencia debe ser menor que el de peligro."
            )

    momento = _ahora_iso()
    for parametro, valor in cambios.items():
        existente = db.execute(
            "SELECT id_config FROM Configuracion WHERE parametro = ?",
            (parametro,),
        ).fetchone()
        if existente is None:
            db.execute(
                "INSERT INTO Configuracion (parametro, valor, fecha_actualizacion) "
                "VALUES (?, ?, ?)",
                (parametro, str(valor), momento),
            )
        else:
            db.execute(
                "UPDATE Configuracion SET valor = ?, fecha_actualizacion = ? "
                "WHERE parametro = ?",
                (str(valor), momento, parametro),
            )
    db.commit()
    return listar_configuracion(db)