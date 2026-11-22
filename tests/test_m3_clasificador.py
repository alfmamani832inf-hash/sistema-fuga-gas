"""Pruebas del clasificador de estados y la alarma virtual (M3)."""

import pytest

from app import create_app
from app.models.db import get_db
from app.services.alarma import accion_para_estado, accion_para_estado_dict
from app.services.clasificador import (
    EstadoSistema,
    clasificar_lectura,
    leer_umbrales_desde_bd,
)


@pytest.fixture()
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test",
        "DATABASE_PATH": str(tmp_path / "t.db"),
    })


# ---------------------------------------------------------------------------
# Clasificador
# ---------------------------------------------------------------------------

def _lectura(valor, valida=True, errores=None):
    return {"valida": valida, "valor_mq2": valor, "errores": errores or []}


def test_normal_por_debajo_de_300():
    assert clasificar_lectura(_lectura(150)) == EstadoSistema.NORMAL


def test_normal_justo_en_el_limite_299():
    assert clasificar_lectura(_lectura(299)) == EstadoSistema.NORMAL


def test_advertencia_justo_en_el_limite_300():
    assert clasificar_lectura(_lectura(300)) == EstadoSistema.ADVERTENCIA


def test_advertencia_599():
    assert clasificar_lectura(_lectura(599)) == EstadoSistema.ADVERTENCIA


def test_peligro_justo_en_el_limite_600():
    assert clasificar_lectura(_lectura(600)) == EstadoSistema.PELIGRO


def test_peligro_valor_alto():
    assert clasificar_lectura(_lectura(950)) == EstadoSistema.PELIGRO


def test_fallo_sensor_por_validacion_invalida():
    assert clasificar_lectura(_lectura(None, valida=False)) == EstadoSistema.FALLO_SENSOR


def test_fallo_sensor_por_valor_nulo():
    assert clasificar_lectura(_lectura(None, valida=True)) == EstadoSistema.FALLO_SENSOR


def test_umbrales_custom():
    # Si los umbrales son 100 y 200, un valor de 250 debe ser PELIGRO.
    estado = clasificar_lectura(_lectura(250), umbral_advertencia=100, umbral_peligro=200)
    assert estado == EstadoSistema.PELIGRO


def test_umbrales_desde_bd(app):
    with app.app_context():
        db = get_db()
        # La semilla no se ejecuto en tmp_path, asi que usamos los defaults.
        adv, pel = leer_umbrales_desde_bd(db)
        assert adv == 300.0
        assert pel == 600.0


def test_umbrales_corruptos_en_bd(app):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO Configuracion (parametro, valor, fecha_actualizacion) "
            "VALUES ('mq2_umbral_advertencia', 'abc', '2026-01-01T00:00:00Z')"
        )
        db.commit()
        adv, pel = leer_umbrales_desde_bd(db)
        # Al ser invalido, debe volver al default.
        assert adv == 300.0
        assert pel == 600.0


# ---------------------------------------------------------------------------
# Alarma
# ---------------------------------------------------------------------------

def test_alarma_normal():
    a = accion_para_estado(EstadoSistema.NORMAL)
    assert a.color_led == "verde"
    assert a.patron_led == "fijo"
    assert a.sonido == "silencio"


def test_alarma_advertencia():
    a = accion_para_estado(EstadoSistema.ADVERTENCIA)
    assert a.color_led == "amarillo"
    assert a.patron_led == "parpadeante"
    assert a.sonido == "pitido"


def test_alarma_peligro():
    a = accion_para_estado(EstadoSistema.PELIGRO)
    assert a.color_led == "rojo"
    assert a.patron_led == "fijo"
    assert a.sonido == "intermitente"


def test_alarma_fallo_sensor():
    a = accion_para_estado(EstadoSistema.FALLO_SENSOR)
    assert a.color_led == "rojo"
    assert a.patron_led == "parpadeante"
    assert a.sonido == "largo"


def test_alarma_serializable():
    d = accion_para_estado_dict(EstadoSistema.PELIGRO)
    assert d["estado"] == "PELIGRO"
    assert d["color_led"] == "rojo"
    assert isinstance(d["frecuencia_sonido_hz"], float)
