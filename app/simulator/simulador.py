"""
Simulador de hardware (Proyecto 1.0).

Genera lecturas MQ-2 (escala 0-1000) y DHT22 (temperatura/humedad)
con ruido realista. Permite forzar escenarios desde el panel para
demostrar el comportamiento del sistema sin hardware fisico.
"""

import random
from datetime import datetime, timezone

from .base import LectorSensor


ESCENARIOS_VALIDOS = {
    "normal",
    "advertencia",
    "peligro",
    "fallo_sensor",
    "perdida_wifi",
    "fallo_valvula",
}


class SimuladorMQ2DHT22(LectorSensor):
    """Simulador con ruido realista y escenarios forzables."""

    def __init__(self) -> None:
        self._escenario = "normal"
        # Deriva lenta de temperatura/humedad (simula inercia termica).
        self._temperatura_base = 22.0
        self._humedad_base = 55.0

    # ------------------------------------------------------------------
    # Escenarios
    # ------------------------------------------------------------------
    def forzar_escenario(self, nombre: str) -> None:
        nombre = (nombre or "").strip().lower()
        if nombre not in ESCENARIOS_VALIDOS:
            raise ValueError(
                f"Escenario invalido: {nombre}. "
                f"Validos: {sorted(ESCENARIOS_VALIDOS)}"
            )
        self._escenario = nombre

    def escenario_actual(self) -> str:
        return self._escenario

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------
    def leer(self) -> dict:
        momento = datetime.now(timezone.utc).isoformat(timespec="seconds")
        esc = self._escenario
        errores = []

        # --- MQ-2 ---
        if esc == "fallo_sensor":
            mq2 = None
            errores.append("lectura_nula")
        elif esc == "perdida_wifi":
            mq2 = self._valor_mq2(250, 280)
        elif esc == "peligro":
            mq2 = self._valor_mq2(620, 950)
        elif esc == "advertencia":
            mq2 = self._valor_mq2(310, 560)
        elif esc == "fallo_valvula":
            mq2 = self._valor_mq2(120, 240)
        else:  # normal
            mq2 = self._valor_mq2(80, 220)

        # 50% de las veces en fallo_sensor, forzamos valor fuera de rango
        if esc == "fallo_sensor" and random.random() < 0.5:
            mq2 = 1500
            errores.append("fuera_de_rango")

        # --- DHT22 ---
        temperatura = round(
            self._temperatura_base + random.uniform(-0.8, 0.8), 1
        )
        humedad = round(self._humedad_base + random.uniform(-2.0, 2.0), 1)
        # Deriva lenta
        self._temperatura_base += random.uniform(-0.05, 0.05)
        self._humedad_base += random.uniform(-0.2, 0.2)

        return {
            "mq2": mq2,
            "temperatura": temperatura,
            "humedad": humedad,
            "timestamp": momento,
            "fuente": "simulado",
            "escenario": esc,
            "errores": errores,
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _valor_mq2(minimo: float, maximo: float) -> float:
        """Valor con ruido uniforme + pequena componente gaussiana."""
        base = random.uniform(minimo, maximo)
        ruido = random.gauss(0, max(1.0, (maximo - minimo) * 0.03))
        return round(max(0.0, base + ruido), 1)