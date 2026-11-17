"""Migra contraseñas en texto plano a hashes Werkzeug (scrypt).

El script es idempotente: solo transforma las contraseñas que no empiezan por
un prefijo de hash conocido. No imprime contraseñas ni hashes.

Uso (desde `backend/`):

    python scripts/migrar_contrasenas.py
    python scripts/migrar_contrasenas.py --dry-run
    python scripts/migrar_contrasenas.py --crear-estudiante

`--crear-estudiante` inserta, solo si se indica explícitamente y si no existe,
el usuario Estudiante de desarrollo vinculado al estudiante id=1.
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

from werkzeug.security import generate_password_hash

# Permite ejecutar el script desde backend/ con `python scripts/migrar_contrasenas.py`
RUTA_BACKEND = Path(__file__).resolve().parents[1]
if str(RUTA_BACKEND) not in sys.path:
    sys.path.insert(0, str(RUTA_BACKEND))

from db import obtener_conexion_db  # noqa: E402

PREFIJOS_HASH = ("scrypt:", "pbkdf2:", "argon2")
CONTRASENA_ESTUDIANTE = "estudiante123"
ESTUDIANTE_ID = 1


def es_hash(valor: Any) -> bool:
    """Indica si el valor almacenado ya es un hash Werkzeug reconocido."""
    return isinstance(valor, str) and valor.startswith(PREFIJOS_HASH)


def migrar_contrasenas(conexion, dry_run: bool) -> None:
    """Hashea las contraseñas que aún estén en texto plano."""
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT id, correo, contrasena FROM usuarios ORDER BY id"
        )
        usuarios: List[Dict[str, Any]] = cursor.fetchall()

    pendientes = [usuario for usuario in usuarios if not es_hash(usuario["contrasena"])]

    print(f"Usuarios revisados: {len(usuarios)}")
    print(f"Contraseñas ya hasheadas: {len(usuarios) - len(pendientes)}")
    print(f"Contraseñas en texto plano detectadas: {len(pendientes)}")

    for usuario in pendientes:
        print(
            "  - Se hasheará la contraseña del usuario "
            f"id={usuario['id']} correo={usuario['correo']}"
        )
        if dry_run:
            continue

        nuevo_hash = generate_password_hash(usuario["contrasena"])
        with conexion.cursor() as cursor:
            cursor.execute(
                "UPDATE usuarios SET contrasena = %s WHERE id = %s",
                (nuevo_hash, usuario["id"]),
            )

    if dry_run:
        print("Modo --dry-run: no se modificó la base de datos.")
    elif pendientes:
        conexion.commit()
        print(f"Contraseñas migradas: {len(pendientes)}")
    else:
        print("No había contraseñas en texto plano; nada que migrar.")


def crear_usuario_estudiante(conexion, dry_run: bool) -> None:
    """Inserta el usuario Estudiante de desarrollo vinculado al estudiante 1."""
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT id, nombre, correo FROM estudiantes WHERE id = %s",
            (ESTUDIANTE_ID,),
        )
        estudiante = cursor.fetchone()

        if not estudiante:
            print(
                f"No existe el estudiante id={ESTUDIANTE_ID}; "
                "no se crea el usuario Estudiante."
            )
            return

        cursor.execute(
            """
            SELECT id FROM usuarios
            WHERE correo = %s OR id_estudiante = %s
            LIMIT 1
            """,
            (estudiante["correo"], estudiante["id"]),
        )
        existente = cursor.fetchone()

    if existente:
        print(
            "El usuario Estudiante ya existe "
            f"(id={existente['id']}); no se inserta de nuevo."
        )
        return

    print(
        "Se creará el usuario Estudiante para "
        f"{estudiante['nombre']} ({estudiante['correo']}), "
        f"id_estudiante={estudiante['id']}."
    )

    if dry_run:
        print("Modo --dry-run: no se insertó el usuario.")
        return

    hash_contrasena = generate_password_hash(CONTRASENA_ESTUDIANTE)
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO usuarios (
                nombre, correo, contrasena, rol, id_estudiante, activo
            ) VALUES (%s, %s, %s, 'Estudiante', %s, 1)
            """,
            (
                estudiante["nombre"],
                estudiante["correo"],
                hash_contrasena,
                estudiante["id"],
            ),
        )
        nuevo_id = cursor.lastrowid

    conexion.commit()
    print(f"Usuario Estudiante creado con id={nuevo_id}.")
    print("Contraseña de desarrollo: la documentada en README.md.")


def main() -> int:
    """Punto de entrada del script."""
    parser = argparse.ArgumentParser(
        description=(
            "Hashea las contraseñas en texto plano de la tabla usuarios. "
            "No imprime contraseñas."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra los cambios sin modificar la base de datos.",
    )
    parser.add_argument(
        "--crear-estudiante",
        action="store_true",
        help=(
            "Inserta el usuario Estudiante de desarrollo vinculado al "
            f"estudiante id={ESTUDIANTE_ID}, si no existe."
        ),
    )
    argumentos = parser.parse_args()

    conexion = None
    try:
        conexion = obtener_conexion_db()
        migrar_contrasenas(conexion, argumentos.dry_run)

        if argumentos.crear_estudiante:
            crear_usuario_estudiante(conexion, argumentos.dry_run)

        return 0

    except Exception as error:
        if conexion is not None:
            conexion.rollback()
        print(
            "Error: no se pudo completar la migración "
            f"({type(error).__name__}). Revisa la conexión y el respaldo."
        )
        return 1

    finally:
        if conexion is not None:
            conexion.close()


if __name__ == "__main__":
    sys.exit(main())
