"""
Pruebas de la API REST (M9).

Verifica el flujo completo desde el cliente HTTP (caja negra):
  - /api/salud, /api/estado, /api/eventos.
  - Forzado de escenario (solo admin).
  - Proteccion de endpoints por login y rol.
"""

import pytest


# ---------------------------------------------------------------------------
# Acceso sin sesion
# ---------------------------------------------------------------------------

def test_api_estado_sin_sesion_redirige(client):
    r = client.get("/api/estado")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_api_escenario_sin_sesion_redirige(client):
    r = client.post("/api/escenario", json={"escenario": "normal"})
    assert r.status_code == 302


# ---------------------------------------------------------------------------
# Operador (solo lectura)
# ---------------------------------------------------------------------------

def test_operador_puede_ver_estado(client_operador):
    r = client_operador.get("/api/estado")
    assert r.status_code == 200
    datos = r.get_json()
    assert "estado" in datos
    assert "alarma" in datos
    assert "diagnostico" in datos
    assert "valvula" in datos


def test_operador_puede_ver_eventos(client_operador):
    r = client_operador.get("/api/eventos")
    assert r.status_code == 200
    datos = r.get_json()
    assert "eventos" in datos


def test_operador_no_puede_forzar_escenario(client_operador):
    r = client_operador.post(
        "/api/escenario", json={"escenario": "peligro"}, follow_redirects=False
    )
    assert r.status_code in (302, 403)


def test_operador_no_puede_reabrir_valvula(client_operador):
    r = client_operador.post("/api/valvula/reabrir", follow_redirects=False)
    assert r.status_code in (302, 403)


# ---------------------------------------------------------------------------
# Administrador (control total)
# ---------------------------------------------------------------------------

def test_admin_puede_forzar_escenario(client_admin):
    r = client_admin.post("/api/escenario", json={"escenario": "peligro"})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


def test_admin_puede_reabrir_valvula(client_admin):
    # Primero cerramos: forzamos peligro.
    client_admin.post("/api/escenario", json={"escenario": "peligro"})
    client_admin.get("/api/estado")  # fuerza una lectura que cierra la valvula

    # Ahora reabrimos.
    r = client_admin.post("/api/valvula/reabrir")
    assert r.status_code == 200
    datos = r.get_json()
    assert datos["confirmado"] is True
    assert datos["estado_reportado"] == "ABIERTA"


def test_admin_puede_ver_salud(client_admin):
    r = client_admin.get("/api/salud")
    assert r.status_code == 200
    datos = r.get_json()
    assert datos["estado"] == "ok"
    assert datos["version"].startswith("1.0-")


# ---------------------------------------------------------------------------
# Flujo completo desde HTTP
# ---------------------------------------------------------------------------

def test_flujo_normal_a_peligro_via_api(client_admin):
    """Simula el flujo del panel: normal -> peligro -> valvula cerrada."""
    # 1) Forzar normal
    client_admin.post("/api/escenario", json={"escenario": "normal"})
    r1 = client_admin.get("/api/estado").get_json()
    assert r1["estado"] == "NORMAL"

    # 2) Forzar peligro
    client_admin.post("/api/escenario", json={"escenario": "peligro"})
    r2 = client_admin.get("/api/estado").get_json()
    assert r2["estado"] == "PELIGRO"
    assert r2["valvula_estado_reportado"] == "CERRADA"

    # 3) Consultar eventos: debe haber al menos uno de PELIGRO.
    eventos = client_admin.get("/api/eventos").get_json()["eventos"]
    assert any(e["estado"] == "PELIGRO" for e in eventos)