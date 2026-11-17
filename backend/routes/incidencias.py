"""Módulo de gestión del ciclo de vida de incidencias y bitácora de auditoría.

Garantiza la aplicación de las reglas de negocio RN-01 (visibilidad por rol),
RN-02 (trazabilidad), RN-03 (ciclo de vida) y RN-04 (auditoría).
"""

import logging
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from db import obtener_conexion_db
from routes.auth import requerir_token_y_rol
from routes.comunes import (
    CATEGORIAS_VALIDAS,
    PRIORIDADES_VALIDAS,
    SELECCION_INCIDENCIA,
    condicion_alcance,
    construir_filtros_incidencias,
    formatear_fecha,
    respuesta_error,
    serializar_incidencia,
    validar_entero,
    validar_enum,
    validar_texto,
)

incidencias_bp = Blueprint("incidencias", __name__)
registro = logging.getLogger(__name__)

ESTADOS_FINALES = ("En seguimiento", "Cerrada")


@incidencias_bp.route("/api/incidencias", methods=["GET"])
@requerir_token_y_rol()
def listar_incidencias(usuario_autenticado: Dict[str, Any]):
    """Lista incidencias con filtros y acotamiento por rol (RN-01)."""
    condicion_rol, parametros_rol = condicion_alcance(usuario_autenticado)
    condicion_filtros, parametros_filtros, error = (
        construir_filtros_incidencias(request.args)
    )

    if error:
        return respuesta_error(error, 400)

    sql = (
        SELECCION_INCIDENCIA
        + " WHERE 1 = 1"
        + condicion_rol
        + condicion_filtros
        + " ORDER BY i.fecha DESC, i.id DESC"
    )

    conexion = obtener_conexion_db()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql, parametros_rol + parametros_filtros)
            filas = cursor.fetchall()

        datos = [serializar_incidencia(fila) for fila in filas]

        return jsonify(
            {
                "mensaje": "Incidencias consultadas correctamente.",
                "total": len(datos),
                "datos": datos,
            }
        ), 200

    except Exception:
        registro.exception("Error al consultar incidencias.")
        return respuesta_error("Error interno al consultar incidencias.", 500)

    finally:
        conexion.close()


@incidencias_bp.route("/api/incidencias/<int:id_incidencia>", methods=["GET"])
@requerir_token_y_rol()
def consultar_incidencia(
    usuario_autenticado: Dict[str, Any],
    id_incidencia: int,
):
    """Devuelve el detalle de una incidencia y su bitácora según permisos."""
    condicion_rol, parametros_rol = condicion_alcance(usuario_autenticado)
    sql = (
        SELECCION_INCIDENCIA
        + " WHERE i.id = %s"
        + condicion_rol
    )

    conexion = obtener_conexion_db()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql, [id_incidencia] + parametros_rol)
            fila = cursor.fetchone()

            if not fila:
                return respuesta_error(
                    "La incidencia no existe o no es visible para su usuario.",
                    404,
                )

            datos = serializar_incidencia(fila)

            # La bitácora solo la ven el Administrador y el responsable asignado
            bitacora_visible = (
                usuario_autenticado["rol"] == "Administrador"
                or (
                    usuario_autenticado["rol"] == "Personal Responsable"
                    and fila["responsable"] == usuario_autenticado["id"]
                )
            )

            datos["bitacora_visible"] = bitacora_visible
            datos["bitacora"] = []

            if bitacora_visible:
                cursor.execute(
                    """
                    SELECT h.id,
                           h.usuario,
                           u.nombre AS usuario_nombre,
                           h.observacion,
                           h.accion_realizada,
                           h.fecha
                    FROM historial_seguimiento AS h
                    LEFT JOIN usuarios AS u ON u.id = h.usuario
                    WHERE h.incidencia = %s
                    ORDER BY h.fecha ASC, h.id ASC
                    """,
                    (id_incidencia,),
                )
                datos["bitacora"] = [
                    {
                        "id": entrada["id"],
                        "usuario": entrada["usuario"],
                        "usuario_nombre": entrada["usuario_nombre"],
                        "observacion": entrada["observacion"],
                        "accion_realizada": entrada["accion_realizada"],
                        "fecha": formatear_fecha(entrada["fecha"]),
                    }
                    for entrada in cursor.fetchall()
                ]

        return jsonify(
            {
                "mensaje": "Incidencia consultada correctamente.",
                "datos": datos,
            }
        ), 200

    except Exception:
        registro.exception("Error al consultar la incidencia.")
        return respuesta_error("Error interno al consultar la incidencia.", 500)

    finally:
        conexion.close()


@incidencias_bp.route("/api/incidencias", methods=["POST"])
@requerir_token_y_rol(
    roles_permitidos=["Administrador", "Docente", "Estudiante"]
)
def registrar_incidencia(usuario_autenticado: Dict[str, Any]):
    """Registra una incidencia (RN-02 y RN-03).

    Args:
        usuario_autenticado (dict): Datos del usuario extraídos del token JWT.

    Returns:
        Response: Confirmación del registro e ID generado.
    """
    datos = request.get_json(silent=True)

    if not isinstance(datos, dict):
        return respuesta_error(
            "El cuerpo de la petición debe ser un objeto JSON.", 400
        )

    rol = usuario_autenticado["rol"]

    # Asignar responsable es una acción reservada (decisión de diseño 5)
    if rol == "Estudiante" and "responsable" in datos:
        return respuesta_error(
            "Un Estudiante no puede asignar un responsable al crear la incidencia.",
            403,
        )

    tipo, error = validar_texto(datos, "tipo", obligatorio=True, maximo=50)
    if error:
        return respuesta_error(error, 400)

    descripcion, error = validar_texto(datos, "descripcion", obligatorio=True)
    if error:
        return respuesta_error(error, 400)

    categoria, error = validar_enum(
        datos, "categoria", CATEGORIAS_VALIDAS, obligatorio=True
    )
    if error:
        return respuesta_error(error, 400)

    prioridad, error = validar_enum(
        datos,
        "prioridad",
        PRIORIDADES_VALIDAS,
        obligatorio=False,
        defecto="Media",
    )
    if error:
        return respuesta_error(error, 400)

    departamento, error = validar_texto(
        datos, "departamento", obligatorio=False, maximo=100
    )
    if error:
        return respuesta_error(error, 400)

    if rol == "Estudiante":
        id_estudiante_propio = usuario_autenticado.get("id_estudiante")
        if not id_estudiante_propio:
            return respuesta_error(
                "La cuenta de estudiante no está vinculada a un registro de estudiante.",
                403,
            )

        if datos.get("id_estudiante") is not None:
            id_solicitado, error = validar_entero(
                datos, "id_estudiante", obligatorio=True
            )
            if error:
                return respuesta_error(error, 400)
            if id_solicitado != id_estudiante_propio:
                return respuesta_error(
                    "Un Estudiante solo puede registrar incidencias para sí mismo.",
                    403,
                )

        id_estudiante = id_estudiante_propio
    else:
        id_estudiante, error = validar_entero(
            datos, "id_estudiante", obligatorio=True
        )
        if error:
            return respuesta_error(error, 400)

    responsable = None
    if rol in ("Administrador", "Docente") and datos.get("responsable") is not None:
        responsable, error = validar_entero(
            datos, "responsable", obligatorio=True
        )
        if error:
            return respuesta_error(error, 400)

    conexion = obtener_conexion_db()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM estudiantes WHERE id = %s",
                (id_estudiante,),
            )
            if not cursor.fetchone():
                return respuesta_error("El estudiante indicado no existe.", 404)

            if responsable is not None:
                cursor.execute(
                    "SELECT id, rol, activo FROM usuarios WHERE id = %s",
                    (responsable,),
                )
                usuario_responsable = cursor.fetchone()
                if not usuario_responsable:
                    return respuesta_error(
                        "El responsable indicado no existe.", 404
                    )
                if (
                    usuario_responsable["rol"] != "Personal Responsable"
                    or not usuario_responsable["activo"]
                ):
                    return respuesta_error(
                        "El responsable indicado no está activo o no tiene "
                        "el rol Personal Responsable.",
                        400,
                    )

            cursor.execute(
                """
                INSERT INTO incidencias (
                    id_estudiante, reportado, responsable, tipo, categoria,
                    prioridad, estado, descripcion, departamento
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    id_estudiante,
                    usuario_autenticado["id"],
                    responsable,
                    tipo,
                    categoria,
                    prioridad,
                    "Registrada",
                    descripcion,
                    departamento,
                ),
            )
            id_nueva_incidencia = cursor.lastrowid
            conexion.commit()

        return jsonify(
            {
                "mensaje": "Incidencia registrada correctamente.",
                "datos": {"id": id_nueva_incidencia, "estado": "Registrada"},
            }
        ), 201

    except Exception:
        conexion.rollback()
        registro.exception("Error interno al guardar la incidencia.")
        return respuesta_error("Error interno al guardar la incidencia.", 500)

    finally:
        conexion.close()


@incidencias_bp.route(
    "/api/incidencias/<int:id_incidencia>/responsable",
    methods=["PUT"],
)
@requerir_token_y_rol(roles_permitidos=["Administrador"])
def asignar_responsable(
    usuario_autenticado: Dict[str, Any],
    id_incidencia: int,
):
    """Asigna o reasigna el responsable de una incidencia (solo Admin)."""
    datos = request.get_json(silent=True)

    if not isinstance(datos, dict):
        return respuesta_error(
            "El cuerpo de la petición debe ser un objeto JSON.", 400
        )

    responsable, error = validar_entero(
        datos, "responsable", obligatorio=True
    )
    if error:
        return respuesta_error(error, 400)

    conexion = obtener_conexion_db()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT id, estado FROM incidencias WHERE id = %s FOR UPDATE",
                (id_incidencia,),
            )
            incidencia = cursor.fetchone()

            if not incidencia:
                return respuesta_error(
                    "La incidencia indicada no existe.", 404
                )

            if incidencia["estado"] == "Cerrada":
                return respuesta_error(
                    "No se puede asignar responsable a una incidencia cerrada.",
                    409,
                )

            cursor.execute(
                "SELECT id, nombre, rol, activo FROM usuarios WHERE id = %s",
                (responsable,),
            )
            usuario_responsable = cursor.fetchone()

            if not usuario_responsable:
                return respuesta_error(
                    "El responsable indicado no existe.", 404
                )

            if (
                usuario_responsable["rol"] != "Personal Responsable"
                or not usuario_responsable["activo"]
            ):
                return respuesta_error(
                    "El responsable indicado no está activo o no tiene "
                    "el rol Personal Responsable.",
                    400,
                )

            cursor.execute(
                "UPDATE incidencias SET responsable = %s WHERE id = %s",
                (responsable, id_incidencia),
            )

            cursor.execute(
                """
                INSERT INTO historial_seguimiento (
                    incidencia, usuario, observacion, accion_realizada
                ) VALUES (%s, %s, %s, %s)
                """,
                (
                    id_incidencia,
                    usuario_autenticado["id"],
                    f"Responsable asignado: {usuario_responsable['nombre']}",
                    "Asignación de responsable",
                ),
            )

            conexion.commit()

        return jsonify(
            {
                "mensaje": "Responsable asignado correctamente.",
                "datos": {
                    "id": id_incidencia,
                    "responsable": responsable,
                    "responsable_nombre": usuario_responsable["nombre"],
                },
            }
        ), 200

    except Exception:
        conexion.rollback()
        registro.exception("Error al asignar responsable.")
        return respuesta_error("Error interno al asignar responsable.", 500)

    finally:
        conexion.close()


@incidencias_bp.route(
    "/api/incidencias/<int:id_incidencia>/seguimiento",
    methods=["POST"],
)
@requerir_token_y_rol(roles_permitidos=["Administrador", "Personal Responsable"])
def agregar_seguimiento_bitacora(
    usuario_autenticado: Dict[str, Any],
    id_incidencia: int,
):
    """Agrega una observación y aplica la máquina de estados (RN-03 y RN-04).

    Args:
        usuario_autenticado (dict): Usuario autenticado procesando el caso.
        id_incidencia (int): Identificador de la incidencia objetivo.

    Returns:
        Response: Confirmación del cambio registrado.
    """
    datos = request.get_json(silent=True)

    if not isinstance(datos, dict):
        return respuesta_error(
            "El cuerpo de la petición debe ser un objeto JSON.", 400
        )

    observacion, error = validar_texto(
        datos, "observacion", obligatorio=True
    )
    if error:
        return respuesta_error(
            "La observación de seguimiento es obligatoria.", 400
        )

    nuevo_estado = datos.get("nuevo_estado")
    if nuevo_estado is not None:
        if (
            not isinstance(nuevo_estado, str)
            or nuevo_estado not in ESTADOS_FINALES
        ):
            return respuesta_error(
                "El campo 'nuevo_estado' debe ser 'En seguimiento' o 'Cerrada'.",
                400,
            )

    conexion = obtener_conexion_db()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, estado, responsable
                FROM incidencias
                WHERE id = %s
                FOR UPDATE
                """,
                (id_incidencia,),
            )
            incidencia = cursor.fetchone()

            if not incidencia:
                return respuesta_error(
                    "La incidencia indicada no existe.", 404
                )

            # Un responsable no asignado no debe saber que la incidencia existe
            if (
                usuario_autenticado["rol"] == "Personal Responsable"
                and incidencia["responsable"] != usuario_autenticado["id"]
            ):
                return respuesta_error(
                    "La incidencia no existe o no está asignada a su usuario.",
                    404,
                )

            estado_actual = incidencia["estado"]

            if estado_actual == "Cerrada":
                return respuesta_error(
                    "La incidencia ya está cerrada y no admite cambios.",
                    409,
                )

            if nuevo_estado == "En seguimiento":
                if estado_actual == "Registrada" and not incidencia["responsable"]:
                    return respuesta_error(
                        "La incidencia necesita un responsable asignado para "
                        "pasar a 'En seguimiento'.",
                        409,
                    )
                estado_final = "En seguimiento"
            elif nuevo_estado == "Cerrada":
                if estado_actual != "En seguimiento":
                    return respuesta_error(
                        "Solo se puede cerrar una incidencia que esté "
                        "'En seguimiento'.",
                        409,
                    )
                estado_final = "Cerrada"
            else:
                estado_final = estado_actual

            if estado_final != estado_actual:
                cursor.execute(
                    "UPDATE incidencias SET estado = %s WHERE id = %s",
                    (estado_final, id_incidencia),
                )
                accion_realizada = (
                    f"Transición de estado a: '{estado_final}'"
                )
            else:
                accion_realizada = "Observación de seguimiento"

            cursor.execute(
                """
                INSERT INTO historial_seguimiento (
                    incidencia, usuario, observacion, accion_realizada
                ) VALUES (%s, %s, %s, %s)
                """,
                (
                    id_incidencia,
                    usuario_autenticado["id"],
                    observacion,
                    accion_realizada,
                ),
            )

            conexion.commit()

        return jsonify(
            {
                "mensaje": "Avance registrado en la bitácora correctamente.",
                "datos": {"id": id_incidencia, "estado": estado_final},
            }
        ), 200

    except Exception:
        conexion.rollback()
        registro.exception("Error en la transacción de seguimiento.")
        return respuesta_error(
            "Error interno en la transacción de seguimiento.", 500
        )

    finally:
        conexion.close()
