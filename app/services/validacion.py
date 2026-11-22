"""
Validacion de lecturas (RF02, RNF02).

Reglas:
  - La lectura MQ-2 debe ser numerica.
  - Debe estar dentro del rango configurado (por defecto 0-1000).
  - Los valores nulos se rechazan.
  - Si hay algun error, la lectura se marca como NO CONFIABLE
    y el estado asociado sera FALLO_SENSOR.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ResultadoValidacion:
    valida: bool
    valor: Optional[float]
    errores: list[str]


def validar_lectura_mq2(
    valor, rango_min: float = 0.0, rango_max: float = 1000.0
) -> ResultadoValidacion:
    """Valida una lectura del MQ-2 segun el rango configurado."""
    errores: list[str] = []

    if valor is None:
        return ResultadoValidacion(False, None, ["lectura_nula"])

    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return ResultadoValidacion(False, None, ["no_numerica"])

    if numero < rango_min or numero > rango_max:
        errores.append("fuera_de_rango")

    # Un cero absoluto en el MQ-2 suele indicar sensor desconectado.
    if numero == 0:
        errores.append("posible_sensor_desconectado")

    return ResultadoValidacion(
        not errores, numero if not errores else None, errores
    )