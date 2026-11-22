"""
Diagnostico del sistema (RF10).

Evalua tres componentes:
  - Sensor:        la ultima lectura fue valida?
  - Comunicacion:  hay conectividad (Wi-Fi) disponible?
  - Salida:        el actuador (electrovalvula) respondio?

El diagnostico NO reemplaza al clasificador de estados: lo complementa.
El clasificador dice "que tan peligrosa es la situacion"; el diagnostico
dice "que componentes del sistema estan funcionando correctamente".
"""

from dataclasses import dataclass, asdict


@dataclass
class EstadoComponente:
    """Estado de un componente individual del sistema."""

    nombre: str          # "sensor", "comunicacion", "salida"
    operativo: bool      # True si funciona, False si falla
    detalle: str         # explicacion legible

    def a_dict(self) -> dict:
        return asdict(self)


def diagnosticar_sensor(resultado_lectura: dict) -> EstadoComponente:
    """
    Evalua si el sensor entrego una lectura confiable.
    """
    if resultado_lectura.get("valida", False) and resultado_lectura.get("valor_mq2") is not None:
        return EstadoComponente(
            nombre="sensor",
            operativo=True,
            detalle=f"Lectura valida: {resultado_lectura['valor_mq2']:.1f} ppm_simulado",
        )
    errores = resultado_lectura.get("errores") or ["desconocido"]
    return EstadoComponente(
        nombre="sensor",
        operativo=False,
        detalle=f"Sin lectura confiable: {', '.join(errores)}",
    )


def diagnosticar_comunicacion(resultado_lectura: dict) -> EstadoComponente:
    """
    Evalua si hay conectividad (Wi-Fi) segun el escenario simulado.
    En hardware real, esto se sustituira por un ping al ESP32.
    """
    escenario = (resultado_lectura.get("cruda") or {}).get("escenario")
    if escenario == "perdida_wifi":
        return EstadoComponente(
            nombre="comunicacion",
            operativo=False,
            detalle="Wi-Fi perdido (escenario simulado). Datos no actualizados.",
        )
    return EstadoComponente(
        nombre="comunicacion",
        operativo=True,
        detalle="Wi-Fi operativo (simulado).",
    )


def diagnosticar_salida(resultado_lectura: dict) -> EstadoComponente:
    """
    Evalua si el actuador responde.
    En hardware real, se verificara el estado reportado de la electrovalvula.
    """
    escenario = (resultado_lectura.get("cruda") or {}).get("escenario")
    if escenario == "fallo_valvula":
        return EstadoComponente(
            nombre="salida",
            operativo=False,
            detalle="Electrovalvula no responde (escenario simulado).",
        )
    return EstadoComponente(
        nombre="salida",
        operativo=True,
        detalle="Electrovalvula operativa (simulado).",
    )


def diagnostico_completo(resultado_lectura: dict) -> dict:
    """
    Devuelve el diagnostico de los tres componentes como dict serializable.
    """
    componentes = [
        diagnosticar_sensor(resultado_lectura),
        diagnosticar_comunicacion(resultado_lectura),
        diagnosticar_salida(resultado_lectura),
    ]
    todo_operativo = all(c.operativo for c in componentes)
    return {
        "todo_operativo": todo_operativo,
        "componentes": [c.a_dict() for c in componentes],
    }