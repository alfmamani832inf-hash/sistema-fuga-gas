"""Pruebas del registro de eventos y diagnostico (M4).

NOTA: Desde el M5, el sistema registra DOS tipos de eventos:
  1. Cambio de estado (NORMAL, ADVERTENCIA, PELIGRO, FALLO_SENSOR).
  2. Orden de valvula (ABRIR, CERRAR) cuando corresponde.
Por eso las pruebas de integracion esperan multiples eventos.
"""

import pytest

from app import create_app
from app.models.db import get_db
from app.services.clasificador import EstadoSistema
from app.services.diagnostico import (
    diagnosticar_comunicacion,
    diagnosticar_salida,
    diagnosticar_sensor,
    diagnostico_completo,
)
from app.services.eventos import (
    listar_eventos,
    obtener_ultimo_estado,
    registrar_evento,
    registrar_transicion_si_corresponde,
)
from app.services.estado_sistema import ServicioEstado
from app.simulator.simulador import SimuladorMQ2DHT22


# ---------------------------------------------------------------------------
# Registro de eventos (RF08) - unitarias
# ---------------------------------------------------------------------------

def test_historial_inicia_vacio(app):
    with app.app_context():
        db = get_db()
        # La app de pruebas siembra datos pero NO eventos.
        assert listar_eventos(db) == []
        assert obtener_ultimo_estado(db) is None


def test_registrar_evento_simple(app):
    with app.app_context():
        db = get_db()
        registrar_evento(db, EstadoSistema.NORMAL, "Inicio de operacion.")
        eventos = listar_eventos(db)
        assert len(eventos) == 1
        assert eventos[0]["estado"] == "NORMAL"


def test_transicion_se_registra(app):
    with app.app_context():
        db = get_db()
        se_registro = registrar_transicion_si_corresponde(
            db, EstadoSistema.NORMAL, "Primera lectura normal."
        )
        assert se_registro is True
        assert len(listar_eventos(db)) == 1


def test_transicion_repetida_no_se_duplica(app):
    with app.app_context():
        db = get_db()
        registrar_transicion_si_corresponde(db, EstadoSistema.NORMAL, "NORMAL.")
        se_registro = registrar_transicion_si_corresponde(
            db, EstadoSistema.NORMAL, "NORMAL otra vez."
        )
        assert se_registro is False
        assert len(listar_eventos(db)) == 1


def test_transicion_cambio_si_se_registra(app):
    with app.app_context():
        db = get_db()
        registrar_transicion_si_corresponde(db, EstadoSistema.NORMAL, "NORMAL.")
        se_registro = registrar_transicion_si_corresponde(
            db, EstadoSistema.ADVERTENCIA, "ADVERTENCIA."
        )
        assert se_registro is True
        assert len(listar_eventos(db)) == 2


def test_orden_eventos_mas_reciente_primero(app):
    with app.app_context():
        db = get_db()
        registrar_evento(db, EstadoSistema.NORMAL, "Primero.")
        registrar_evento(db, EstadoSistema.PELIGRO, "Segundo.")
        eventos = listar_eventos(db)
        assert eventos[0]["estado"] == "PELIGRO"
        assert eventos[1]["estado"] == "NORMAL"


# ---------------------------------------------------------------------------
# Diagnostico (RF10)
# ---------------------------------------------------------------------------

def _lectura_ok(escenario="normal"):
    return {
        "valida": True,
        "valor_mq2": 150.0,
        "errores": [],
        "cruda": {"escenario": escenario, "fuente": "simulado"},
    }


def test_diagnostico_sensor_ok():
    c = diagnosticar_sensor(_lectura_ok())
    assert c.operativo is True


def test_diagnostico_sensor_fallo():
    c = diagnosticar_sensor({
        "valida": False,
        "valor_mq2": None,
        "errores": ["lectura_nula"],
        "cruda": {"escenario": "fallo_sensor"},
    })
    assert c.operativo is False


def test_diagnostico_comunicacion_ok():
    c = diagnosticar_comunicacion(_lectura_ok())
    assert c.operativo is True


def test_diagnostico_comunicacion_fallo():
    c = diagnosticar_comunicacion(_lectura_ok("perdida_wifi"))
    assert c.operativo is False


def test_diagnostico_salida_ok():
    c = diagnosticar_salida(_lectura_ok())
    assert c.operativo is True


def test_diagnostico_salida_fallo():
    c = diagnosticar_salida(_lectura_ok("fallo_valvula"))
    assert c.operativo is False


def test_diagnostico_completo_serializable():
    d = diagnostico_completo(_lectura_ok())
    assert d["todo_operativo"] is True
    assert len(d["componentes"]) == 3


# ---------------------------------------------------------------------------
# Integracion (M4 + M5) - esperan multiples eventos
# ---------------------------------------------------------------------------

def test_servicio_registra_transicion(app):
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("normal")
        servicio = ServicioEstado(sim)

        r1 = servicio.estado_actual()
        assert r1["estado"] == "NORMAL"
        assert r1["evento_registrado"] is True

        r2 = servicio.estado_actual()
        assert r2["estado"] == "NORMAL"
        assert r2["evento_registrado"] is False

        db = get_db()
        eventos = listar_eventos(db)
        # 1 por cambio de estado + 1 por orden ABRIR = 2
        assert len(eventos) == 2


def test_servicio_transicion_normal_a_peligro(app):
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("normal")
        servicio = ServicioEstado(sim)
        servicio.estado_actual()

        sim.forzar_escenario("peligro")
        r = servicio.estado_actual()
        assert r["estado"] == "PELIGRO"
        assert r["evento_registrado"] is True

        db = get_db()
        eventos = listar_eventos(db)
        # 2 por cambio de estado + 2 por ordenes de valvula = 4
        assert len(eventos) == 4


def test_servicio_incluye_diagnostico(app):
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("perdida_wifi")
        r = ServicioEstado(sim).estado_actual()
        assert "diagnostico" in r
        assert r["diagnostico"]["todo_operativo"] is False


def test_servicio_fallo_sensor_registra_evento(app):
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("fallo_sensor")
        r = ServicioEstado(sim).estado_actual()
        assert r["estado"] == "FALLO_SENSOR"
        assert r["evento_registrado"] is True