"""Configuración centralizada del backend.

Carga las variables desde `backend/.env` (sin sobrescribir las que ya existan
en el entorno) y expone valores tipados para el resto de módulos. Ningún
secreto ni credencial debe quedar escrito en el código.
"""

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Ruta absoluta de backend/ para localizar .env sin depender del directorio actual
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _texto(nombre: str, defecto: str = "") -> str:
    """Devuelve una variable de entorno de texto, con valor por defecto."""
    return os.getenv(nombre, defecto).strip()


def _entero(nombre: str, defecto: int) -> int:
    """Devuelve una variable de entorno entera y valida su formato."""
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return defecto
    try:
        return int(valor)
    except ValueError as error:
        raise RuntimeError(
            f"La variable de entorno {nombre} debe ser un número entero."
        ) from error


def _booleano(nombre: str, defecto: bool = False) -> bool:
    """Interpreta una variable de entorno como booleano."""
    valor = os.getenv(nombre)
    if valor is None:
        return defecto
    return valor.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def _lista(nombre: str, defecto: List[str]) -> List[str]:
    """Convierte una lista separada por comas en una lista de Python."""
    valor = os.getenv(nombre)
    if not valor or not valor.strip():
        return defecto
    return [elemento.strip() for elemento in valor.split(",") if elemento.strip()]


# Base de datos MySQL
DB_HOST = _texto("DB_HOST", "localhost")
DB_PORT = _entero("DB_PORT", 3306)
DB_USER = _texto("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = _texto("DB_NAME", "sistema_incidencias")

# Seguridad y JWT (se validan al arrancar la aplicación)
SECRET_KEY = _texto("SECRET_KEY")
JWT_SECRET_KEY = _texto("JWT_SECRET_KEY")
JWT_EXPIRACION_HORAS = _entero("JWT_EXPIRACION_HORAS", 8)

# Flask y CORS
FLASK_DEBUG = _booleano("FLASK_DEBUG", False)
CORS_ORIGINS = _lista(
    "CORS_ORIGINS",
    ["http://127.0.0.1:5500", "http://localhost:5500"],
)


def validar_secretos() -> None:
    """Verifica que las claves obligatorias estén configuradas.

    Raises:
        RuntimeError: Si falta `SECRET_KEY` o `JWT_SECRET_KEY`, o si la
            expiración del token no es positiva.
    """
    faltantes = [
        nombre
        for nombre, valor in (
            ("SECRET_KEY", SECRET_KEY),
            ("JWT_SECRET_KEY", JWT_SECRET_KEY),
        )
        if not valor
    ]
    if faltantes:
        raise RuntimeError(
            "Faltan variables de entorno obligatorias: "
            + ", ".join(faltantes)
            + ". Copia backend/.env.example a backend/.env y configura valores propios."
        )
    if JWT_EXPIRACION_HORAS <= 0:
        raise RuntimeError("JWT_EXPIRACION_HORAS debe ser mayor que cero.")
