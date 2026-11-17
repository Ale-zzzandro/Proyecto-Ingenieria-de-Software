"""Módulo de conexión y gestión del almacenamiento persistente MySQL.

Este módulo proporciona la función de fábrica para instanciar conexiones a la
base de datos utilizando PyMySQL bajo los estándares de codificación PEP 8.
"""

import pymysql
from pymysql.cursors import DictCursor

import config


def obtener_conexion_db() -> pymysql.connections.Connection:
    """Crea y retorna una nueva conexión activa hacia la base de datos MySQL.

    Returns:
        pymysql.connections.Connection: Objeto de conexión configurado con
            retorno de filas en formato diccionario.

    Raises:
        pymysql.MySQLError: Si ocurre un error al autenticar o conectar.
    """
    conexion = pymysql.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        port=config.DB_PORT,
        cursorclass=DictCursor,
        charset="utf8mb4",
        autocommit=False,
    )

    return conexion
