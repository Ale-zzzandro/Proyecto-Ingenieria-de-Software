# AGENTS.md

Guía de trabajo para agentes y desarrolladores del **Sistema de Gestión de Incidencias Escolares** (Centro Universitario de Tonalá, UdeG).

## 1. Descripción y stack

Aplicación web para digitalizar el ciclo de vida de una incidencia escolar: reporte → seguimiento → cierre, con responsables, observaciones y auditoría. Todo el dominio, la documentación y los comentarios están en **español**.

- **Backend:** Python 3.11, Flask 3, PyMySQL, PyJWT, Flask-CORS, Werkzeug.
- **Base de datos:** MySQL 8, InnoDB, `utf8mb4` / `utf8mb4_unicode_ci`.
- **Frontend:** HTML5 + CSS3 + JavaScript vanilla (SPA simple, JWT en `localStorage`).
- **Entorno:** Windows + VS Code; comandos de ejemplo en PowerShell.

## 2. Estructura real

```
backend/
  app.py                 # Fábrica de la app Flask, CORS, logging y blueprints
  config.py              # Configuración tipada desde backend/.env
  db.py                  # obtener_conexion_db() con PyMySQL, DictCursor y utf8mb4
  requirements.txt
  scripts/
    migrar_contrasenas.py # Hashea contraseñas en texto plano (idempotente)
  routes/
    __init__.py
    auth.py              # POST /api/login y decorador requerir_token_y_rol
    estudiantes.py       # GET y POST /api/estudiantes
    incidencias.py       # POST /api/incidencias y POST .../seguimiento
frontend/
  index.html             # Pantallas 1 a 6 (secciones mostrar/ocultar)
  css/styles.css
  js/config.js           # API_URL
  js/auth.js             # Login, cierre de sesión y UI por rol
  js/app.js              # Incidencias, estudiantes y seguimiento
docs/                    # ARQUITECTURA, API, BASE_DE_DATOS, REGLAS_DE_NEGOCIO, ROADMAP
sistema_incidencias.sql  # Dump histórico DAÑADO en codificación; NO usar como fuente
```

> El backend se ejecuta **desde `backend/`** porque usa imports como `from db import ...` y `from routes.auth import ...`.

## 3. Comandos

```powershell
# Entorno virtual (desde la raíz)
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt

# Backend (desde backend/)
cd backend
python app.py            # http://localhost:5000

# Migrar contraseñas en texto plano (idempotente; respaldar la BD antes)
python scripts\migrar_contrasenas.py --dry-run
python scripts\migrar_contrasenas.py
```

Frontend: abrir `frontend/index.html` con **Live Server** (VS Code). No requiere build.

## 4. Convenciones del código existente

- **PEP 8**, nombres descriptivos en español, docstrings y comentarios en español.
- **Type hints** en funciones nuevas y existentes cuando se toquen.
- **SQL siempre parametrizado** con `%s`; nunca concatenar valores de usuario.
- Usar `with conexion.cursor() as cursor:` y `conexion.commit()` / `conexion.rollback()`.
- Cerrar la conexión en `finally: conexion.close()`.
- Proteger rutas con `@requerir_token_y_rol(roles_permitidos=[...])`; el decorador inyecta el payload JWT como **primer argumento** (`current_user` / `usuario_autenticado`).
- Respuestas JSON: **siempre** incluir `mensaje` (éxito y error). No devolver `str(e)` en errores 500; registrar con `logging`.
- Nombres de tablas en **minúscula** en todo el SQL nuevo: `usuarios`, `estudiantes`, `incidencias`, `historial_seguimiento`.

## 5. Decisiones de diseño ya tomadas (respetar)

1. Rol `Estudiante` en el ENUM de `usuarios`; columnas `usuarios.id_estudiante` (NULL, UNIQUE, FK) y `usuarios.activo` (default 1). El login acepta correo **o** matrícula y rechaza inactivos.
2. `incidencias.departamento VARCHAR(100) NULL` para "persona asignada o departamento".
3. Visibilidad (RN-01): Admin ve todo; Docente y Estudiante solo lo que `reportado` = su id; Personal Responsable solo lo que `responsable` = su id. La bitácora solo la ven Admin y el responsable asignado; quien reportó ve solo datos generales y estado.
4. Docente y Estudiante pueden crear incidencias. Al Estudiante el catálogo solo le devuelve campos mínimos (`id`, `nombre`, `matrícula`).
5. Solo el Administrador asigna/reasigna responsable (endpoint propio). Al crear, solo **Administrador y Docente** pueden indicar un responsable activo con rol `Personal Responsable`; si un **Estudiante** envía `responsable`, se **rechaza con `403`** (no se ignora). En la Fase 3 el formulario del Estudiante no muestra el selector.
6. Ciclo de vida: `Registrada` → `En seguimiento` → `Cerrada`. "En seguimiento" exige responsable + primera observación; cerrar exige estar "En seguimiento" + observación. "Cerrada" es final. Solo responsable asignado o Admin da seguimiento/cierra. **Nunca sobrescribir `responsable` al agregar seguimiento.**
7. JSON: siempre `mensaje`. Errores 500 sin detalles internos.
8. Migraciones SQL numeradas e idempotentes en `backend/db/migraciones/`; esquema completo en `backend/db/schema.sql`. **Nunca ejecutar SQL destructivo sin confirmación.**

## 6. Reglas de oro

- Respetar **RN-01** (seguridad/privacidad), **RN-02** (trazabilidad del creador), **RN-03** (ciclo de vida) y **RN-04** (auditoría).
- Cero secretos hardcodeados: usar `.env` (ver `backend/.env.example`).
- No romper la API sin actualizar `docs/API.md` en la misma fase.
- Cambios pequeños, verificables y con pruebas manuales documentadas.
- Pedir confirmación antes de tocar el esquema de la BD o añadir dependencias.
- No usar el dump `sistema_incidencias.sql` como fuente: está dañado en codificación.
- **Sin control de versiones:** antes de cada fase el desarrollador copia la carpeta del proyecto como respaldo; al terminar, el agente lista exactamente los archivos creados, modificados y eliminados.

## 7. Flujo de trabajo por fases

1. **Fase 0:** documentación y andamiaje (entregada y aprobada).
2. **Fase 1:** seguridad base y limpieza del backend (entregada, pendiente de aprobación).
3. **Fase 2:** backend funcional completo.
4. **Fase 3:** frontend completo.
5. **Fase 4:** pruebas y cierre.

Al terminar cada fase: resumen, lista exacta de archivos creados/modificados/eliminados, prueba manual paso a paso y **detenerse** hasta que el usuario escriba "continúa con la Fase N".

**Respaldos:** antes de cada fase el desarrollador copia la carpeta del proyecto como respaldo; al terminar, el agente lista exactamente los archivos creados, modificados y eliminados. No se usa ninguna herramienta de control de versiones.

## 8. Documentación

- [README](README.md)
- [Arquitectura](docs/ARQUITECTURA.md)
- [API](docs/API.md)
- [Base de datos](docs/BASE_DE_DATOS.md)
- [Reglas de negocio](docs/REGLAS_DE_NEGOCIO.md)
- [Roadmap](docs/ROADMAP.md)
