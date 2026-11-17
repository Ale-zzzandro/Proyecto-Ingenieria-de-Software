"""Fábrica de la aplicación Flask del sistema de incidencias escolares."""

import logging

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

import config
from routes.auth import auth_bp
from routes.estudiantes import estudiantes_bp
from routes.incidencias import incidencias_bp
from routes.panel import panel_bp
from routes.usuarios import usuarios_bp


def crear_app() -> Flask:
    """Crea y configura la aplicación Flask.

    Returns:
        Flask: Aplicación con CORS restringido, logging y blueprints.

    Raises:
        RuntimeError: Si faltan secretos obligatorios en la configuración.
    """
    config.validar_secretos()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["DEBUG"] = config.FLASK_DEBUG

    CORS(app, origins=config.CORS_ORIGINS)

    logging.basicConfig(
        level=logging.DEBUG if config.FLASK_DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    registro = logging.getLogger(__name__)

    app.register_blueprint(auth_bp)
    app.register_blueprint(estudiantes_bp)
    app.register_blueprint(incidencias_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(panel_bp)

    @app.errorhandler(Exception)
    def manejar_error_no_controlado(error: Exception):
        """Devuelve un 500 genérico sin exponer detalles internos."""
        if isinstance(error, HTTPException):
            return error
        registro.exception("Error no controlado en la API.")
        return jsonify({"mensaje": "Error interno del servidor."}), 500

    return app


app = crear_app()


if __name__ == "__main__":
    print("Servidor backend iniciado en http://localhost:5000")
    app.run(debug=config.FLASK_DEBUG, port=5000)
