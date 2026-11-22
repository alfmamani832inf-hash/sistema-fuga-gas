"""Pruebas del M1 (actualizadas a M7: requieren login)."""

from app.models.db import get_db


def test_tablas(app):
    with app.app_context():
        db = get_db()
        nombres = {f["name"] for f in db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()}
    for t in {"Sensor", "Lectura", "Evento", "Actuador", "Configuracion", "Usuario"}:
        assert t in nombres


def test_historial_inicia_vacio(app):
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) AS c FROM Lectura").fetchone()["c"] == 0
        assert db.execute("SELECT COUNT(*) AS c FROM Evento").fetchone()["c"] == 0


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["estado"] == "ok"


def test_panel_redirige_a_login_sin_sesion(client):
    r = client.get("/")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_panel_con_sesion_muestra_modo_simulacion(client_admin):
    r = client_admin.get("/")
    assert r.status_code == 200
    contenido = r.get_data(as_text=True)
    assert "MODO SIMULACIÓN" in contenido or "MODO SIMULACION" in contenido