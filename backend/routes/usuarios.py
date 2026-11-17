"""Rutas de gestión de usuarios y del selector de responsables.

La gestión de cuentas está reservada al Administrador (RN-01). El selector de
responsables se expone a cualquier usuario autenticado porque alimenta el
formulario de incidencias.
"""

import logging
from typing import Any, Dict, List

import pymysql
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from db import obtener_conexion_db
from routes.auth import requerir_token_y_rol
from routes.comunes import (
    ROLES_VALIDOS,
    formatear_fecha,
    respuesta_error,
    validar_correo,
    validar_entero,
    validar_enum,
    validar_texto,
)

usuarios_bp = Blueprint("usuarios", __name__)
registro = logging.getLogger(__name__)

LONGITUD_NOMBRE = 100
LONGITUD_CORREO = 100
LONGITUD_CONTRASENA = 128
LONGITUD_MINIMA_CONTRASENA = 8


def _normalizar_activo(valor: Any) -> Any:
    """Convierte un valor booleano/0-1 a entero, o devuelve None si es inválido."""
    if isinstance(valor, bool):
        return 1 if valor else 0
    if isinstance(valor, int) and valor in (0, 1):
        return valor
    if isinstance(valor, str):
        texto = valor.strip().lower()
        if texto in {"1", "true"}:
            return 1
        if texto in {"0", "false"}:
            return 0
    return None


@usuarios_bp.route("/api/usuarios", methods=["GET"])
@requerir_token_y_rol(roles_permitidos=["Administrador"])
def listar_usuarios(usuario_autenticado: Dict[str, Any]):
    """Lista las cuentas de usuario con filtros opcionales (solo Admin)."""
    condiciones: List[str] = []
    parametros: List[Any] = []

    if "rol" in request.args:
        rol, error = validar_enum(
            request.args, "rol", ROLES_VALIDOS, obligatorio=True
        )
        if error:
            return respuesta_error(error, 400)
        condiciones.append("rol = %s")
        parametros.append(rol)

    if "activo" in request.args:
        activo = _normalizar_activo(request.args.get("activo"))
        if activo is None:
            return respuesta_error(
                "El filtro 'activo' debe ser 0 o 1.", 400
            )
        condiciones.append("activo = %s")
        parametros.append(activo)

    sql = (
        "SELECT id, nombre, correo, rol, id_estudiante, activo, creado_en "
        "FROM usuarios"
    )
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)
    sql += " ORDER BY id ASC"

    conexion = obtener_conexion_db()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql, parametros)
            filas = cursor.fetchall()

        datos = [
            {
                "id": fila["id"],
                "nombre": fila["nombre"],
                "correo": fila["correo"],
                "rol": fila["rol"],
                "id_estudiante": fila["id_estudiante"],
                "activo": fila["activo"],
                "creado_en": formatear_fecha(fila["creado_en"]),
            }
            for fila in filas
        ]

        return jsonify(
            {
                "mensaje": "Usuarios consultados correctamente.",
                "total": len(datos),
                "datos": datos,
            }
        ), 200

    except Exception:
        registro.exception("Error al consultar usuarios.")
        return respuesta_error("Error interno al consultar usuarios.", 500)

    finally:
        conexion.close()


@usuarios_bp.route("/api/usuarios", methods=["POST"])
@requerir_token_y_rol(roles_permitidos=["Administrador"])
def crear_usuario(usuario_autenticado: Dict[str, Any]):
    """Crea una cuenta de usuario (solo Admin)."""
    datos = request.get_json(silent=True)

    if not isinstance(datos, dict):
        return respuesta_error(
            "El cuerpo de la petición debe ser un objeto JSON.", 400
        )

    nombre, error = validar_texto(
        datos, "nombre", obligatorio=True, maximo=LONGITUD_NOMBRE
    )
    if error:
        return respuesta_error(error, 400)

    correo, error = validar_texto(
        datos, "correo", obligatorio=True, maximo=LONGITUD_CORREO
    )
    if error:
        return respuesta_error(error, 400)

    if not validar_correo(correo):
        return respuesta_error(
            "El campo 'correo' no tiene un formato válido.", 400
        )

    contrasena, error = validar_texto(
        datos, "contrasena", obligatorio=True, maximo=LONGITUD_CONTRASENA
    )
    if error:
        return respuesta_error(error, 400)

    if len(contrasena) < LONGITUD_MINIMA_CONTRASENA:
        return respuesta_error(
            "La contraseña debe tener al menos "
            f"{LONGITUD_MINIMA_CONTRASENA} caracteres.",
            400,
        )

    rol, error = validar_enum(
        datos, "rol", ROLES_VALIDOS, obligatorio=True
    )
    if error:
        return respuesta_error(error, 400)

    if "activo" in datos and datos["activo"] is not None:
        activo = _normalizar_activo(datos["activo"])
        if activo is None:
            return respuesta_error(
                "El campo 'activo' debe ser un valor booleano.", 400
            )
    else:
        activo = 1

    id_estudiante = None
    if rol == "Estudiante":
        id_estudiante, error = validar_entero(
            datos, "id_estudiante", obligatorio=True
        )
        if error:
            return respuesta_error(
                "El campo 'id_estudiante' es obligatorio para el rol "
                "Estudiante.",
                400,
            )
    elif datos.get("id_estudiante") is not None:
        return respuesta_error(
            "El campo 'id_estudiante' solo aplica al rol Estudiante.", 400
        )

    conexion = obtener_conexion_db()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM usuarios WHERE correo = %s LIMIT 1",
                (correo,),
            )
            if cursor.fetchone():
                return respuesta_error("El correo ya está registrado.", 409)

            if id_estudiante is not None:
                cursor.execute(
                    "SELECT id FROM estudiantes WHERE id = %s",
                    (id_estudiante,),
                )
                if not cursor.fetchone():
                    return respuesta_error(
                        "El estudiante indicado no existe.", 404
                    )

                cursor.execute(
                    "SELECT id FROM usuarios WHERE id_estudiante = %s",
                    (id_estudiante,),
                )
                if cursor.fetchone():
                    return respuesta_error(
                        "El estudiante ya está vinculado a otra cuenta.", 409
                    )

            cursor.execute(
                """
                INSERT INTO usuarios (
                    nombre, correo, contrasena, rol, id_estudiante, activo
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    nombre,
                    correo,
                    generate_password_hash(contrasena),
                    rol,
                    id_estudiante,
                    activo,
                ),
            )
            id_nuevo_usuario = cursor.lastrowid
            conexion.commit()

        return jsonify(
            {
                "mensaje": "Usuario creado correctamente.",
                "datos": {"id": id_nuevo_usuario},
            }
        ), 201

    except pymysql.err.IntegrityError:
        conexion.rollback()
        return respuesta_error(
            "El correo o el estudiante ya están vinculados a otra cuenta.", 409
        )

    except Exception:
        conexion.rollback()
        registro.exception("Error al crear usuario.")
        return respuesta_error("Error interno al crear usuario.", 500)

    finally:
        conexion.close()


@usuarios_bp.route("/api/usuarios/<int:id_usuario>/estado", methods=["PUT"])
@requerir_token_y_rol(roles_permitidos=["Administrador"])
def cambiar_estado_usuario(
    usuario_autenticado: Dict[str, Any],
    id_usuario: int,
):
    """Activa o desactiva una cuenta (solo Admin, sin autodesactivación)."""
    datos = request.get_json(silent=True)

    if not isinstance(datos, dict):
        return respuesta_error(
            "El cuerpo de la petición debe ser un objeto JSON.", 400
        )

    if "activo" not in datos or not isinstance(datos["activo"], bool):
        return respuesta_error(
            "El campo 'activo' debe ser un valor booleano.", 400
        )

    nuevo_activo = 1 if datos["activo"] else 0

    if id_usuario == usuario_autenticado["id"] and nuevo_activo == 0:
        return respuesta_error(
            "El Administrador no puede desactivar su propia cuenta.", 409
        )

    conexion = obtener_conexion_db()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM usuarios WHERE id = %s",
                (id_usuario,),
            )
            if not cursor.fetchone():
                return respuesta_error(
                    "El usuario indicado no existe.", 404
                )

            cursor.execute(
                "UPDATE usuarios SET activo = %s WHERE id = %s",
                (nuevo_activo, id_usuario),
            )
            conexion.commit()

        accion = "activado" if nuevo_activo == 1 else "desactivado"
        return jsonify(
            {
                "mensaje": f"Usuario {accion} correctamente.",
                "datos": {"id": id_usuario, "activo": nuevo_activo},
            }
        ), 200

    except Exception:
        conexion.rollback()
        registro.exception("Error al cambiar el estado del usuario.")
        return respuesta_error(
            "Error interno al cambiar el estado del usuario.", 500
        )

    finally:
        conexion.close()


@usuarios_bp.route("/api/responsables", methods=["GET"])
@requerir_token_y_rol()
def listar_responsables(usuario_autenticado: Dict[str, Any]):
    """Devuelve los responsables activos para el formulario de incidencias."""
    conexion = obtener_conexion_db()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nombre, correo
                FROM usuarios
                WHERE rol = 'Personal Responsable' AND activo = 1
                ORDER BY nombre ASC
                """
            )
            responsables = cursor.fetchall()

        return jsonify(
            {
                "mensaje": "Responsables consultados correctamente.",
                "datos": responsables,
            }
        ), 200

    except Exception:
        registro.exception("Error al consultar responsables.")
        return respuesta_error(
            "Error interno al consultar responsables.", 500
        )

    finally:
        conexion.close()
