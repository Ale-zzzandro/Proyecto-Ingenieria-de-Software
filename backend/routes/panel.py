"""Rutas del panel de métricas.

Aplica el mismo acotamiento por rol que el listado de incidencias (RN-01), de
modo que cada usuario solo ve agregados de los casos que le corresponden.
"""

import logging
from typing import Any, Dict, List

from flask import Blueprint, jsonify

from db import obtener_conexion_db
from routes.auth import requerir_token_y_rol
from routes.comunes import (
    CATEGORIAS_VALIDAS,
    ESTADOS_VALIDOS,
    PRIORIDADES_VALIDAS,
    condicion_alcance,
    formatear_fecha,
    respuesta_error,
)

panel_bp = Blueprint("panel", __name__)
registro = logging.getLogger(__name__)


def _mapa_ceros(claves: Any) -> Dict[str, int]:
    """Construye un mapa con todas las claves de la enumeración en cero."""
    return {clave: 0 for clave in claves}


@panel_bp.route("/api/panel/metricas", methods=["GET"])
@requerir_token_y_rol()
def consultar_metricas(usuario_autenticado: Dict[str, Any]):
    """Devuelve los totales y las incidencias recientes visibles para el rol."""
    condicion_rol, parametros_rol = condicion_alcance(usuario_autenticado)

    conexion = obtener_conexion_db()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM incidencias AS i "
                "WHERE 1 = 1" + condicion_rol,
                parametros_rol,
            )
            total = cursor.fetchone()["total"]

            por_estado = _mapa_ceros(ESTADOS_VALIDOS)
            cursor.execute(
                "SELECT i.estado AS clave, COUNT(*) AS cantidad "
                "FROM incidencias AS i WHERE 1 = 1"
                + condicion_rol
                + " GROUP BY i.estado",
                parametros_rol,
            )
            for fila in cursor.fetchall():
                if fila["clave"] in por_estado:
                    por_estado[fila["clave"]] = fila["cantidad"]

            por_prioridad = _mapa_ceros(PRIORIDADES_VALIDAS)
            cursor.execute(
                "SELECT i.prioridad AS clave, COUNT(*) AS cantidad "
                "FROM incidencias AS i WHERE 1 = 1"
                + condicion_rol
                + " GROUP BY i.prioridad",
                parametros_rol,
            )
            for fila in cursor.fetchall():
                if fila["clave"] in por_prioridad:
                    por_prioridad[fila["clave"]] = fila["cantidad"]

            por_categoria = _mapa_ceros(CATEGORIAS_VALIDAS)
            cursor.execute(
                "SELECT i.categoria AS clave, COUNT(*) AS cantidad "
                "FROM incidencias AS i WHERE 1 = 1"
                + condicion_rol
                + " GROUP BY i.categoria",
                parametros_rol,
            )
            for fila in cursor.fetchall():
                if fila["clave"] in por_categoria:
                    por_categoria[fila["clave"]] = fila["cantidad"]

            cursor.execute(
                """
                SELECT i.id,
                       e.nombre AS estudiante_nombre,
                       i.categoria,
                       i.prioridad,
                       i.estado,
                       i.fecha
                FROM incidencias AS i
                JOIN estudiantes AS e ON e.id = i.id_estudiante
                WHERE 1 = 1
                """
                + condicion_rol
                + " ORDER BY i.fecha DESC, i.id DESC LIMIT 5",
                parametros_rol,
            )
            recientes: List[Dict[str, Any]] = [
                {
                    "id": fila["id"],
                    "estudiante_nombre": fila["estudiante_nombre"],
                    "categoria": fila["categoria"],
                    "prioridad": fila["prioridad"],
                    "estado": fila["estado"],
                    "fecha": formatear_fecha(fila["fecha"]),
                }
                for fila in cursor.fetchall()
            ]

        return jsonify(
            {
                "mensaje": "Métricas consultadas correctamente.",
                "datos": {
                    "total": total,
                    "por_estado": por_estado,
                    "por_prioridad": por_prioridad,
                    "por_categoria": por_categoria,
                    "recientes": recientes,
                },
            }
        ), 200

    except Exception:
        registro.exception("Error al consultar métricas del panel.")
        return respuesta_error(
            "Error interno al consultar métricas del panel.", 500
        )

    finally:
        conexion.close()
