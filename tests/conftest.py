"""
Configuracion compartida de pytest.

Crea una app de pruebas con la semilla basica cargada (actuadores,
umbrales, usuarios admin y operador). Provee fixtures `client_admin`
y `client_operador` que simulan sesion iniciada.
"""

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.models.db import get_db


@pytest.fixture()
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test",
        "DATABASE_PATH": str(tmp_path / "t.db"),
    })
    with app.app_context():
        db = get_db()

        # 1) Datos sin parametros (script plano).
        db.executescript(
            """
            INSERT INTO Sensor (tipo, ubicacion_logica, estado)
            VALUES ('MQ-2', 'prueba', 'INICIALIZANDO');

            INSERT INTO Actuador (tipo, estado_reportado)
            VALUES ('ELECTROVALVULA', 'DESCONOCIDO');

            INSERT INTO Configuracion (parametro, valor, fecha_actualizacion)
            VALUES ('mq2_umbral_advertencia', '300', '2026-01-01T00:00:00Z');

            INSERT INTO Configuracion (parametro, valor, fecha_actualizacion)
            VALUES ('mq2_umbral_peligro', '600', '2026-01-01T00:00:00Z');
            """
        )

        # 2) Usuarios con hash (aqui si se pueden usar parametros).
        db.execute(
            "INSERT INTO Usuario (nombre, rol, hash) VALUES (?, ?, ?)",
            ("admin", "ADMINISTRADOR", generate_password_hash("Admin1234")),
        )
        db.execute(
            "INSERT INTO Usuario (nombre, rol, hash) VALUES (?, ?, ?)",
            ("operador", "OPERADOR", generate_password_hash("Operador1234")),
        )
        db.commit()
    return app


@pytest.fixture()
def client(app):
    """Cliente sin sesion (anonimo)."""
    return app.test_client()


@pytest.fixture()
def client_admin(app):
    """Cliente con sesion iniciada como admin."""
    cliente = app.test_client()
    cliente.post("/login", data={"nombre": "admin", "password": "Admin1234"})
    return cliente


@pytest.fixture()
def client_operador(app):
    """Cliente con sesion iniciada como operador."""
    cliente = app.test_client()
    cliente.post("/login", data={"nombre": "operador", "password": "Operador1234"})
    return cliente