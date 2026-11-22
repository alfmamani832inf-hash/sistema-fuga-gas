"""
Instancia unica del simulador para toda la aplicacion.

Flask atiende cada request en un contexto distinto. Si creamos un
SimuladorMQ2DHT22 dentro de cada request, perdemos el escenario forzado
y la deriva de temperatura. Por eso usamos una instancia unica,
guardada en app.extensions, que persiste entre requests.

En la version 2.0, este modulo se reemplazara por un cliente ESP32.
"""

from app.simulator.simulador import SimuladorMQ2DHT22


CLAVE_EXTENSION = "simulador_gas"


def obtener_simulador(app) -> SimuladorMQ2DHT22:
    """Devuelve la instancia unica del simulador, creandola si no existe."""
    if CLAVE_EXTENSION not in app.extensions:
        app.extensions[CLAVE_EXTENSION] = SimuladorMQ2DHT22()
    return app.extensions[CLAVE_EXTENSION]