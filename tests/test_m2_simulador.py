"""Pruebas del simulador y la validacion (M2)."""

import pytest

from app.simulator.simulador import SimuladorMQ2DHT22, ESCENARIOS_VALIDOS
from app.services.validacion import validar_lectura_mq2


def test_escenarios_validos():
    sim = SimuladorMQ2DHT22()
    for esc in ESCENARIOS_VALIDOS:
        sim.forzar_escenario(esc)
        assert sim.escenario_actual() == esc


def test_escenario_invalido_lanza_error():
    sim = SimuladorMQ2DHT22()
    with pytest.raises(ValueError):
        sim.forzar_escenario("incendio")


def test_normal_en_rango():
    sim = SimuladorMQ2DHT22()
    sim.forzar_escenario("normal")
    for _ in range(50):
        lectura = sim.leer()
        assert 0 <= lectura["mq2"] <= 300


def test_advertencia_en_rango():
    sim = SimuladorMQ2DHT22()
    sim.forzar_escenario("advertencia")
    for _ in range(50):
        lectura = sim.leer()
        assert 250 <= lectura["mq2"] <= 650


def test_peligro_en_rango():
    sim = SimuladorMQ2DHT22()
    sim.forzar_escenario("peligro")
    for _ in range(50):
        lectura = sim.leer()
        assert lectura["mq2"] >= 550


def test_fallo_sensor_puede_ser_nulo():
    sim = SimuladorMQ2DHT22()
    sim.forzar_escenario("fallo_sensor")
    vistos_nulo = False
    for _ in range(30):
        lectura = sim.leer()
        if lectura["mq2"] is None:
            vistos_nulo = True
    assert vistos_nulo


def test_validacion_nulo():
    r = validar_lectura_mq2(None)
    assert r.valida is False
    assert "lectura_nula" in r.errores


def test_validacion_fuera_de_rango():
    r = validar_lectura_mq2(1500)
    assert r.valida is False
    assert "fuera_de_rango" in r.errores


def test_validacion_valor_valido():
    r = validar_lectura_mq2(450)
    assert r.valida is True
    assert r.valor == 450.0


def test_validacion_cero_absoluto():
    r = validar_lectura_mq2(0)
    assert r.valida is False
    assert "posible_sensor_desconectado" in r.errores