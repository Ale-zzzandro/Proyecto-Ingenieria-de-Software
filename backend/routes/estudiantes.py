"""Rutas del catálogo y alta de estudiantes.

Aplica RN-01 (visibilidad por rol): el personal autorizado consulta el catálogo
completo, mientras que un Estudiante solo puede ver su propio registro con los
campos mínimos.
"""

import logging
from typing import Any, Dict, List

import pymysql
from flask import Blueprint, jsonify, request

from db import obtener_conexion_db
from routes.auth import requerir_token_y_rol
from routes.comunes import (
    formatear_fecha,
    respuesta_error,
    validar_correo,
    validar_texto,
)

estudiantes_bp = Blueprint("estudiantes", __name__)
registro = logging.getLogger(__name__)

# Longitudes máximas alineadas con el esquema
LONGITUD_MATRICULA = 20
LONGITUD_NOMBRE = 100
LONGITUD_GRADO = 20
LONGITUD_CORREO = 100
LONGITUD_TELEFONO = 20


def _validar_filtros(argumentos: Any) -> Any:
    """Valida los filtros `q` y `grado` de la consulta.

    Returns:
        str | None: Mensaje de error, o None si los filtros son válidos.
    """
    q = argumentos.get("q")
    if q is not None:
        if len(q) > LONGITUD_NOMBRE:
            return (
                f"El filtro 'q' supera la longitud máxima de "
                f"{LONGITUD_NOMBRE} caracteres."
            )

    grado = argumentos.get("grado")
    if grado is not None and len(grado) > LONGITUD_GRADO:
        return (
            f"El filtro 'grado' supera la longitud máxima de "
            f"{LONGITUD_GRADO} caracteres."
        )

    return None


@estudiantes_bp.route("/api/estudiantes", methods=["GET"])
@requerir_token_y_rol()
def obtener_estudiantes(usuario_autenticado: Dict[str, Any]):
    """Consulta el catálogo de estudiantes con acotamiento por rol (RN-01)."""
    error = _validar_filtros(request.args)
    if error:
        return respuesta_error(error, 400)

    conexion = obtener_conexion_db()
    try:
        with conexion.cursor() as cursor:
            # Un Estudiante solo ve su propio registro con campos mínimos
            if usuario_autenticado.get("rol") == "Estudiante":
                id_estudiante = usuario_autenticado.get("id_estudiante")

                if not id_estudiante:
                    return jsonify(
                        {
                            "mensaje": "Estudiantes consultados correctamente.",
                            "total": 0,
                            "datos": [],
                        }
                    ), 200

                cursor.execute(
                    """
                    SELECT id, nombre, matricula
                    FROM estudiantes
                    WHERE id = %s
                    """,
                    (id_estudiante,),
                )
                fila = cursor.fetchone()
                datos = [fila] if fila else []

                return jsonify(
                    {
                        "mensaje": "Estudiantes consultados correctamente.",
                        "total": len(datos),
                        "datos": datos,
                    }
                ), 200

            condiciones: List[str] = []
            parametros: List[Any] = []

            q = request.args.get("q")
            if q and q.strip():
                patron = f"%{q.strip()}%"
                condiciones.append(
                    "(nombre LIKE %s OR matricula LIKE %s OR correo LIKE %s)"
                )
                parametros.extend([patron] * 3)

            grado = request.args.get("grado")
            if grado and grado.strip():
                condiciones.append("grado = %s")
                parametros.append(grado.strip())

            sql = (
                "SELECT id, matricula, nombre, grado, correo, telefono, creado_en "
                "FROM estudiantes"
            )
            if condiciones:
                sql += " WHERE " + " AND ".join(condiciones)
            sql += " ORDER BY nombre ASC"

            cursor.execute(sql, parametros)
            filas = cursor.fetchall()

        datos = [
            {
                "id": fila["id"],
                "matricula": fila["matricula"],
                "nombre": fila["nombre"],
                "grado": fila["grado"],
                "correo": fila["correo"],
                "telefono": fila["telefono"],
                "creado_en": formatear_fecha(fila["creado_en"]),
            }
            for fila in filas
        ]

        return jsonify(
            {
                "mensaje": "Estudiantes consultados correctamente.",
                "total": len(datos),
                "datos": datos,
            }
        ), 200

    except Exception:
        registro.exception("Error al consultar estudiantes.")
        return respuesta_error("Error interno al consultar estudiantes.", 500)

    finally:
        conexion.close()


@estudiantes_bp.route("/api/estudiantes", methods=["POST"])
@requerir_token_y_rol(roles_permitidos=["Administrador"])
def crear_estudiante(usuario_autenticado: Dict[str, Any]):
    """Registra un estudiante (solo Administrador)."""
    datos = request.get_json(silent=True)

    if not isinstance(datos, dict):
        return respuesta_error(
            "El cuerpo de la petición debe ser un objeto JSON.", 400
        )

    matricula, error = validar_texto(
        datos, "matricula", obligatorio=True, maximo=LONGITUD_MATRICULA
    )
    if error:
        return respuesta_error(error, 400)

    nombre, error = validar_texto(
        datos, "nombre", obligatorio=True, maximo=LONGITUD_NOMBRE
    )
    if error:
        return respuesta_error(error, 400)

    grado, error = validar_texto(
        datos, "grado", obligatorio=True, maximo=LONGITUD_GRADO
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

    telefono, error = validar_texto(
        datos, "telefono", obligatorio=False, maximo=LONGITUD_TELEFONO
    )
    if error:
        return respuesta_error(error, 400)

    conexion = obtener_conexion_db()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT matricula, correo
                FROM estudiantes
                WHERE matricula = %s OR correo = %s
                LIMIT 1
                """,
                (matricula, correo),
            )
            duplicado = cursor.fetchone()
            if duplicado:
                if duplicado["matricula"] == matricula:
                    return respuesta_error(
                        "La matrícula ya está registrada.", 409
                    )
                return respuesta_error(
                    "El correo ya está registrado.", 409
                )

            cursor.execute(
                """
                INSERT INTO estudiantes (matricula, nombre, grado, correo, telefono)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (matricula, nombre, grado, correo, telefono),
            )
            id_nuevo_estudiante = cursor.lastrowid
            conexion.commit()

        return jsonify(
            {
                "mensaje": "Estudiante registrado correctamente.",
                "datos": {"id": id_nuevo_estudiante},
            }
        ), 201

    except pymysql.err.IntegrityError:
        conexion.rollback()
        return respuesta_error(
            "La matrícula o el correo ya están registrados.", 409
        )

    except Exception:
        conexion.rollback()
        registro.exception("Error al registrar estudiante.")
        return respuesta_error(
            "Error interno al registrar estudiante.", 500
        )

    finally:
        conexion.close()
