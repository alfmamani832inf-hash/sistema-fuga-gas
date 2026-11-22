"""Semilla del proyecto."""
import secrets
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash
from app import create_app
from app.models.db import get_db

SENSORES = [("MQ-2", "Camara de prueba"), ("DHT22", "Camara de prueba")]
ACTUADORES = ["ELECTROVALVULA", "BUZZER", "LED"]
CONFIGURACION = [
    ("mq2_umbral_advertencia", "300"),
    ("mq2_umbral_peligro", "600"),
    ("mq2_rango_min", "0"),
    ("mq2_rango_max", "1000"),
    ("intervalo_lectura_seg", "2"),
    ("calibracion_estado", "VALORES SIMULADOS - PENDIENTES DE CALIBRACION REAL"),
]


def ahora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main():
    app = create_app()
    with app.app_context():
        db = get_db()
        for tipo, ubi in SENSORES:
            if not db.execute(
                "SELECT 1 FROM Sensor WHERE tipo=? AND ubicacion_logica=?",
                (tipo, ubi),
            ).fetchone():
                db.execute(
                    "INSERT INTO Sensor (tipo, ubicacion_logica, estado) "
                    "VALUES (?, ?, 'INICIALIZANDO')",
                    (tipo, ubi),
                )
        for tipo in ACTUADORES:
            if not db.execute(
                "SELECT 1 FROM Actuador WHERE tipo=?", (tipo,)
            ).fetchone():
                db.execute(
                    "INSERT INTO Actuador (tipo, estado_reportado) "
                    "VALUES (?, 'DESCONOCIDO')",
                    (tipo,),
                )
        for param, val in CONFIGURACION:
            if not db.execute(
                "SELECT 1 FROM Configuracion WHERE parametro=?", (param,)
            ).fetchone():
                db.execute(
                    "INSERT INTO Configuracion "
                    "(parametro, valor, fecha_actualizacion) VALUES (?, ?, ?)",
                    (param, val, ahora()),
                )
        generadas = []
        for nombre, rol, pw in [
            (app.config["ADMIN_USUARIO"], "ADMINISTRADOR", app.config["ADMIN_PASSWORD"]),
            (app.config["OPERADOR_USUARIO"], "OPERADOR", app.config["OPERADOR_PASSWORD"]),
        ]:
            if db.execute(
                "SELECT 1 FROM Usuario WHERE nombre=?", (nombre,)
            ).fetchone():
                continue
            if not pw:
                pw = secrets.token_urlsafe(12)
                generadas.append((nombre, rol, pw))
            db.execute(
                "INSERT INTO Usuario (nombre, rol, hash) VALUES (?, ?, ?)",
                (nombre, rol, generate_password_hash(pw)),
            )
        db.commit()

    print("=" * 60)
    print("SEMILLA APLICADA")
    print("=" * 60)
    print(f"BD: {app.config['DATABASE_PATH']}")
    for n, r, p in generadas:
        print(f"  {n} ({r}): {p}")
    print("Historial de lecturas/eventos: VACIO (no se inventan datos).")


if __name__ == "__main__":
    main()