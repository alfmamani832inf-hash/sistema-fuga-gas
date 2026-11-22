"""Rutas de autenticacion (login, logout)."""

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.services.auth import (
    autenticar,
    cerrar_sesion,
    iniciar_sesion,
    usuario_actual,
)

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_id" in session:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()
        password = request.form.get("password") or ""
        usuario = autenticar(nombre, password)
        if usuario is None:
            flash("Usuario o contrasena incorrectos.", "error")
            return render_template("login.html", titulo=current_app.config["TITULO_SISTEMA"]), 401
        iniciar_sesion(usuario)
        destino = request.args.get("next") or url_for("main.index")
        # Evita open redirect: solo rutas internas.
        if not destino.startswith("/"):
            destino = url_for("main.index")
        return redirect(destino)

    return render_template("login.html", titulo=current_app.config["TITULO_SISTEMA"])


@bp.route("/logout", methods=["POST", "GET"])
def logout():
    cerrar_sesion()
    flash("Sesion cerrada.", "ok")
    return redirect(url_for("auth.login"))