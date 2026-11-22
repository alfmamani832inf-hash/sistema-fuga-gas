"""Configuracion central leida desde .env."""
import os
from pathlib import Path
from dotenv import load_dotenv

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ_PROYECTO / ".env")


def _ruta_bd(valor: str) -> str:
    ruta = Path(valor)
    if not ruta.is_absolute():
        ruta = RAIZ_PROYECTO / ruta
    return str(ruta)


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    DATABASE_PATH = _ruta_bd(os.getenv("DATABASE_PATH", "instance/gas_monitor.db"))
    ADMIN_USUARIO = os.getenv("ADMIN_USUARIO", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
    OPERADOR_USUARIO = os.getenv("OPERADOR_USUARIO", "operador")
    OPERADOR_PASSWORD = os.getenv("OPERADOR_PASSWORD", "")
    MODO_SIMULACION = os.getenv("MODO_SIMULACION", "1") == "1"
    
    # Título actualizado (sin el "Proyecto 1.0 -")
    TITULO_SISTEMA = "Sistema de Control y Deteccion por Fuga de Gas"