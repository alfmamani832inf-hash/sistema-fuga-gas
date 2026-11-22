"""Pruebas de autenticacion, roles y configuracion (M7)."""

import pytest

from app.services.auth import autenticar
from app.services.configuracion import (
    actualizar_configuracion,
    listar_configuracion,
)


# ---------------------------------------------------------------------------
# Autenticacion
# ---------------------------------------------------------------------------

def test_login_correcto_redirige(app, client):
    r = client.post("/login", data={"nombre": "admin", "password": "Admin1234"})
    assert r.status_code == 302
    assert "/" in r.headers["Location"]


def test_login_incorrecto_retorna_401(app, client):
    r = client.post("/login", data={"nombre": "admin", "password": "malo"})
    assert r.status_code == 401


def test_login_usuario_inexistente_retorna_401(app, client):
    r = client.post("/login", data={"nombre": "fantasma", "password": "x"})
    assert r.status_code == 401


def test_autenticar_devuelve_usuario(app):
    with app.app_context():
        u = autenticar("admin", "Admin1234")
        assert u is not None
        assert u["rol"] == "ADMINISTRADOR"


def test_autenticar_password_mala(app):
    with app.app_context():
        assert autenticar("admin", "otra") is None


def test_logout_limpia_sesion(app, client_admin):
    r = client_admin.post("/logout", follow_redirects=False)
    assert r.status_code == 302
    r2 = client_admin.get("/")
    assert r2.status_code == 302
    assert "/login" in r2.headers["Location"]


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

def test_operador_no_puede_forzar_escenario(app, client_operador):
    r = client_operador.post(
        "/api/escenario",
        json={"escenario": "peligro"},
        follow_redirects=False,
    )
    # role_required redirige al panel (302) o devuelve 403. En nuestro caso, 302.
    assert r.status_code in (302, 403)


def test_operador_no_puede_reabrir_valvula(app, client_operador):
    r = client_operador.post("/api/valvula/reabrir", follow_redirects=False)
    assert r.status_code in (302, 403)


def test_operador_no_puede_cambiar_configuracion(app, client_operador):
    r = client_operador.post(
        "/api/configuracion",
        json={"mq2_umbral_peligro": "700"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 403)


def test_admin_si_puede_forzar_escenario(app, client_admin):
    r = client_admin.post("/api/escenario", json={"escenario": "normal"})
    assert r.status_code == 200


def test_admin_si_puede_cambiar_configuracion(app, client_admin):
    r = client_admin.post(
        "/api/configuracion",
        json={"mq2_umbral_peligro": "700"},
    )
    assert r.status_code == 200
    datos = r.get_json()
    assert datos["configuracion"]["mq2_umbral_peligro"]["valor"] == "700"


def test_admin_puede_ver_configuracion(app, client_admin):
    r = client_admin.get("/api/configuracion")
    assert r.status_code == 200
    datos = r.get_json()
    assert "mq2_umbral_peligro" in datos


def test_operador_puede_ver_configuracion(app, client_operador):
    r = client_operador.get("/api/configuracion")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------

def test_umbral_advertencia_menor_que_peligro(app):
    with app.app_context():
        with pytest.raises(ValueError):
            actualizar_configuracion(
                __import__("app.models.db", fromlist=["get_db"]).get_db(),
                {"mq2_umbral_advertencia": "700", "mq2_umbral_peligro": "600"},
            )


def test_actualizar_configuracion_ok(app):
    with app.app_context():
        from app.models.db import get_db
        db = get_db()
        actualizar_configuracion(db, {"mq2_umbral_advertencia": "350"})
        c = listar_configuracion(db)
        assert c["mq2_umbral_advertencia"]["valor"] == "350"