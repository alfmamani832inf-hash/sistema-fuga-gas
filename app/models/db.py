"""Acceso a SQLite."""
import sqlite3
from flask import current_app, g

ESQUEMA_SQL = """
CREATE TABLE IF NOT EXISTS Sensor (
    id_sensor INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    ubicacion_logica TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'INICIALIZANDO'
);
CREATE TABLE IF NOT EXISTS Lectura (
    id_lectura INTEGER PRIMARY KEY AUTOINCREMENT,
    id_sensor INTEGER NOT NULL,
    fecha_hora TEXT NOT NULL,
    valor REAL,
    unidad TEXT NOT NULL DEFAULT 'ppm_simulado',
    FOREIGN KEY (id_sensor) REFERENCES Sensor (id_sensor)
);
CREATE TABLE IF NOT EXISTS Evento (
    id_evento INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora TEXT NOT NULL,
    estado TEXT NOT NULL,
    descripcion TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS Actuador (
    id_actuador INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    estado_reportado TEXT NOT NULL DEFAULT 'DESCONOCIDO'
);
CREATE TABLE IF NOT EXISTS Configuracion (
    id_config INTEGER PRIMARY KEY AUTOINCREMENT,
    parametro TEXT NOT NULL UNIQUE,
    valor TEXT NOT NULL,
    fecha_actualizacion TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS Usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    rol TEXT NOT NULL CHECK (rol IN ('OPERADOR', 'ADMINISTRADOR')),
    hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lectura_fecha ON Lectura (fecha_hora);
CREATE INDEX IF NOT EXISTS idx_evento_fecha ON Evento (fecha_hora);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conexion = sqlite3.connect(current_app.config["DATABASE_PATH"])
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys = ON")
        g.db = conexion
    return g.db


def close_db(_excepcion=None) -> None:
    conexion = g.pop("db", None)
    if conexion is not None:
        conexion.close()


def init_db() -> None:
    db = get_db()
    db.executescript(ESQUEMA_SQL)
    db.commit()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
