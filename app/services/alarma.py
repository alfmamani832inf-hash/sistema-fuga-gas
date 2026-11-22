"""
Alarma virtual (RF04).

Determina la accion del LED y del buzzer para cada estado del sistema.
El frontend (M6) leera esta configuracion para iluminar el LED en
pantalla y reproducir el sonido de alarma en el navegador.
"""

from dataclasses import dataclass

from .clasificador import EstadoSistema


@dataclass
class AccionAlarma:
    """Configuracion visual y sonora para un estado."""

    estado: EstadoSistema
    color_led: str        # "verde", "amarillo", "rojo", "azul"
    patron_led: str       # "apagado", "fijo", "parpadeante"
    frecuencia_led_hz: float   # 0 si es fijo o apagado
    sonido: str           # "silencio", "pitido", "intermitente", "largo"
    frecuencia_sonido_hz: float  # frecuencia del tono (0 si silencio)
    descripcion: str


# Mapa de acciones por estado.
# Los colores coinciden con la semantica visual estandar de seguridad.
ACCIONES_POR_ESTADO = {
    EstadoSistema.INICIALIZANDO: AccionAlarma(
        estado=EstadoSistema.INICIALIZANDO,
        color_led="azul",
        patron_led="parpadeante",
        frecuencia_led_hz=1.0,
        sonido="silencio",
        frecuencia_sonido_hz=0.0,
        descripcion="Sistema arrancando, esperando primera lectura valida.",
    ),
    EstadoSistema.NORMAL: AccionAlarma(
        estado=EstadoSistema.NORMAL,
        color_led="verde",
        patron_led="fijo",
        frecuencia_led_hz=0.0,
        sonido="silencio",
        frecuencia_sonido_hz=0.0,
        descripcion="Sin presencia de gas. Operacion normal.",
    ),
    EstadoSistema.ADVERTENCIA: AccionAlarma(
        estado=EstadoSistema.ADVERTENCIA,
        color_led="amarillo",
        patron_led="parpadeante",
        frecuencia_led_hz=2.0,
        sonido="pitido",
        frecuencia_sonido_hz=880.0,
        descripcion="Concentracion moderada. Precaución.",
    ),
    EstadoSistema.PELIGRO: AccionAlarma(
        estado=EstadoSistema.PELIGRO,
        color_led="rojo",
        patron_led="fijo",
        frecuencia_led_hz=0.0,
        sonido="intermitente",
        frecuencia_sonido_hz=1500.0,
        descripcion="Concentracion peligrosa. Evacuar y cortar suministro.",
    ),
    EstadoSistema.FALLO_SENSOR: AccionAlarma(
        estado=EstadoSistema.FALLO_SENSOR,
        color_led="rojo",
        patron_led="parpadeante",
        frecuencia_led_hz=4.0,
        sonido="largo",
        frecuencia_sonido_hz=440.0,
        descripcion="Sensor sin lectura confiable. Revisar conexion.",
    ),
}


def accion_para_estado(estado: EstadoSistema) -> AccionAlarma:
    """Devuelve la accion de alarma correspondiente al estado."""
    return ACCIONES_POR_ESTADO[estado]


def accion_para_estado_dict(estado: EstadoSistema) -> dict:
    """
    Devuelve la accion como dict serializable a JSON (para la API REST del M6).
    """
    accion = accion_para_estado(estado)
    return {
        "estado": accion.estado.value,
        "color_led": accion.color_led,
        "patron_led": accion.patron_led,
        "frecuencia_led_hz": accion.frecuencia_led_hz,
        "sonido": accion.sonido,
        "frecuencia_sonido_hz": accion.frecuencia_sonido_hz,
        "descripcion": accion.descripcion,
    }