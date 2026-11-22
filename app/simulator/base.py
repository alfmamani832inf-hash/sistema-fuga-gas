"""
Interfaz base para cualquier lector de sensores.

En la version 1.0 la implementa SimuladorMQ2DHT22.
En la version 2.0 la implementara LectorESP32 (hardware real),
sin cambiar el resto del sistema.
"""

from abc import ABC, abstractmethod


class LectorSensor(ABC):
    """Contrato que debe cumplir todo lector de sensores."""

    @abstractmethod
    def leer(self) -> dict:
        """
        Devuelve una lectura cruda con la forma:
        {
            "mq2": 123.4,          # valor en escala simulada 0-1000 (o None)
            "temperatura": 22.5,   # C (o None)
            "humedad": 55.0,       # % (o None)
            "timestamp": "2026-...Z",
            "fuente": "simulado" | "esp32",
            "escenario": "normal",
            "errores": []
        }
        """
        raise NotImplementedError

    @abstractmethod
    def forzar_escenario(self, nombre: str) -> None:
        """Solo aplica al simulador. En hardware real puede ignorarse."""
        raise NotImplementedError

    @abstractmethod
    def escenario_actual(self) -> str:
        """Devuelve el nombre del escenario activo."""
        raise NotImplementedError