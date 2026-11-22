"""Pruebas del control logico de la valvula (M5)."""

import pytest

from app.models.db import get_db
from app.services.clasificador import EstadoSistema
from app.services.estado_sistema import ServicioEstado
from app.services.valvula import (
    VALVULA_ABIERTA,
    VALVULA_CERRADA,
    VALVULA_DESCONOCIDO,
    VALVULA_FALLO,
    decidir_accion_valvula,
    estado_reportado_actual,
    reabrir_valvula_manual,
)
from app.simulator.simulador import SimuladorMQ2DHT22


# ---------------------------------------------------------------------------
# Decision de accion
# ---------------------------------------------------------------------------

def test_peligro_ordena_cerrar():
    accion = decidir_accion_valvula(EstadoSistema.PELIGRO, VALVULA_ABIERTA)
    assert accion["orden"] == "CERRAR"
    assert accion["estado_esperado"] == VALVULA_CERRADA


def test_peligro_con_valvula_ya_cerrada_mantiene():
    accion = decidir_accion_valvula(EstadoSistema.PELIGRO, VALVULA_CERRADA)
    assert accion["orden"] == "MANTENER"


def test_normal_con_valvula_abierta_mantiene():
    accion = decidir_accion_valvula(EstadoSistema.NORMAL, VALVULA_ABIERTA)
    assert accion["orden"] == "MANTENER"
    assert accion["estado_esperado"] == VALVULA_ABIERTA


def test_normal_con_valvula_desconocida_abre():
    accion = decidir_accion_valvula(EstadoSistema.NORMAL, VALVULA_DESCONOCIDO)
    assert accion["orden"] == "ABRIR"
    assert accion["estado_esperado"] == VALVULA_ABIERTA


def test_normal_con_valvula_cerrada_no_reabre_sola():
    accion = decidir_accion_valvula(EstadoSistema.NORMAL, VALVULA_CERRADA)
    assert accion["orden"] == "MANTENER"
    assert accion["estado_esperado"] == VALVULA_CERRADA


def test_fallo_actual_mantiene():
    accion = decidir_accion_valvula(EstadoSistema.NORMAL, VALVULA_FALLO)
    assert accion["orden"] == "MANTENER"
    assert "fallo" in accion["razon"].lower()


# ---------------------------------------------------------------------------
# Ejecucion con simulador real
# ---------------------------------------------------------------------------

def test_normal_abre_valvula(app):
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("normal")
        r = ServicioEstado(sim).estado_actual()
        assert r["valvula"]["orden"] == "ABRIR"
        assert r["valvula"]["confirmado"] is True
        assert r["valvula_estado_reportado"] == VALVULA_ABIERTA


def test_peligro_cierra_valvula(app):
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("peligro")
        r = ServicioEstado(sim).estado_actual()
        assert r["valvula"]["orden"] == "CERRAR"
        assert r["valvula"]["confirmado"] is True
        assert r["valvula_estado_reportado"] == VALVULA_CERRADA


def test_fallo_valvula_no_confirma(app):
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("fallo_valvula")
        r = ServicioEstado(sim).estado_actual()
        assert r["diagnostico"]["todo_operativo"] is False
        assert r["valvula_estado_reportado"] in (VALVULA_FALLO, VALVULA_DESCONOCIDO)


def test_fallo_valvula_en_peligro_no_confirma_cierre(app):
    """Regla de oro: si el actuador falla, confirmado debe ser False."""
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("fallo_valvula")
        r = ServicioEstado(sim).estado_actual()
        assert r["valvula"]["confirmado"] is False


def test_peligro_cierra_valvula_realmente(app):
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("normal")
        ServicioEstado(sim).estado_actual()
        db = get_db()
        assert estado_reportado_actual(db) == VALVULA_ABIERTA

        sim.forzar_escenario("peligro")
        ServicioEstado(sim).estado_actual()
        assert estado_reportado_actual(db) == VALVULA_CERRADA


# ---------------------------------------------------------------------------
# Reapertura manual
# ---------------------------------------------------------------------------

def test_reabrir_valvula_cerrada(app):
    with app.app_context():
        db = get_db()
        db.execute(
            "UPDATE Actuador SET estado_reportado = ? WHERE tipo = ?",
            (VALVULA_CERRADA, "ELECTROVALVULA"),
        )
        db.commit()
        r = reabrir_valvula_manual(db)
        assert r["confirmado"] is True
        assert r["estado_reportado"] == VALVULA_ABIERTA


def test_reabrir_valvula_en_fallo_no_permite(app):
    with app.app_context():
        db = get_db()
        db.execute(
            "UPDATE Actuador SET estado_reportado = ? WHERE tipo = ?",
            (VALVULA_FALLO, "ELECTROVALVULA"),
        )
        db.commit()
        r = reabrir_valvula_manual(db)
        assert r["confirmado"] is False
        assert r["estado_reportado"] == VALVULA_FALLO