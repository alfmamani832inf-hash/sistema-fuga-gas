"""Fabrica de la aplicacion Flask."""
import secrets
from pathlib import Path

from flask import Flask

from .config import Config
from .models import db


def create_app(test_config=None):
    raiz = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(raiz / "templates"),
        static_folder=str(raiz / "static"),
    )
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = secrets.token_hex(32)
        app.logger.warning("SECRET_KEY no definida en .env.")

    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    with app.app_context():
        db.init_db()

    # Blueprints
    from .routes.auth import bp as auth_bp
    from .routes.main import bp as main_bp
    from .routes.api import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # Context processor: expone "usuario" y "es_admin" a todas las plantillas.
    @app.context_processor
    def inyectar_usuario():
        from .services.auth import usuario_actual
        usuario = usuario_actual()
        return {
            "usuario": usuario,
            "es_admin": (usuario or {}).get("rol") == "ADMINISTRADOR",
        }

    return app