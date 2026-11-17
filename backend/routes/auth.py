"""Módulo de control de acceso y autenticación de usuarios (RBAC).

Gestiona la emisión de tokens JWT y los decoradores de seguridad para restringir
el acceso a los endpoints de la API según el rol del usuario autenticado.
"""

import datetime
import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import jwt
from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash

import config
from db import obtener_conexion_db

auth_bp = Blueprint("auth", __name__)
registro = logging.getLogger(__name__)


def _extraer_token(encabezado: str) -> str:
    """Extrae el token de un encabezado `Authorization`."""
    partes = encabezado.split()
    if len(partes) == 2 and partes[0].lower() == "bearer":
        return partes[1]
    if len(partes) == 1:
        return partes[0]
    raise jwt.InvalidTokenError("Encabezado de autorización inválido.")


def requerir_token_y_rol(roles_permitidos: Optional[List[str]] = None) -> Callable:
    """Decorador middleware para validar JWT y verificar permisos por rol.

    Args:
        roles_permitidos (list, optional): Lista de roles autorizados para el
            endpoint. Si es None, permite cualquier usuario autenticado.

    Returns:
        Callable: Función decorada con validación de seguridad.
    """

    def decorador(func: Callable) -> Callable:
        @wraps(func)
        def funcion_decorada(*args, **kwargs):
            encabezado_auth = request.headers.get("Authorization")

            if not encabezado_auth:
                return jsonify(
                    {"mensaje": "Acceso denegado. Token de sesión faltante."}
                ), 401

            try:
                token = _extraer_token(encabezado_auth)
                datos_usuario = jwt.decode(
                    token,
                    config.JWT_SECRET_KEY,
                    algorithms=["HS256"],
                )

                if "id" not in datos_usuario or "rol" not in datos_usuario:
                    raise jwt.InvalidTokenError("Payload incompleto.")

                if (
                    roles_permitidos
                    and datos_usuario["rol"] not in roles_permitidos
                ):
                    return jsonify(
                        {"mensaje": "Permisos insuficientes para esta operación."}
                    ), 403

            except jwt.ExpiredSignatureError:
                return jsonify({"mensaje": "La sesión ha expirado."}), 401
            except (jwt.InvalidTokenError, IndexError):
                return jsonify(
                    {"mensaje": "Token de autenticación inválido."}
                ), 401

            return func(datos_usuario, *args, **kwargs)

        return funcion_decorada

    return decorador


def _buscar_usuario(identificador: str) -> Optional[Dict[str, Any]]:
    """Busca un usuario por correo o, si es Estudiante, por matrícula."""
    conexion = obtener_conexion_db()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.nombre, u.correo, u.contrasena, u.rol,
                       u.id_estudiante, u.activo
                FROM usuarios AS u
                LEFT JOIN estudiantes AS e ON e.id = u.id_estudiante
                WHERE u.correo = %s
                   OR (u.rol = 'Estudiante' AND e.matricula = %s)
                LIMIT 1
                """,
                (identificador, identificador),
            )
            return cursor.fetchone()
    finally:
        conexion.close()


def _contrasena_valida(usuario: Dict[str, Any], contrasena: str) -> bool:
    """Compara la contraseña recibida con el hash almacenado."""
    try:
        return check_password_hash(usuario["contrasena"], contrasena)
    except (TypeError, ValueError):
        return False


@auth_bp.route("/api/login", methods=["POST"])
def iniciar_sesion():
    """Procesa las credenciales de acceso e inicia sesión en el sistema.

    Returns:
        Response: Objeto JSON con el token JWT y los datos públicos del usuario.
    """
    datos_peticion = request.get_json(silent=True)

    if not isinstance(datos_peticion, dict):
        return jsonify(
            {"mensaje": "El cuerpo de la petición debe ser un objeto JSON."}
        ), 400

    identificador = datos_peticion.get("correo")
    contrasena_usuario = datos_peticion.get("contrasena")

    if (
        not isinstance(identificador, str)
        or not identificador.strip()
        or not isinstance(contrasena_usuario, str)
        or not contrasena_usuario
    ):
        return jsonify(
            {"mensaje": "Correo o matrícula y contraseña obligatorios."}
        ), 400

    identificador = identificador.strip()

    try:
        usuario_encontrado = _buscar_usuario(identificador)

        # Mensaje genérico: no se revela si el usuario existe o está inactivo
        if (
            not usuario_encontrado
            or not _contrasena_valida(usuario_encontrado, contrasena_usuario)
            or not usuario_encontrado.get("activo")
        ):
            return jsonify(
                {"mensaje": "Credenciales de acceso incorrectas."}
            ), 401

        tiempo_expiracion = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=config.JWT_EXPIRACION_HORAS)

        payload_jwt = {
            "id": usuario_encontrado["id"],
            "nombre": usuario_encontrado["nombre"],
            "rol": usuario_encontrado["rol"],
            "id_estudiante": usuario_encontrado["id_estudiante"],
            "exp": tiempo_expiracion,
        }

        token_emitido = jwt.encode(
            payload_jwt,
            config.JWT_SECRET_KEY,
            algorithm="HS256",
        )

        return jsonify(
            {
                "mensaje": "Sesión iniciada correctamente.",
                "token": token_emitido,
                "usuario": {
                    "id": usuario_encontrado["id"],
                    "nombre": usuario_encontrado["nombre"],
                    "correo": usuario_encontrado["correo"],
                    "rol": usuario_encontrado["rol"],
                    "id_estudiante": usuario_encontrado["id_estudiante"],
                },
            }
        ), 200

    except Exception:
        registro.exception("Error interno al iniciar sesión.")
        return jsonify({"mensaje": "Error interno del servidor."}), 500
