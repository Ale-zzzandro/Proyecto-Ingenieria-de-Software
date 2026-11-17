"""Utilidades compartidas por las rutas de la API.

Centraliza validaciones, formato de fechas, acotamiento por rol (RN-01) y la
selección base de incidencias para evitar duplicar lógica entre blueprints.
"""

import datetime
import re
from typing import Any, Dict, List, Optional, Tuple

from flask import jsonify

# Enumeraciones del esquema (deben coincidir con la base de datos)
ROLES_VALIDOS = (
    "Administrador",
    "Docente",
    "Personal Responsable",
    "Estudiante",
)
CATEGORIAS_VALIDAS = ("Conducta", "Académica", "Asistencia", "Otra")
PRIORIDADES_VALIDAS = ("Baja", "Media", "Alta", "Urgente")
ESTADOS_VALIDOS = ("Registrada", "En seguimiento", "Cerrada")

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Selección base reutilizada por el listado, el detalle y las métricas
SELECCION_INCIDENCIA = """
SELECT i.id,
       i.id_estudiante,
       e.nombre AS estudiante_nombre,
       e.matricula AS estudiante_matricula,
       i.reportado,
       ur.nombre AS reportado_nombre,
       i.responsable,
       uresp.nombre AS responsable_nombre,
       i.departamento,
       i.tipo,
       i.categoria,
       i.prioridad,
       i.estado,
       i.descripcion,
       i.fecha
FROM incidencias AS i
JOIN estudiantes AS e ON e.id = i.id_estudiante
LEFT JOIN usuarios AS ur ON ur.id = i.reportado
LEFT JOIN usuarios AS uresp ON uresp.id = i.responsable
"""


def respuesta_error(mensaje: str, codigo: int) -> Tuple[Any, int]:
    """Construye una respuesta JSON de error con la clave `mensaje`."""
    return jsonify({"mensaje": mensaje}), codigo


def formatear_fecha(valor: Any) -> Optional[str]:
    """Convierte un `datetime` de MySQL a `YYYY-MM-DD HH:MM:SS`."""
    if valor is None:
        return None
    if isinstance(valor, datetime.datetime):
        return valor.strftime("%Y-%m-%d %H:%M:%S")
    return str(valor)


def validar_texto(
    datos: Dict[str, Any],
    campo: str,
    *,
    obligatorio: bool = True,
    maximo: Optional[int] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Valida y normaliza un campo de texto.

    Returns:
        tuple: (valor, mensaje_error). El valor es None si el campo opcional
            viene vacío; el mensaje es None si el campo es válido.
    """
    if campo not in datos or datos[campo] is None:
        if obligatorio:
            return None, f"El campo '{campo}' es obligatorio."
        return None, None

    valor = datos[campo]
    if not isinstance(valor, str):
        return None, f"El campo '{campo}' debe ser texto."

    valor = valor.strip()
    if obligatorio and not valor:
        return None, f"El campo '{campo}' no puede estar vacío."

    if maximo is not None and len(valor) > maximo:
        return None, (
            f"El campo '{campo}' supera la longitud máxima de {maximo} caracteres."
        )

    return (valor or None), None


def validar_entero(
    datos: Dict[str, Any],
    campo: str,
    *,
    obligatorio: bool = True,
) -> Tuple[Optional[int], Optional[str]]:
    """Valida un entero positivo, aceptando números o cadenas numéricas."""
    if campo not in datos or datos[campo] is None:
        if obligatorio:
            return None, f"El campo '{campo}' es obligatorio."
        return None, None

    valor = datos[campo]
    if isinstance(valor, bool):
        return None, f"El campo '{campo}' debe ser un número entero."

    if isinstance(valor, int):
        numero = valor
    elif isinstance(valor, str):
        try:
            numero = int(valor.strip())
        except ValueError:
            return None, f"El campo '{campo}' debe ser un número entero."
    else:
        return None, f"El campo '{campo}' debe ser un número entero."

    if numero <= 0:
        return None, f"El campo '{campo}' debe ser mayor que cero."

    return numero, None


def validar_enum(
    datos: Dict[str, Any],
    campo: str,
    permitidos: Tuple[str, ...],
    *,
    obligatorio: bool = True,
    defecto: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Valida que un campo pertenezca a una enumeración."""
    if campo not in datos or datos[campo] is None:
        if obligatorio:
            return None, f"El campo '{campo}' es obligatorio."
        return defecto, None

    valor = datos[campo]
    if not isinstance(valor, str) or valor not in permitidos:
        return None, (
            f"El campo '{campo}' debe ser uno de: {', '.join(permitidos)}."
        )

    return valor, None


def validar_correo(valor: str) -> bool:
    """Comprueba un formato de correo básico."""
    return bool(PATRON_CORREO.match(valor))


def condicion_alcance(usuario: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """Devuelve la condición SQL de visibilidad por rol (RN-01).

    El resultado se concatena a un `WHERE 1 = 1` sobre el alias `i` de
    `incidencias`.
    """
    rol = usuario.get("rol")

    if rol == "Administrador":
        return "", []
    if rol in ("Docente", "Estudiante"):
        return " AND i.reportado = %s", [usuario["id"]]
    if rol == "Personal Responsable":
        return " AND i.responsable = %s", [usuario["id"]]

    return " AND 1 = 0", []


def serializar_incidencia(fila: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte una fila de incidencia en el JSON del contrato."""
    return {
        "id": fila["id"],
        "id_estudiante": fila["id_estudiante"],
        "estudiante_nombre": fila["estudiante_nombre"],
        "estudiante_matricula": fila["estudiante_matricula"],
        "reportado": fila["reportado"],
        "reportado_nombre": fila["reportado_nombre"],
        "responsable": fila["responsable"],
        "responsable_nombre": fila["responsable_nombre"],
        "departamento": fila["departamento"],
        "tipo": fila["tipo"],
        "categoria": fila["categoria"],
        "prioridad": fila["prioridad"],
        "estado": fila["estado"],
        "descripcion": fila["descripcion"],
        "fecha": formatear_fecha(fila["fecha"]),
    }


def parsear_fecha(valor: str, *, fin_de_dia: bool = False) -> datetime.datetime:
    """Convierte una fecha de filtro a `datetime`.

    Acepta `YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS` y `YYYY-MM-DDTHH:MM:SS`.
    Si solo llega la fecha y `fin_de_dia` es True, devuelve el final del día.

    Raises:
        ValueError: Si el formato no es válido.
    """
    valor = valor.strip()

    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(valor, formato)
        except ValueError:
            continue

    fecha = datetime.datetime.strptime(valor, "%Y-%m-%d")
    if fin_de_dia:
        return fecha.replace(hour=23, minute=59, second=59)
    return fecha


def construir_filtros_incidencias(
    argumentos: Any,
) -> Tuple[str, List[Any], Optional[str]]:
    """Construye las condiciones de los filtros de `GET /api/incidencias`.

    Returns:
        tuple: (condicion_sql, parametros, mensaje_error).
    """
    condiciones: List[str] = []
    parametros: List[Any] = []

    q = argumentos.get("q")
    if q is not None:
        q = q.strip()
        if q:
            patron = f"%{q}%"
            condiciones.append(
                "(i.tipo LIKE %s OR i.descripcion LIKE %s OR "
                "i.departamento LIKE %s OR e.nombre LIKE %s OR e.matricula LIKE %s)"
            )
            parametros.extend([patron] * 5)

    for campo, columna in (
        ("estudiante", "i.id_estudiante"),
        ("responsable", "i.responsable"),
    ):
        if campo in argumentos:
            numero, error = validar_entero(argumentos, campo, obligatorio=True)
            if error:
                return "", [], f"El filtro '{campo}' debe ser un entero positivo."
            condiciones.append(f"{columna} = %s")
            parametros.append(numero)

    for campo, permitidos, columna in (
        ("categoria", CATEGORIAS_VALIDAS, "i.categoria"),
        ("prioridad", PRIORIDADES_VALIDAS, "i.prioridad"),
        ("estado", ESTADOS_VALIDOS, "i.estado"),
    ):
        if campo in argumentos:
            valor = argumentos.get(campo)
            if valor not in permitidos:
                return "", [], (
                    f"El filtro '{campo}' debe ser uno de: "
                    f"{', '.join(permitidos)}."
                )
            condiciones.append(f"{columna} = %s")
            parametros.append(valor)

    for campo, fin_de_dia, operador in (
        ("desde", False, ">="),
        ("hasta", True, "<="),
    ):
        if campo in argumentos:
            valor = argumentos.get(campo)
            if not isinstance(valor, str) or not valor.strip():
                return "", [], f"El filtro '{campo}' debe ser una fecha válida."
            try:
                fecha = parsear_fecha(valor, fin_de_dia=fin_de_dia)
            except ValueError:
                return "", [], (
                    f"El filtro '{campo}' debe tener formato "
                    "YYYY-MM-DD o YYYY-MM-DD HH:MM:SS."
                )
            condiciones.append(f"i.fecha {operador} %s")
            parametros.append(fecha)

    if not condiciones:
        return "", parametros, None

    return " AND " + " AND ".join(condiciones), parametros, None
