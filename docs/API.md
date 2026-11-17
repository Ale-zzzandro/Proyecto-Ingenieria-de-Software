# API

Base URL: `http://localhost:5000/api`

Este documento tiene dos partes:

1. **API actual** — estado histórico verificado en la Fase 0; se conserva como referencia de las brechas corregidas.
2. **API objetivo** — contrato implementado en la Fase 2, respetando las decisiones de diseño.

> **Estado tras la Fase 2:** todos los endpoints de la Parte B están implementados en `backend/routes/` y verificados con una batería de 88 comprobaciones por rol. La Parte A describe el punto de partida y ya no representa el comportamiento vigente.

---

## 0. Convenciones

- Todas las peticiones y respuestas usan `application/json` salvo que se indique lo contrario.
- Fechas: el contrato objetivo usa `YYYY-MM-DD` o `YYYY-MM-DD HH:MM:SS` (hora local del servidor, sin zona horaria). La API actual puede devolver `datetime` serializado por Flask como fecha HTTP (RFC 822); se indica en cada endpoint.
- Autenticación: encabezado `Authorization: Bearer <token>`.
- **Toda respuesta incluye `mensaje`**, tanto en éxito como en error (decisión 7).
- Errores 500: mensaje genérico al cliente y detalle solo en el log del servidor.
- Códigos usados: `200`, `201`, `400`, `401`, `403`, `404`, `409`, `500`.

### Roles

`Administrador`, `Docente`, `Personal Responsable`, `Estudiante`.

### Enumeraciones

| Campo | Valores |
|---|---|
| `usuarios.rol` | `Administrador`, `Docente`, `Personal Responsable`, `Estudiante` |
| `incidencias.categoria` | `Conducta`, `Académica`, `Asistencia`, `Otra` |
| `incidencias.prioridad` | `Baja`, `Media`, `Alta`, `Urgente` |
| `incidencias.estado` | `Registrada`, `En seguimiento`, `Cerrada` |

---

# Parte A — API actual (histórica, Fase 0)

> Sección conservada para documentar las brechas que se corrigieron en las fases 1 y 2. El contrato vigente es la Parte B.

## A.1 Resumen histórico (Fase 0)

| Método | Ruta | Roles permitidos | Estado |
|---|---|---|---|
| POST | `/api/login` | Público | ✅ Implementado |
| GET | `/api/estudiantes` | Administrador, Docente, Personal Responsable | ✅ Implementado |
| POST | `/api/estudiantes` | Administrador | ✅ Implementado |
| POST | `/api/incidencias` | Administrador, Docente | ✅ Implementado |
| POST | `/api/incidencias/<id>/seguimiento` | Administrador, Personal Responsable | ✅ Implementado (con bugs) |
| GET | `/api/incidencias` | — | ❌ **No existe** (el frontend lo invoca) |
| GET | `/api/incidencias/<id>` | — | ❌ No existe |
| PUT | `/api/incidencias/<id>/responsable` | — | ❌ No existe |
| GET | `/api/panel/metricas` | — | ❌ No existe |
| GET/POST/PUT | `/api/usuarios...` | — | ❌ No existe |
| GET | `/api/responsables` | — | ❌ No existe |

## A.2 POST `/api/login`

**Archivo/función:** `backend/routes/auth.py` → `iniciar_sesion()`.

**Body:**

```json
{ "correo": "admin@cutonala.udg.mx", "contrasena": "admin123" }
```

**Respuestas reales:**

| Código | Cuerpo |
|---|---|
| 200 | `{"mensaje": "Sesión iniciada correctamente.", "token": "<JWT>", "usuario": {"id": 1, "nombre": "...", "correo": "...", "rol": "Administrador", "id_estudiante": null}}` |
| 400 | `{"mensaje": "Correo o matrícula y contraseña obligatorios."}` |
| 400 | `{"mensaje": "El cuerpo de la petición debe ser un objeto JSON."}` |
| 401 | `{"mensaje": "Credenciales de acceso incorrectas."}` |
| 500 | `{"mensaje": "Error interno del servidor."}` |

**Notas verificadas (Fase 1):**

- El campo `correo` acepta un correo o una matrícula (solo para usuarios con rol `Estudiante`).
- Compara con `check_password_hash`; las contraseñas deben estar hasheadas (script `backend/scripts/migrar_contrasenas.py`).
- Rechaza usuarios con `activo = 0` con el mismo `401` genérico.
- El token expira a las `JWT_EXPIRACION_HORAS` (default 8) y usa `datetime.now(timezone.utc)`.
- Incluye `id_estudiante` en el JWT y en `usuario`.
- Los errores 500 no exponen detalles internos; se registran con `logging`.

## A.3 GET `/api/estudiantes`

**Archivo/función:** `backend/routes/estudiantes.py` → `obtener_estudiantes()`.

**Roles:** Administrador, Docente, Personal Responsable.

**Respuesta 200:** objeto con `mensaje`, `total` y `datos`:

```json
{
  "mensaje": "Estudiantes consultados correctamente.",
  "total": 1,
  "datos": [
    {
      "id": 1,
      "matricula": "219876543",
      "nombre": "Jocelyn Citlalli Silva Diaz",
      "grado": "6to Semestre",
      "correo": "jocelyn.silva@alumnos.udg.mx",
      "telefono": "3312345678",
      "creado_en": "Sat, 19 Sep 2026 17:14:30 GMT"
    }
  ]
}
```

> `creado_en` es un `datetime` de Python y Flask lo serializa por defecto como fecha HTTP (RFC 822), no como ISO 8601. El contrato objetivo formateará las fechas explícitamente como `YYYY-MM-DD HH:MM:SS` en la Fase 2.

**Otros códigos:** `401` sin token; `403` rol no permitido; `500` genérico sin detalles internos.

**Notas (Fase 1):** sin filtros ni paginación; incluye `mensaje`; cierra la conexión en `finally`; el rol Estudiante todavía no está permitido en este endpoint (se define en la Fase 2).

## A.4 POST `/api/estudiantes`

**Archivo/función:** `backend/routes/estudiantes.py` → `crear_estudiante()`.

**Roles:** Administrador.

**Body:**

```json
{
  "matricula": "219000111",
  "nombre": "Nombre Completo",
  "grado": "2do Semestre",
  "correo": "alumno@alumnos.udg.mx",
  "telefono": "3311112222"
}
```

`telefono` es opcional (se guarda `''` si falta). Matrícula, nombre, grado y correo son obligatorios.

**Respuestas reales:**

| Código | Cuerpo |
|---|---|
| 201 | `{"mensaje": "Estudiante registrado correctamente.", "datos": {"id": 3}}` |
| 400 | `{"mensaje": "El campo 'matricula' es obligatorio."}` (o el campo inválido) |
| 400 | `{"mensaje": "La matrícula o el correo ya están registrados."}` |
| 401/403 | `{"mensaje": "..."}` |
| 500 | `{"mensaje": "Error interno al registrar estudiante."}` |

**Notas (Fase 1):** valida cuerpo JSON, campos obligatorios, tipo texto y longitudes; los duplicados devuelven **400** (el contrato objetivo usará `409` en la Fase 2); no valida formato de correo; no expone detalles de MySQL; el frontend todavía no envía `telefono`.

## A.5 POST `/api/incidencias`

**Archivo/función:** `backend/routes/incidencias.py` → `registrar_incidencia()`.

**Roles:** Administrador, Docente.

**Body:**

```json
{
  "id_estudiante": 1,
  "tipo": "Falta de entrega de actividades",
  "categoria": "Académica",
  "prioridad": "Media",
  "descripcion": "El alumno no ha entregado los últimos 3 avances."
}
```

`prioridad` es opcional (default `Media`). `estado` se fuerza a `Registrada` y `reportado` se toma del JWT (RN-02).

**Respuestas reales:**

| Código | Cuerpo |
|---|---|
| 201 | `{"mensaje": "Incidencia registrada correctamente.", "id_incidencia": 2}` |
| 400 | `{"mensaje": "Faltan datos requeridos del reporte."}` |
| 500 | `{"mensaje": "Error interno al guardar la incidencia."}` |
| 401/403 | `{"mensaje": "..."}` |

**Notas (Fase 1):** no validaba ENUMs ni la existencia del estudiante (corregido en la Fase 2); no aceptaba `departamento` ni `responsable`; el rol Estudiante todavía no podía crear; los 500 no exponen `str(e)`.

## A.6 POST `/api/incidencias/<id>/seguimiento`

**Archivo/función:** `backend/routes/incidencias.py` → `agregar_seguimiento_bitacora()`.

**Roles:** Administrador, Personal Responsable.

**Body:**

```json
{ "observacion": "Se contactó al alumno.", "nuevo_estado": "En seguimiento" }
```

**Respuestas reales:**

| Código | Cuerpo |
|---|---|
| 200 | `{"mensaje": "Avance registrado en la bitácora con éxito."}` |
| 400 | `{"mensaje": "La observación de seguimiento es obligatoria."}` |
| 404 | `{"mensaje": "La incidencia especificada no existe."}` |
| 500 | `{"mensaje": "Error interno en la transacción de seguimiento."}` |
| 401/403 | `{"mensaje": "..."}` |

**Bugs verificados (corregidos en Fase 2):**

1. `UPDATE incidencias SET estado = %s, responsable = %s` **sobrescribe `responsable`** con el usuario que da seguimiento (líneas 137-142).
2. Permite pasar a `Cerrada` desde `Registrada` (el `elif` no exige `En seguimiento`).
3. No valida que `nuevo_estado` sea permitido: un valor inválido deja el estado actual y aun así registra la observación.
4. No verifica que el usuario sea el responsable asignado ni que exista un responsable.
5. No impide modificar una incidencia ya `Cerrada`.
6. No audita la asignación de responsable (no existe endpoint).

---

# Parte B — API objetivo (implementada en la Fase 2)

## B.1 Convención de respuesta

Éxito con datos:

```json
{ "mensaje": "Consulta exitosa.", "datos": [] }
```

Éxito con creación:

```json
{ "mensaje": "Incidencia registrada correctamente.", "datos": { "id": 2 } }
```

Error:

```json
{ "mensaje": "Descripción legible del error." }
```

Colecciones pueden incluir `total`:

```json
{ "mensaje": "Consulta exitosa.", "total": 12, "datos": [] }
```

Las fechas se devuelven como cadenas `YYYY-MM-DD HH:MM:SS` (formateadas explícitamente en el backend; no se depende de la serialización automática de Flask).

> **Estado:** la Fase 1 unificó `mensaje` y el objeto `{mensaje, total, datos}` en `GET /api/estudiantes`. La Fase 2 implementó el resto del contrato con esta misma convención y fechas formateadas explícitamente. El frontend se adapta en la Fase 3.

## B.2 Resumen

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| POST | `/api/login` | Público | Login por correo **o** matrícula |
| GET | `/api/estudiantes` | Todos los autenticados | Catálogo (campos según rol) |
| POST | `/api/estudiantes` | Administrador | Alta de estudiante |
| GET | `/api/incidencias` | Todos los autenticados | Lista con buscador/filtros y acotamiento RN-01 |
| GET | `/api/incidencias/<id>` | Todos los autenticados | Detalle + bitácora según permisos |
| POST | `/api/incidencias` | Administrador, Docente, Estudiante | Registrar incidencia |
| PUT | `/api/incidencias/<id>/responsable` | Administrador | Asignar/reasignar responsable |
| POST | `/api/incidencias/<id>/seguimiento` | Administrador, Personal Responsable | Observación y transición de estado |
| GET | `/api/panel/metricas` | Todos los autenticados | Métricas + 5 recientes (acotado por rol) |
| GET | `/api/usuarios` | Administrador | Listar usuarios |
| POST | `/api/usuarios` | Administrador | Crear usuario |
| PUT | `/api/usuarios/<id>/estado` | Administrador | Activar/desactivar usuario |
| GET | `/api/responsables` | Todos los autenticados | Selector de responsables activos |

## B.3 POST `/api/login`

**Body:**

```json
{ "correo": "admin@cutonala.udg.mx", "contrasena": "admin123" }
```

El campo `correo` acepta indistintamente un correo o una matrícula (se conserva el nombre por compatibilidad).

**200:**

```json
{
  "mensaje": "Sesión iniciada correctamente.",
  "token": "<JWT>",
  "usuario": {
    "id": 1,
    "nombre": "Administrador General",
    "correo": "admin@cutonala.udg.mx",
    "rol": "Administrador",
    "id_estudiante": null
  }
}
```

**Errores:** `400` faltan campos; `401` credenciales incorrectas, usuario inactivo o cuenta de estudiante sin vínculo (mensaje genérico para no filtrar información); `500` error interno.

**Reglas:** `check_password_hash`; `activo = 1`; JWT con `id`, `nombre`, `rol`, `id_estudiante`, `exp`; expiración configurable (`JWT_EXPIRACION_HORAS`, default 8).

## B.4 GET `/api/estudiantes`

**Roles:** todos los autenticados.

**Query opcional:** `q` (nombre/matrícula/correo), `grado`.

**Respuesta según rol:**

- Administrador, Docente, Personal Responsable: `id`, `matricula`, `nombre`, `grado`, `correo`, `telefono`, `creado_en`.
- Estudiante: **solo su propio registro** con `id`, `nombre`, `matricula` (decisión 4 + RN-01). *(Supuesto: no se expone el catálogo completo a estudiantes; confirmar en Fase 2.)*

**200:**

```json
{
  "mensaje": "Estudiantes consultados correctamente.",
  "total": 2,
  "datos": [
    { "id": 1, "matricula": "219876543", "nombre": "Jocelyn Citlalli Silva Diaz", "grado": "6to Semestre", "correo": "jocelyn.silva@alumnos.udg.mx", "telefono": "3312345678", "creado_en": "2026-09-19 17:14:30" }
  ]
}
```

**Errores:** `400` filtro inválido; `401`; `500`.

## B.5 POST `/api/estudiantes`

**Rol:** Administrador.

**Body:** `matricula`, `nombre`, `grado`, `correo` obligatorios; `telefono` opcional (máx. 20).

**201:** `{"mensaje": "Estudiante registrado correctamente.", "datos": {"id": 3}}`

**Errores:** `400` campos faltantes/formato inválido; `409` matrícula o correo duplicado; `401/403`; `500`.

## B.6 GET `/api/incidencias`

**Roles:** todos los autenticados.

**Query string:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `q` | texto | Busca en `tipo`, `descripcion`, `departamento`, nombre y matrícula del estudiante |
| `estudiante` | int | `id_estudiante` |
| `categoria` | enum | `Conducta`, `Académica`, `Asistencia`, `Otra` |
| `prioridad` | enum | `Baja`, `Media`, `Alta`, `Urgente` |
| `estado` | enum | `Registrada`, `En seguimiento`, `Cerrada` |
| `responsable` | int | `id` de usuario responsable |
| `desde` | fecha | `fecha >= desde` (inclusive) |
| `hasta` | fecha | `fecha <= hasta` (inclusive; si es solo fecha, hasta el final del día) |

**Acotamiento por rol (RN-01), siempre aplicado antes de los filtros:**

| Rol | Condición |
|---|---|
| Administrador | Sin restricción |
| Docente | `reportado = usuario.id` |
| Estudiante | `reportado = usuario.id` |
| Personal Responsable | `responsable = usuario.id` |

Si un rol acotado envía un filtro que contradice su ámbito (p. ej. un Docente filtra por otro `estudiante`), el resultado es vacío; no se devuelve `403` para no filtrar existencia.

**200:**

```json
{
  "mensaje": "Incidencias consultadas correctamente.",
  "total": 1,
  "datos": [
    {
      "id": 1,
      "id_estudiante": 1,
      "estudiante_nombre": "Jocelyn Citlalli Silva Diaz",
      "estudiante_matricula": "219876543",
      "reportado": 2,
      "reportado_nombre": "Gabriel Navarro (Maestro)",
      "responsable": 3,
      "responsable_nombre": "Psic. Ana Torres",
      "departamento": null,
      "tipo": "Falta de entrega de actividades",
      "categoria": "Académica",
      "prioridad": "Media",
      "estado": "Registrada",
      "descripcion": "El alumno no ha entregado los últimos 3 avances.",
      "fecha": "2026-09-19 11:14:37"
    }
  ]
}
```

**Errores:** `400` ENUM/fecha inválidos; `401`; `500`.

**SQL de referencia:** `JOIN estudiantes` y `LEFT JOIN usuarios` para nombres; `ORDER BY fecha DESC, id DESC`; `LIKE` parametrizado.

## B.7 GET `/api/incidencias/<id>`

**Roles:** todos los autenticados, con la misma visibilidad de B.6.

**200 (Admin o responsable asignado):**

```json
{
  "mensaje": "Incidencia consultada correctamente.",
  "datos": {
    "id": 1,
    "id_estudiante": 1,
    "estudiante_nombre": "Jocelyn Citlalli Silva Diaz",
    "reportado": 2,
    "reportado_nombre": "Gabriel Navarro (Maestro)",
    "responsable": 3,
    "responsable_nombre": "Psic. Ana Torres",
    "departamento": null,
    "tipo": "Falta de entrega de actividades",
    "categoria": "Académica",
    "prioridad": "Media",
    "estado": "Registrada",
    "descripcion": "El alumno no ha entregado los últimos 3 avances.",
    "fecha": "2026-09-19 11:14:37",
    "bitacora_visible": true,
    "bitacora": [
      {
        "id": 1,
        "usuario": 3,
        "usuario_nombre": "Psic. Ana Torres",
        "observacion": "Se contactó al alumno.",
        "accion_realizada": "Transición de estado a: 'En seguimiento'",
        "fecha": "2026-09-20 09:30:00"
      }
    ]
  }
}
```

**Privacidad de la bitácora:**

- Administrador y responsable asignado: `bitacora_visible: true` y arreglo completo.
- Quien reportó (Docente/Estudiante): `bitacora_visible: false` y `bitacora: []`; solo ve estado y datos generales.
- Personal Responsable no asignado: `404` (no se revela la existencia).

**Errores:** `401`; `404` inexistente o no visible; `500`.

## B.8 POST `/api/incidencias`

**Roles:** Administrador, Docente, Estudiante.

**Body:**

```json
{
  "id_estudiante": 1,
  "tipo": "Falta de entrega de actividades",
  "categoria": "Académica",
  "prioridad": "Media",
  "descripcion": "El alumno no ha entregado los últimos 3 avances.",
  "departamento": "Coordinación Académica",
  "responsable": 3
}
```

| Campo | Obligatorio | Regla |
|---|---|---|
| `id_estudiante` | Admin/Docente | Estudiante lo omite o debe coincidir con su propio `id_estudiante` |
| `tipo` | Sí | Texto, máx. 50 |
| `categoria` | Sí | ENUM válido |
| `prioridad` | No | ENUM válido, default `Media` |
| `descripcion` | Sí | Texto no vacío |
| `departamento` | No | Texto, máx. 100 |
| `responsable` | No | **Solo Administrador y Docente**; usuario **activo** con rol `Personal Responsable`. Si lo envía un Estudiante → `403`. |

**Reglas:** `reportado` = usuario del JWT (RN-02); `estado` = `Registrada` (RN-03); si el rol es Estudiante y su cuenta no tiene `id_estudiante`, `403`; si intenta reportar a otro estudiante, `403`. El `responsable` opcional solo lo pueden indicar Administrador y Docente; si un Estudiante envía ese campo se **rechaza con `403`** (no se ignora silenciosamente), porque asignar responsable es una acción reservada.

**201:**

```json
{
  "mensaje": "Incidencia registrada correctamente.",
  "datos": { "id": 2, "estado": "Registrada" }
}
```

**Errores:** `400` campos/ENUM inválidos; `403` estudiante no vinculado, ajeno o intento de asignar `responsable`; `404` estudiante o responsable inexistente; `401`; `500`.

## B.9 PUT `/api/incidencias/<id>/responsable`

**Rol:** Administrador.

**Body:**

```json
{ "responsable": 3 }
```

**Reglas:** el usuario debe existir, estar activo y tener rol `Personal Responsable`; no se permite modificar una incidencia `Cerrada` (`409`); se registra en `historial_seguimiento` la acción de asignación con fecha/usuario (RN-04), usando `accion_realizada = "Asignación de responsable"` y una `observacion` generada (por ejemplo, `"Responsable asignado: Psic. Ana Torres"`).

**200:**

```json
{
  "mensaje": "Responsable asignado correctamente.",
  "datos": { "id": 1, "responsable": 3, "responsable_nombre": "Psic. Ana Torres" }
}
```

**Errores:** `400` responsable inválido; `404` incidencia o usuario inexistente; `409` incidencia cerrada; `401/403`; `500`.

## B.10 POST `/api/incidencias/<id>/seguimiento`

**Roles:** Administrador y Personal Responsable **asignado** (el Admin puede actuar sin estar asignado).

**Body:**

```json
{ "observacion": "Se contactó al alumno.", "nuevo_estado": "En seguimiento" }
```

`nuevo_estado` es opcional; si se omite, se conserva el estado actual y solo se agrega la observación. Valores permitidos: `En seguimiento`, `Cerrada`.

**Máquina de estados (RN-03):**

| Estado actual | `nuevo_estado` | Condición | Resultado |
|---|---|---|---|
| `Registrada` | `En seguimiento` | Responsable asignado + observación no vacía | `En seguimiento` |
| `Registrada` | `Cerrada` | — | `409` |
| `En seguimiento` | `En seguimiento` | Observación | Sin cambio de estado |
| `En seguimiento` | `Cerrada` | Observación | `Cerrada` |
| `Cerrada` | cualquiera | — | `409` (estado final) |
| cualquiera | valor no permitido | — | `400` |

**Reglas adicionales:** nunca se modifica `responsable`; toda observación/transición inserta fila en `historial_seguimiento` con `usuario` del JWT y `fecha` (RN-04); un Personal Responsable no asignado recibe `404`.

**200:**

```json
{
  "mensaje": "Avance registrado en la bitácora correctamente.",
  "datos": { "id": 1, "estado": "En seguimiento" }
}
```

**Errores:** `400` observación vacía o estado inválido; `404` incidencia inexistente o no asignada; `409` estado final/transición no permitida; `401/403`; `500`.

## B.11 GET `/api/panel/metricas`

**Roles:** todos los autenticados, con acotamiento RN-01 idéntico a B.6.

**200:**

```json
{
  "mensaje": "Métricas consultadas correctamente.",
  "datos": {
    "total": 1,
    "por_estado": { "Registrada": 1, "En seguimiento": 0, "Cerrada": 0 },
    "por_prioridad": { "Baja": 0, "Media": 1, "Alta": 0, "Urgente": 0 },
    "por_categoria": { "Conducta": 0, "Académica": 1, "Asistencia": 0, "Otra": 0 },
    "recientes": [
      {
        "id": 1,
        "estudiante_nombre": "Jocelyn Citlalli Silva Diaz",
        "categoria": "Académica",
        "prioridad": "Media",
        "estado": "Registrada",
        "fecha": "2026-09-19 11:14:37"
      }
    ]
  }
}
```

`recientes` devuelve como máximo **5** incidencias, ordenadas por `fecha DESC, id DESC`. Las claves de los mapas se devuelven siempre, con `0` cuando no hay casos.

## B.12 GET `/api/usuarios`

**Rol:** Administrador.

**Query opcional:** `rol` (ENUM), `activo` (`0`/`1`).

**200:**

```json
{
  "mensaje": "Usuarios consultados correctamente.",
  "total": 4,
  "datos": [
    {
      "id": 1,
      "nombre": "Administrador General",
      "correo": "admin@cutonala.udg.mx",
      "rol": "Administrador",
      "id_estudiante": null,
      "activo": 1,
      "creado_en": "2026-09-19 17:14:30"
    }
  ]
}
```

Nunca se devuelve `contrasena`.

## B.13 POST `/api/usuarios`

**Rol:** Administrador.

**Body:**

```json
{
  "nombre": "Nuevo Docente",
  "correo": "nuevo.docente@cutonala.udg.mx",
  "contrasena": "contrasenaSegura123",
  "rol": "Docente",
  "id_estudiante": null,
  "activo": 1
}
```

**Reglas:** correo único; contraseña mínima de 8 caracteres, guardada con `generate_password_hash`; si `rol = "Estudiante"`, `id_estudiante` es obligatorio, debe existir y no estar vinculado a otra cuenta (`UNIQUE`).

**201:**

```json
{ "mensaje": "Usuario creado correctamente.", "datos": { "id": 5 } }
```

**Errores:** `400` campos/rol inválidos o contraseña corta; `409` correo o `id_estudiante` duplicado; `401/403`; `500`.

## B.14 PUT `/api/usuarios/<id>/estado`

**Rol:** Administrador.

**Body:** `{ "activo": false }`

**200:** `{"mensaje": "Usuario desactivado correctamente.", "datos": {"id": 2, "activo": 0}}`

**Reglas:** un usuario inactivo no puede iniciar sesión; el Administrador no puede desactivar su propia cuenta (`409`).

**Errores:** `400` valor no booleano; `404` inexistente; `409` autodesactivación; `401/403`; `500`.

## B.15 GET `/api/responsables`

**Roles:** todos los autenticados (selector del formulario de incidencias).

**200:**

```json
{
  "mensaje": "Responsables consultados correctamente.",
  "datos": [
    { "id": 3, "nombre": "Psic. Ana Torres", "correo": "ana.torres@cutonala.udg.mx" }
  ]
}
```

Solo devuelve usuarios con `rol = 'Personal Responsable'` y `activo = 1`.

---

## C. Brechas entre la API actual y la objetivo

| # | Brecha | Fase |
|---|---|---|
| 1 | `GET /api/incidencias` no existe y el frontend lo llama | 2 |
| 2 | No hay detalle ni consulta de bitácora | 2 |
| 3 | No hay asignación de responsable | 2 |
| 4 | No hay métricas de panel | 2 |
| 5 | No hay gestión de usuarios ni selector de responsables | 2 |
| 6 | `message` vs `mensaje` | 1-2 |
| 7 | Errores 500 filtran `str(e)` | 1 |
| 8 | Nombres de tablas capitalizados en SQL | 1 |
| 9 | Sin validación de ENUMs/JSON | 1-2 |
| 10 | Sin acotamiento por rol ni privacidad de bitácora | 2 |
| 11 | Ciclo de vida incompleto y `responsable` sobrescrito | 2 |
| 12 | Login solo por correo, contraseña en texto plano, sin `activo` | 1 |
| 13 | Frontend no maneja el contrato nuevo | 3 |
