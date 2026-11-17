# Sistema de Gestión de Incidencias Escolares

Aplicación web para digitalizar el ciclo de vida de una incidencia escolar en el **Centro Universitario de Tonalá (UdeG)**: desde el reporte hasta su resolución, con seguimiento de responsables, observaciones, estados y fechas auditables.

Proyecto de la materia **Ingeniería del Software (Act. 17)**.

## Características

- Autenticación con JWT y control de acceso por roles (RBAC).
- Roles: Administrador, Docente, Personal Responsable del Seguimiento y Estudiante.
- Registro de incidencias con categoría, prioridad, descripción, estudiante, departamento y responsable opcional (solo Administrador/Docente pueden indicarlo al crear).
- Ciclo de vida controlado: `Registrada` → `En seguimiento` → `Cerrada`.
- Bitácora de seguimiento con observaciones, acción realizada, fecha/hora y usuario.
- Consulta de incidencias con buscador y filtros por estudiante, fecha, categoría, prioridad, responsable y estado.
- Panel con métricas y reportes recientes, acotado según el rol.
- Gestión de estudiantes y de usuarios (alta, listado, activación/desactivación).
- Interfaz en español, responsiva y sin framework de frontend.

> **Estado:** proyecto en desarrollo por fases. La Fase 1 dejó la configuración por entorno, las contraseñas hasheadas y la limpieza del backend; la Fase 2 completó todos los endpoints del contrato (incidencias, estudiantes, usuarios, responsables y métricas). El frontend se adapta en la Fase 3. Consulta [docs/ROADMAP.md](docs/ROADMAP.md) para el estado real.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11, Flask 3.0, PyMySQL 1.1, PyJWT 2.8, Flask-CORS 4.0, Werkzeug 3.0 |
| Base de datos | MySQL 8, InnoDB, `utf8mb4_unicode_ci` |
| Frontend | HTML5, CSS3, JavaScript vanilla |
| Autenticación | JWT (HS256) en `localStorage` |
| Entorno | Windows + VS Code + Live Server |

## Requisitos

- Python 3.11 o superior.
- MySQL 8 (servicio local en el puerto 3306).
- VS Code con la extensión **Live Server** (recomendado para el frontend).
- PowerShell.

## Instalación paso a paso

### 1. Crear la base de datos

**Opción A — instalación nueva (recomendada):** ejecutar `backend/db/schema.sql`, que crea la base `sistema_incidencias`, las cuatro tablas con el esquema final y datos semilla de desarrollo.

Desde MySQL Workbench: abrir el archivo y ejecutarlo completo.

Desde PowerShell (si `mysql` está en el `PATH`):

```powershell
cmd /c "mysql -u root -p < backend\db\schema.sql"
```

**Opción B — base de datos existente con el esquema viejo:** hacer respaldo y ejecutar solo la migración aditiva:

```powershell
mysqldump -u root -p --result-file=respaldo_antes_001.sql sistema_incidencias
cmd /c "mysql -u root -p sistema_incidencias < backend\db\migraciones\001_roles_y_vinculos.sql"
```

La migración es idempotente en lo posible y **no elimina datos**. No ejecutar `schema.sql` sobre una base con datos si no se está seguro: está pensado para instalaciones nuevas. Ver [docs/BASE_DE_DATOS.md](docs/BASE_DE_DATOS.md).

### 2. Entorno virtual y dependencias

Desde la raíz del proyecto:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

Si PowerShell bloquea la activación:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### 3. Variables de entorno

```powershell
Copy-Item backend\.env.example backend\.env
```

Editar `backend/.env` con la contraseña local de MySQL y claves propias. **No compartir ni publicar** `.env`.

> `config.py` carga `.env` con `python-dotenv` y exige `SECRET_KEY` y `JWT_SECRET_KEY`. Si faltan, el backend no arranca y muestra un mensaje indicando qué variable configurar.

### 4. Ejecutar el backend

```powershell
cd backend
python app.py
```

Servidor: <http://localhost:5000>. Prueba rápida:

```powershell
curl.exe -X POST http://localhost:5000/api/login `
  -H "Content-Type: application/json" `
  -d '{\"correo\":\"admin@cutonala.udg.mx\",\"contrasena\":\"admin123\"}'
```

### 5. Migrar contraseñas existentes

Si tu base ya tiene usuarios con contraseñas en texto plano, **primero haz un respaldo** y después ejecuta el script desde `backend/`:

```powershell
# Respaldo de la base (si mysqldump está en el PATH)
mysqldump -u root -p --result-file=respaldo_antes_contrasenas.sql sistema_incidencias
```

> Si `mysqldump` no está en el `PATH`, exporta el respaldo desde MySQL Workbench (**Server → Data Export**).

```powershell
cd backend
python scripts\migrar_contrasenas.py --dry-run   # solo muestra lo que haría
python scripts\migrar_contrasenas.py             # hashea las contraseñas en texto plano
```

El script es idempotente: volver a ejecutarlo no altera las contraseñas que ya son hashes Werkzeug. No imprime contraseñas.

Si además quieres crear el usuario **Estudiante** de desarrollo vinculado al estudiante `id=1` (solo si no existe), indícalo explícitamente:

```powershell
python scripts\migrar_contrasenas.py --crear-estudiante
```

### 6. Ejecutar el frontend

Abrir la carpeta `frontend/` en VS Code y usar **Live Server** sobre `index.html` (por defecto <http://127.0.0.1:5500>). El frontend apunta a `http://localhost:5000/api` en `frontend/js/config.js`.

## Credenciales de desarrollo

Solo para entorno local. En `backend/db/schema.sql` las contraseñas se guardan como **hashes Werkzeug**. En una base existente hay que ejecutar `backend/scripts/migrar_contrasenas.py` una vez para convertir las contraseñas en texto plano.

| Rol | Usuario / matrícula | Contraseña |
|---|---|---|
| Administrador | `admin@cutonala.udg.mx` | `admin123` |
| Docente | `gabriel.navarro@cutonala.udg.mx` | `docente123` |
| Personal Responsable | `ana.torres@cutonala.udg.mx` | `resp123` |
| Estudiante | `jocelyn.silva@alumnos.udg.mx` o `219876543` | `estudiante123` |

> El usuario Estudiante se incluye en el esquema nuevo como semilla de desarrollo. En la base existente se crea con `python scripts\migrar_contrasenas.py --crear-estudiante`. El login acepta correo **o** matrícula y rechaza usuarios inactivos.

> ⚠️ **Importante:** el login usa `check_password_hash`. Si tu base todavía tiene contraseñas en texto plano, ejecuta el script de migración antes de probar el acceso.

## Estructura del proyecto

```
.
├── AGENTS.md
├── README.md
├── docs/
│   ├── ARQUITECTURA.md
│   ├── API.md
│   ├── BASE_DE_DATOS.md
│   ├── REGLAS_DE_NEGOCIO.md
│   └── ROADMAP.md
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── db.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── db/
│   │   ├── schema.sql
│   │   └── migraciones/001_roles_y_vinculos.sql
│   ├── scripts/
│   │   └── migrar_contrasenas.py
│   └── routes/
│       ├── __init__.py
│       ├── auth.py
│       ├── comunes.py
│       ├── estudiantes.py
│       ├── incidencias.py
│       ├── panel.py
│       └── usuarios.py
└── frontend/
    ├── index.html
    ├── css/styles.css
    └── js/{config,auth,app}.js
```

## Estado actual

| Área | Estado |
|---|---|
| Configuración por entorno | ✅ `config.py` + `backend/.env`; secretos fuera del código |
| Login con JWT | ✅ Correo o matrícula, `check_password_hash`, inactivos rechazados |
| Catálogo de estudiantes | ✅ GET con filtros y visibilidad por rol; POST con validaciones y `409` |
| Registro de incidencias | ✅ Admin/Docente/Estudiante, con departamento y responsable opcional |
| Lista de incidencias | ✅ `GET /api/incidencias` con filtros y acotamiento RN-01 |
| Detalle y bitácora | ✅ `GET /api/incidencias/<id>` con `bitacora_visible` |
| Ciclo de vida RN-03 | ✅ Máquina de estados completa; `responsable` no se sobrescribe |
| Gestión de usuarios | ✅ Listar, crear y activar/desactivar (solo Admin) |
| Rol Estudiante | ✅ Permisos, vínculo con estudiante y creación desde la API |
| Selector de responsables | ✅ `GET /api/responsables` (solo activos) |
| Métricas del panel | ✅ Totales y 5 recientes acotados por rol |
| Manejo de errores | ✅ 500 genéricos con logging; sin `str(e)` |
| Pruebas automatizadas | ⚠️ Verificado con script de 88 comprobaciones; suite formal en Fase 4 |

Detalle completo en [docs/ROADMAP.md](docs/ROADMAP.md).

## Respaldo de trabajo

El proyecto **no usa control de versiones**. Antes de cada fase el desarrollador copia la carpeta del proyecto como respaldo; al terminar, el agente lista exactamente los archivos creados, modificados y eliminados.

## Documentación

- [Arquitectura](docs/ARQUITECTURA.md)
- [API (contrato implementado)](docs/API.md)
- [Base de datos](docs/BASE_DE_DATOS.md)
- [Reglas de negocio](docs/REGLAS_DE_NEGOCIO.md)
- [Roadmap y plan de trabajo](docs/ROADMAP.md)
- [Guía para agentes](AGENTS.md)

## Créditos

- **Desarrollo:** Jocelyn Citlalli Silva Diaz.
- **Materia:** Ingeniería del Software, Act. 17.
- **Profesor:** Gabriel Navarro Salcedo.
- **Institución:** Centro Universitario de Tonalá, Universidad de Guadalajara.
