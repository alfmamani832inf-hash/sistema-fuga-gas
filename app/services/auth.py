"""
Autenticacion y control de roles (RNF01, RF09).

Reglas:
  - Las contrasenas se validan contra los hashes de la tabla Usuario.
  - La sesion se guarda en cookie firmada con SECRET_KEY.
  - Los roles son OPERADOR (solo lectura) y ADMINISTRADOR (todo).
"""

from functools import wraps

from flask import flash, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash

from app.models.db import get_db


ROLES_VALIDOS = {"OPERADOR", "ADMINISTRADOR"}


def autenticar(nombre: str, password: str) -> dict | None:
    """
    Verifica credenciales contra la tabla Usuario.
    Devuelve el dict del usuario si son correctas, None si no.
    """
    if not nombre or not password:
        return None
    db = get_db()
    fila = db.execute(
        "SELECT id, nombre, rol, hash FROM Usuario WHERE nombre = ?",
        (nombre,),
    ).fetchone()
    if fila is None:
        return None
    if not check_password_hash(fila["hash"], password):
        return None
    return {"id": fila["id"], "nombre": fila["nombre"], "rol": fila["rol"]}


def iniciar_sesion(usuario: dict) -> None:
    """Guarda los datos del usuario en la sesion de Flask."""
    session.clear()
    session["usuario_id"] = usuario["id"]
    session["usuario_nombre"] = usuario["nombre"]
    session["usuario_rol"] = usuario["rol"]


def cerrar_sesion() -> None:
    """Limpia la sesion."""
    session.clear()


def usuario_actual() -> dict | None:
    """
    Devuelve el dict del usuario logueado o None.
    Tambien lo guarda en `g.usuario` para que las plantillas lo lean.
    """
    if "usuario_id" not in session:
        return None
    return {
        "id": session["usuario_id"],
        "nombre": session.get("usuario_nombre"),
        "rol": session.get("usuario_rol"),
    }


def login_required(vista):
    """Decorador: exige sesion iniciada."""

    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("auth.login", next=request.path))
        return vista(*args, **kwargs)

    return envoltura


def role_required(*roles_permitidos):
    """
    Decorador: exige sesion iniciada y un rol especifico.
    Uso: @role_required("ADMINISTRADOR")
    """

    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if "usuario_id" not in session:
                return redirect(url_for("auth.login", next=request.path))
            rol = session.get("usuario_rol")
            if rol not in roles_permitidos:
                flash("No tiene permisos para esta accion.", "error")
                return redirect(url_for("main.index"))
            return vista(*args, **kwargs)

        return envoltura

    return decorador


def es_admin() -> bool:
    """Atajo para saber si el usuario logueado es administrador."""
    return session.get("usuario_rol") == "ADMINISTRADOR"