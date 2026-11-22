"""
Servicio de adquisicion de lecturas.

Coordina: lector (real o simulado) -> validacion -> persistencia
en la tabla Lectura. En el M3 se conectara con el clasificador.
"""

from datetime import datetime, timezone

from app.models.db import get_db
from .validacion import validar_lectura_mq2


class ServicioLecturas:
    def __init__(self, lector):
        """
        :param lector: instancia de LectorSensor (simulador o ESP32).
        """
        self.lector = lector

    def obtener_lectura_validada(self) -> dict:
        """
        Devuelve un dict con:
        {
            "cruda": {...},               # lectura original del sensor
            "valida": True/False,
            "valor_mq2": float | None,
            "errores": [...],
            "fuente": "simulado" | "esp32",
            "timestamp": "...Z"
        }
        """
        cruda = self.lector.leer()
        validacion = validar_lectura_mq2(cruda.get("mq2"))

        return {
            "cruda": cruda,
            "valida": validacion.valida,
            "valor_mq2": validacion.valor,
            "errores": list(cruda.get("errores", [])) + validacion.errores,
            "fuente": cruda.get("fuente", "desconocida"),
            "timestamp": cruda.get("timestamp")
            or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    def guardar_lectura(self, id_sensor: int, resultado: dict) -> int:
        """
        Persiste la lectura validada en la tabla Lectura.
        Las lecturas invalidas se guardan con valor NULL para dejar
        constancia del intento, pero NUNCA se presentan como confiables.
        """
        db = get_db()
        cursor = db.execute(
            "INSERT INTO Lectura (id_sensor, fecha_hora, valor, unidad) "
            "VALUES (?, ?, ?, 'ppm_simulado')",
            (id_sensor, resultado["timestamp"], resultado["valor_mq2"]),
        )
        db.commit()
        return cursor.lastrowid