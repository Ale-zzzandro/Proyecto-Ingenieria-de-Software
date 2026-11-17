# Reglas de negocio

Símbolos: **✅ cumple**, **⚠️ cumple parcialmente**, **❌ no cumple / no existe**.

Las referencias son al código actual (Fase 2). La Fase 3 adaptará el frontend y la Fase 4 formalizará las pruebas automatizadas.

---

## RN-01 — Seguridad y privacidad

> Ningún usuario no autenticado puede consultar o registrar información. Las consultas se acotan según el rol.

**Estado global: ✅**

| Aspecto | Estado | Dónde se cumple |
|---|---|---|
| Login público y resto protegido | ✅ | `backend/routes/auth.py` → `requerir_token_y_rol()`; aplicado en todos los blueprints |
| Token ausente/inválido → 401 | ✅ | `auth.py` → `requerir_token_y_rol()` |
| Rol no permitido → 403 | ✅ | `auth.py` → `requerir_token_y_rol()` |
| Listado de incidencias | ✅ | `GET /api/incidencias` en `incidencias.py` |
| Acotamiento por fila (Admin todo; Docente/Estudiante `reportado`; Responsable `responsable`) | ✅ | `routes/comunes.py` → `condicion_alcance()`, aplicado a listado, detalle y métricas |
| Detalle con visibilidad por rol | ✅ | `GET /api/incidencias/<id>`; `404` si no es visible |
| Bitácora solo Admin y responsable asignado | ✅ | `bitacora_visible` en el detalle; el resto recibe `bitacora: []` |
| Rol Estudiante | ✅ | ENUM de `usuarios` + `usuarios.id_estudiante` (migración 001) |
| Catálogo de estudiantes con campos mínimos para Estudiante | ✅ | `GET /api/estudiantes` devuelve solo `id`, `nombre`, `matricula` de su propio registro |
| Rechazo de usuarios inactivos | ✅ | `auth.py` valida `usuarios.activo`; `PUT /api/usuarios/<id>/estado` lo administra |
| Gestión de usuarios solo Admin | ✅ | `routes/usuarios.py` |
| Selector de responsables solo lectura | ✅ | `GET /api/responsables` devuelve únicamente cuentas activas con rol `Personal Responsable` |

**Pendiente:** pruebas automatizadas formales (Fase 4) y adaptación visual de permisos en el frontend (Fase 3).

---

## RN-02 — Trazabilidad e inmutabilidad del creador

> Al registrar una incidencia se captura automáticamente quién la reportó y la fecha/hora, sin permitir alteraciones.

**Estado global: ✅** (con una limitación de BD documentada)

| Aspecto | Estado | Dónde se cumple |
|---|---|---|
| `reportado` se toma del JWT, no del body | ✅ | `incidencias.py` → `registrar_incidencia()` |
| `fecha` automática | ✅ | `incidencias.fecha DEFAULT CURRENT_TIMESTAMP` (MySQL) |
| `estado` inicial `Registrada` | ✅ | `registrar_incidencia()` inserta siempre `Registrada` |
| No existe endpoint que modifique `reportado` | ✅ | Solo existe asignación de `responsable` y seguimiento |
| Inmutabilidad a nivel BD | ⚠️ | No hay trigger ni privilegio que impida un `UPDATE reportado` manual |
| Devolver/consultar la trazabilidad | ✅ | El detalle expone `reportado`, `reportado_nombre` y `fecha` |
| Pruebas | ⚠️ | Verificado con el script de Fase 2 (88 comprobaciones); suite formal en Fase 4 |

**Pendiente:** un trigger de inmutabilidad es opcional y requiere confirmación del desarrollador; suite de pruebas en Fase 4.

---

## RN-03 — Ciclo de vida

> Toda incidencia inicia en `Registrada`. Solo pasa a `En seguimiento` cuando tiene responsable asignado y se añade la primera observación. Solo el responsable o el administrador puede cambiar a `Cerrada`.

**Estado global: ✅**

| Aspecto | Estado | Dónde se cumple |
|---|---|---|
| Estado inicial `Registrada` | ✅ | `registrar_incidencia()` |
| `En seguimiento` exige responsable asignado | ✅ | `agregar_seguimiento_bitacora()` devuelve `409` si falta |
| `En seguimiento` exige primera observación | ✅ | La observación es obligatoria (`400` si está vacía) |
| Solo el responsable asignado o Admin cambia estado | ✅ | `requerir_token_y_rol` + validación de asignación; Responsable no asignado → `404` |
| Cerrar exige estar `En seguimiento` | ✅ | `409` si se intenta desde `Registrada` |
| `Cerrada` es estado final | ✅ | `409` ante cualquier cambio posterior |
| `nuevo_estado` solo admite valores permitidos | ✅ | `400` si no es `En seguimiento` o `Cerrada` |
| No sobrescribir `responsable` al dar seguimiento | ✅ | El `UPDATE` solo modifica `estado` |
| Asignación/reasignación solo Admin | ✅ | `PUT /api/incidencias/<id>/responsable` |
| No reabrir una incidencia cerrada | ✅ | `409` en seguimiento y en reasignación |

**Pendiente:** pruebas automatizadas formales (Fase 4).

---

## RN-04 — Auditoría

> Toda actualización u observación en la bitácora guarda fecha, hora exacta y usuario.

**Estado global: ✅** (con una limitación de BD documentada)

| Aspecto | Estado | Dónde se cumple |
|---|---|---|
| `historial_seguimiento.usuario` desde el JWT | ✅ | `incidencias.py` → seguimiento y asignación |
| `historial_seguimiento.fecha` automática | ✅ | `DEFAULT CURRENT_TIMESTAMP` |
| `accion_realizada` descriptiva | ✅ | `"Observación de seguimiento"`, `"Transición de estado a: '...'"`, `"Asignación de responsable"` |
| Observación no vacía | ✅ | `400` si está vacía |
| Registrar asignación de responsable | ✅ | `PUT .../responsable` inserta en la bitácora |
| Consultar la bitácora (fecha y hora) | ✅ | `GET /api/incidencias/<id>` con `fecha` completa |
| Inmutabilidad de la bitácora | ⚠️ | No hay endpoint de modificación/borrado, pero tampoco restricción de BD |
| Registrar cambios de estado sin observación | ✅ | Toda transición exige observación y queda auditada |

**Pendiente:** mostrar la bitácora con fecha y hora en la Pantalla 6 (Fase 3); pruebas de auditoría (Fase 4).

---

## Decisión de diseño 5 — responsable al crear una incidencia

- Solo **Administrador** y **Docente** pueden enviar el campo `responsable` en `POST /api/incidencias`.
- Si un **Estudiante** envía `responsable`, la petición se **rechaza con `403`** (no se ignora silenciosamente). El motivo es que asignar responsable es una acción reservada; ignorar el campo ocultaría un intento de operación no permitida.
- La asignación o reasignación posterior sigue siendo exclusiva del Administrador mediante `PUT /api/incidencias/<id>/responsable`.
- En la Fase 3, el formulario del Estudiante no mostrará el selector de responsable.

---

## Matriz Rol × Acción (objetivo)

`Sí` = permitido; `No` = denegado; el ámbito se indica entre paréntesis.

| Acción | Administrador | Docente | Personal Responsable | Estudiante | No autenticado |
|---|---|---|---|---|---|
| Iniciar sesión | Sí | Sí | Sí | Sí | Sí |
| Ver panel/métricas | Sí (todo) | Sí (solo sus reportes) | Sí (solo asignadas) | Sí (solo sus reportes) | No |
| Listar incidencias | Sí (todo) | Sí (`reportado` = él) | Sí (`responsable` = él) | Sí (`reportado` = él) | No |
| Ver detalle | Sí (todo) | Sí (solo reportadas) | Sí (solo asignadas) | Sí (solo reportadas) | No |
| Ver bitácora | Sí | No | Sí (solo asignadas) | No | No |
| Crear incidencia | Sí | Sí | No | Sí (solo para sí mismo) | No |
| Indicar `responsable` al crear | Sí | Sí | No | No (`403`) | No |
| Asignar/reasignar responsable | Sí | No | No | No | No |
| Registrar seguimiento | Sí | No | Sí (solo asignadas) | No | No |
| Cambiar a `En seguimiento` / `Cerrada` | Sí | No | Sí (solo asignadas) | No | No |
| Consultar catálogo de estudiantes | Sí (completo) | Sí (completo) | Sí (completo) | Sí (solo su registro mínimo) | No |
| Alta de estudiante | Sí | No | No | No | No |
| Gestionar usuarios (crear/listar/activar) | Sí | No | No | No | No |
| Ver selector de responsables | Sí | Sí | Sí | Sí (solo lectura; el formulario no lo usa) | No |

> El selector de responsables sigue el contrato B.15 de [API.md](API.md): cualquier usuario autenticado puede leerlo. El formulario del Estudiante no lo mostrará en la Fase 3.

### Estado actual de la matriz (Fase 2)

| Acción | Admin | Docente | Personal Responsable | Estudiante |
|---|---|---|---|---|
| Iniciar sesión | ✅ | ✅ | ✅ | ✅ |
| Ver panel/métricas | ✅ | ✅ | ✅ | ✅ |
| Listar incidencias | ✅ | ✅ | ✅ | ✅ |
| Ver detalle | ✅ | ✅ | ✅ | ✅ |
| Ver bitácora | ✅ | ✅ (sin bitácora) | ✅ (solo asignadas) | ✅ (sin bitácora) |
| Crear incidencia | ✅ | ✅ | ❌ (correcto) | ✅ (solo para sí mismo) |
| Indicar `responsable` al crear | ✅ | ✅ | ❌ (correcto) | ✅ (rechazo 403) |
| Asignar responsable | ✅ | ❌ (correcto) | ❌ (correcto) | ❌ (correcto) |
| Registrar seguimiento | ✅ | ❌ (correcto) | ✅ (solo asignadas) | ❌ (correcto) |
| Cambiar estado | ✅ | ❌ (correcto) | ✅ (solo asignadas) | ❌ (correcto) |
| Catálogo de estudiantes | ✅ | ✅ | ✅ | ✅ (mínimo propio) |
| Alta de estudiante | ✅ | ❌ (correcto) | ❌ (correcto) | ❌ (correcto) |
| Gestionar usuarios | ✅ | ❌ (correcto) | ❌ (correcto) | ❌ (correcto) |
| Selector de responsables | ✅ | ✅ | ✅ | ✅ (solo lectura) |

---

## Trazabilidad de reglas por archivo

| Regla | Archivo / función principal | Fase |
|---|---|---|
| RN-01 | `routes/auth.py` → `requerir_token_y_rol`; `routes/comunes.py` → `condicion_alcance`; `routes/incidencias.py`, `routes/estudiantes.py`, `routes/panel.py`, `routes/usuarios.py` | 2 (implementado) |
| RN-02 | `routes/incidencias.py` → `registrar_incidencia` y `consultar_incidencia` | 2 (implementado) |
| RN-03 | `routes/incidencias.py` → `agregar_seguimiento_bitacora` y `asignar_responsable` | 2 (implementado) |
| RN-04 | `routes/incidencias.py` → seguimiento, asignación y detalle | 2 (implementado) |
| Permisos | `routes/auth.py` + `routes/comunes.py` → `condicion_alcance` | 2 (implementado) |
| Pruebas | Script de Fase 2 (88 comprobaciones); `tests/` formal en Fase 4 | 2 / 4 |
