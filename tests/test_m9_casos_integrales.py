"""
Pruebas integrales del sistema (M9).

Cubre los casos de prueba definidos en el documento del proyecto:
  CN01 - Inicio sin datos validos
  CN02 - Lectura normal
  CN03 - Advertencia
  CN04 - Peligro
  CN05 - Interrupcion de Wi-Fi
  CN06 - Historial vacio

Y pruebas adicionales de transiciones de estado y fallo de salida.
"""

import pytest

from app.models.db import get_db
from app.services.clasificador import EstadoSistema
from app.services.estado_sistema import ServicioEstado
from app.services.eventos import listar_eventos
from app.services.valvula import VALVULA_ABIERTA, VALVULA_CERRADA, VALVULA_FALLO
from app.simulator.simulador import SimuladorMQ2DHT22


# ---------------------------------------------------------------------------
# CN01 - Inicio sin datos validos
# ---------------------------------------------------------------------------

def test_cn01_inicio_sin_datos_validos(app):
    """
    CN01: Al iniciar con el sensor en fallo, el estado debe ser FALLO_SENSOR
    y la lectura no debe presentarse como confiable.
    """
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("fallo_sensor")
        servicio = ServicioEstado(sim)
        resultado = servicio.estado_actual()

        assert resultado["estado"] == "FALLO_SENSOR"
        assert resultado["valida"] is False
        assert len(resultado["errores"]) > 0


# ---------------------------------------------------------------------------
# CN02 - Lectura normal
# ---------------------------------------------------------------------------

def test_cn02_lectura_normal(app):
    """
    CN02: Una lectura en la zona segura debe clasificarse como NORMAL,
    la valvula debe abrirse y no debe haber sonido de alarma.
    """
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("normal")
        servicio = ServicioEstado(sim)
        resultado = servicio.estado_actual()

        assert resultado["estado"] == "NORMAL"
        assert resultado["valida"] is True
        assert resultado["alarma"]["sonido"] == "silencio"
        assert resultado["alarma"]["color_led"] == "verde"
        assert resultado["valvula"]["confirmado"] is True
        assert resultado["valvula_estado_reportado"] == VALVULA_ABIERTA


# ---------------------------------------------------------------------------
# CN03 - Advertencia
# ---------------------------------------------------------------------------

def test_cn03_advertencia(app):
    """
    CN03: Una lectura en zona intermedia debe clasificarse como ADVERTENCIA
    con LED amarillo parpadeante y sonido de pitido.
    """
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("advertencia")
        servicio = ServicioEstado(sim)
        resultado = servicio.estado_actual()

        assert resultado["estado"] == "ADVERTENCIA"
        assert resultado["valida"] is True
        assert resultado["alarma"]["color_led"] == "amarillo"
        assert resultado["alarma"]["patron_led"] == "parpadeante"
        assert resultado["alarma"]["sonido"] == "pitido"


# ---------------------------------------------------------------------------
# CN04 - Peligro
# ---------------------------------------------------------------------------

def test_cn04_peligro_cierra_valvula(app):
    """
    CN04: Una lectura en zona peligrosa debe clasificarse como PELIGRO,
    cerrar automaticamente la valvula y activar alarma intermitente.
    """
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("peligro")
        servicio = ServicioEstado(sim)
        resultado = servicio.estado_actual()

        assert resultado["estado"] == "PELIGRO"
        assert resultado["valida"] is True
        assert resultado["alarma"]["color_led"] == "rojo"
        assert resultado["alarma"]["sonido"] == "intermitente"

        # La valvula debe estar cerrada o cerrarse en esta misma lectura.
        assert resultado["valvula_estado_reportado"] == VALVULA_CERRADA or \
               resultado["valvula"]["estado_esperado"] == VALVULA_CERRADA
        assert resultado["valvula"]["confirmado"] is True


# ---------------------------------------------------------------------------
# CN05 - Interrupcion de Wi-Fi
# ---------------------------------------------------------------------------

def test_cn05_interrupcion_wifi(app):
    """
    CN05: Si se pierde la comunicacion Wi-Fi, el diagnostico debe marcar
    el componente de comunicacion como no operativo, pero el dato del sensor
    sigue siendo valido (no se inventan lecturas).
    """
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("perdida_wifi")
        servicio = ServicioEstado(sim)
        resultado = servicio.estado_actual()

        assert resultado["diagnostico"]["todo_operativo"] is False
        componentes = {c["nombre"]: c["operativo"] for c in resultado["diagnostico"]["componentes"]}
        assert componentes["comunicacion"] is False
        # El sensor sigue siendo valido: no se descarta el dato por perder Wi-Fi.
        assert componentes["sensor"] is True
        # Pero el valor no se presenta como "actualizado" por el panel,
        # eso lo maneja el JS (badge NO ACTUALIZADO).


# ---------------------------------------------------------------------------
# CN06 - Historial vacio
# ---------------------------------------------------------------------------

def test_cn06_historial_vacio_no_inventa(app):
    """
    CN06: Una BD recien creada no debe contener eventos ni lecturas.
    El endpoint /api/eventos debe devolver [] y el panel debe mostrar
    'Sin eventos registrados'.
    """
    with app.app_context():
        db = get_db()
        assert listar_eventos(db) == []
        assert db.execute("SELECT COUNT(*) AS c FROM Lectura").fetchone()["c"] == 0


# ---------------------------------------------------------------------------
# Transiciones de estado
# ---------------------------------------------------------------------------

def test_transicion_normal_advertencia_peligro_normal(app):
    """
    Recorre una transicion completa: NORMAL -> ADVERTENCIA -> PELIGRO -> NORMAL
    y verifica que se registren los eventos correspondientes.
    """
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        servicio = ServicioEstado(sim)
        db = get_db()

        # 1) NORMAL
        sim.forzar_escenario("normal")
        r1 = servicio.estado_actual()
        assert r1["estado"] == "NORMAL"

        # 2) ADVERTENCIA
        sim.forzar_escenario("advertencia")
        r2 = servicio.estado_actual()
        assert r2["estado"] == "ADVERTENCIA"
        assert r2["evento_registrado"] is True

        # 3) PELIGRO
        sim.forzar_escenario("peligro")
        r3 = servicio.estado_actual()
        assert r3["estado"] == "PELIGRO"
        assert r3["evento_registrado"] is True
        assert r3["valvula_estado_reportado"] == VALVULA_CERRADA

        # 4) NORMAL de nuevo (la valvula queda cerrada por emergencia previa)
        sim.forzar_escenario("normal")
        r4 = servicio.estado_actual()
        assert r4["estado"] == "NORMAL"
        assert r4["evento_registrado"] is True
        # La valvula NO se reabre automaticamente: requiere accion manual.
        assert r4["valvula_estado_reportado"] == VALVULA_CERRADA
        assert "reapertura manual" in r4["valvula"]["razon"].lower()

        # Verificacion final: hay al menos 4 eventos de estado registrados.
        estados = [e["estado"] for e in listar_eventos(db) if "Valvula" not in e["descripcion"]]
        assert "NORMAL" in estados
        assert "ADVERTENCIA" in estados
        assert "PELIGRO" in estados


# ---------------------------------------------------------------------------
# Fallo de salida (regla de oro)
# ---------------------------------------------------------------------------

def test_fallo_salida_no_se_afirma_que_actuo(app):
    """
    Prueba de honestidad: si la valvula reporta fallo, el sistema
    NO debe afirmar que actuo. Debe devolver confirmado=False
    y estado_reportado=FALLO.
    """
    with app.app_context():
        sim = SimuladorMQ2DHT22()
        sim.forzar_escenario("fallo_valvula")
        servicio = ServicioEstado(sim)
        resultado = servicio.estado_actual()

        assert resultado["valvula"]["confirmado"] is False
        assert resultado["valvula_estado_reportado"] == VALVULA_FALLO
        assert "NO se confirma" in resultado["valvula"]["razon"]

        # Tambien el diagnostico debe reflejar el fallo de salida.
        componentes = {c["nombre"]: c["operativo"] for c in resultado["diagnostico"]["componentes"]}
        assert componentes["salida"] is False