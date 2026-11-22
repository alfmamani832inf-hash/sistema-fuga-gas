"""
Servicio integrador del estado del sistema (M3 + M4 + M5).

Une: lectura simulada -> validacion -> clasificacion -> alarma
     -> control de valvula -> registro de eventos -> diagnostico.
"""

from app.models.db import get_db
from .alarma import accion_para_estado_dict
from .clasificador import (
    EstadoSistema,
    clasificar_lectura_con_bd,
)
from .diagnostico import diagnostico_completo
from .eventos import registrar_evento, registrar_transicion_si_corresponde
from .lecturas import ServicioLecturas
from .valvula import controlar_valvula, estado_reportado_actual


DESCRIPCIONES = {
    EstadoSistema.INICIALIZANDO: "Sistema en inicializacion.",
    EstadoSistema.NORMAL: "Concentracion de gas en rango normal.",
    EstadoSistema.ADVERTENCIA: "Concentracion de gas en rango de advertencia.",
    EstadoSistema.PELIGRO: "Concentracion de gas en rango de peligro.",
    EstadoSistema.FALLO_SENSOR: "Lectura del sensor no confiable.",
}


class ServicioEstado:
    def __init__(self, lector):
        self.lector = lector
        self.servicio_lecturas = ServicioLecturas(lector)

    def estado_actual(self) -> dict:
        lectura = self.servicio_lecturas.obtener_lectura_validada()
        db = get_db()
        estado = clasificar_lectura_con_bd(lectura, db)
        alarma = accion_para_estado_dict(estado)

        # --- M5: control de la valvula ---
        resultado_valvula = controlar_valvula(db, estado, lectura.get("cruda", {}))

        # --- M4: registrar transicion si el estado cambio ---
        descripcion = DESCRIPCIONES.get(estado, "Cambio de estado.")
        se_registro = registrar_transicion_si_corresponde(db, estado, descripcion)

        # --- M4: diagnostico ---
        diagnostico = diagnostico_completo(lectura)

        # --- M5: registrar orden de valvula como evento (si fue orden real) ---
        if resultado_valvula["orden"] in ("ABRIR", "CERRAR"):
            registrar_evento(
                db,
                estado,
                f"Valvula: orden {resultado_valvula['orden']} -> "
                f"reportado {resultado_valvula['estado_reportado']} "
                f"(confirmado={resultado_valvula['confirmado']})",
            )

        cruda = lectura.get("cruda", {})
        return {
            "estado": estado.value,
            "valor_mq2": lectura["valor_mq2"],
            "valida": lectura["valida"],
            "errores": lectura["errores"],
            "timestamp": lectura["timestamp"],
            "fuente": lectura["fuente"],
            "escenario": cruda.get("escenario"),
            "alarma": alarma,
            "temperatura": cruda.get("temperatura"),
            "humedad": cruda.get("humedad"),
            "evento_registrado": se_registro,
            "diagnostico": diagnostico,
            "valvula": resultado_valvula,
            "valvula_estado_reportado": estado_reportado_actual(db),
        }

    def guardar_estado_actual(self, id_sensor: int) -> dict:
        resultado = self.estado_actual()
        self.servicio_lecturas.guardar_lectura(id_sensor, resultado)
        return resultado