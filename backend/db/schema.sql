-- ============================================================================
-- Sistema de Gestión de Incidencias Escolares
-- Esquema COMPLETO final (instalación nueva) — MySQL 8 / InnoDB / utf8mb4
--
-- Uso:
--   PowerShell: cmd /c "mysql -u root -p < backend\db\schema.sql"
--   o ejecutar este archivo completo desde MySQL Workbench.
--
-- IMPORTANTE:
--   * Este script está pensado para una base NUEVA. Usa CREATE ... IF NOT EXISTS
--     y no elimina datos.
--   * Si ya existe la base con el esquema viejo, NO uses este archivo para
--     migrar: ejecuta backend/db/migraciones/001_roles_y_vinculos.sql.
--   * Para recrear desde cero una base existente hay que eliminarla manualmente
--     (acción destructiva, fuera de este script y sujeta a confirmación).
-- ============================================================================

CREATE DATABASE IF NOT EXISTS sistema_incidencias
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE sistema_incidencias;

SET NAMES utf8mb4;

-- ----------------------------------------------------------------------------
-- 1. Estudiantes (se crea primero por la FK de usuarios.id_estudiante)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS estudiantes (
    id          INT          NOT NULL AUTO_INCREMENT,
    matricula   VARCHAR(20)  NOT NULL,
    nombre      VARCHAR(100) NOT NULL,
    grado       VARCHAR(20)  NOT NULL,
    correo      VARCHAR(100) NOT NULL,
    telefono    VARCHAR(20)  NULL,
    creado_en   TIMESTAMP    NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY ux_estudiantes_matricula (matricula),
    UNIQUE KEY ux_estudiantes_correo (correo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 2. Usuarios
--    - rol incluye 'Estudiante'
--    - id_estudiante vincula la cuenta con su registro de estudiante
--    - activo permite bloquear el inicio de sesión
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id             INT          NOT NULL AUTO_INCREMENT,
    nombre         VARCHAR(100) NOT NULL,
    correo         VARCHAR(100) NOT NULL,
    contrasena     VARCHAR(255) NOT NULL,
    rol            ENUM('Administrador', 'Docente', 'Personal Responsable', 'Estudiante') NOT NULL,
    id_estudiante  INT          NULL,
    activo         TINYINT(1)   NOT NULL DEFAULT 1,
    creado_en      TIMESTAMP    NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY ux_usuarios_correo (correo),
    UNIQUE KEY ux_usuarios_id_estudiante (id_estudiante),
    KEY idx_usuarios_rol_activo (rol, activo),
    CONSTRAINT fk_usuarios_estudiante
        FOREIGN KEY (id_estudiante) REFERENCES estudiantes (id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 3. Incidencias
--    - reportado: usuario que registra (RN-02)
--    - responsable: usuario que atiende (opcional al crear)
--    - departamento: alternativa a persona asignada (Pantalla 4)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS incidencias (
    id             INT          NOT NULL AUTO_INCREMENT,
    id_estudiante  INT          NOT NULL,
    reportado      INT          NOT NULL,
    responsable    INT          NULL,
    tipo           VARCHAR(50)  NOT NULL,
    categoria      ENUM('Conducta', 'Académica', 'Asistencia', 'Otra') NOT NULL,
    prioridad      ENUM('Baja', 'Media', 'Alta', 'Urgente') NOT NULL DEFAULT 'Media',
    estado         ENUM('Registrada', 'En seguimiento', 'Cerrada') NOT NULL DEFAULT 'Registrada',
    descripcion    TEXT         NOT NULL,
    departamento   VARCHAR(100) NULL,
    fecha          DATETIME     NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_incidencias_estudiante (id_estudiante),
    KEY idx_incidencias_reportado (reportado),
    KEY idx_incidencias_responsable (responsable),
    KEY idx_incidencias_estado_fecha (estado, fecha),
    KEY idx_incidencias_categoria_prioridad (categoria, prioridad),
    KEY idx_incidencias_fecha (fecha),
    CONSTRAINT fk_incidencias_estudiante
        FOREIGN KEY (id_estudiante) REFERENCES estudiantes (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_incidencias_reportado
        FOREIGN KEY (reportado) REFERENCES usuarios (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_incidencias_responsable
        FOREIGN KEY (responsable) REFERENCES usuarios (id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 4. Historial de seguimiento (bitácora de auditoría, solo INSERT desde la API)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS historial_seguimiento (
    id                INT          NOT NULL AUTO_INCREMENT,
    incidencia        INT          NOT NULL,
    usuario           INT          NOT NULL,
    observacion       TEXT         NOT NULL,
    accion_realizada  VARCHAR(100) NOT NULL,
    fecha             DATETIME     NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_historial_incidencia_fecha (incidencia, fecha),
    KEY idx_historial_usuario (usuario),
    CONSTRAINT fk_historial_incidencia
        FOREIGN KEY (incidencia) REFERENCES incidencias (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_historial_usuario
        FOREIGN KEY (usuario) REFERENCES usuarios (id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- DATOS SEMILLA DE DESARROLLO
--
-- Las contraseñas están hasheadas con Werkzeug 3.0.1
-- (werkzeug.security.generate_password_hash, método scrypt).
-- Credenciales en texto plano SOLO para desarrollo local:
--   admin@cutonala.udg.mx        -> admin123
--   gabriel.navarro@cutonala.udg.mx -> docente123
--   ana.torres@cutonala.udg.mx   -> resp123
--   jocelyn.silva@alumnos.udg.mx / 219876543 -> estudiante123
-- ============================================================================

INSERT IGNORE INTO estudiantes (id, matricula, nombre, grado, correo, telefono) VALUES
    (1, '219876543', 'Jocelyn Citlalli Silva Diaz', '6to Semestre', 'jocelyn.silva@alumnos.udg.mx', '3312345678'),
    (2, '219112233', 'Carlos Eduardo López', '4to Semestre', 'carlos.lopez@alumnos.udg.mx', '3398765432');

INSERT IGNORE INTO usuarios (id, nombre, correo, contrasena, rol, id_estudiante, activo) VALUES
    (1, 'Administrador General', 'admin@cutonala.udg.mx',
        'scrypt:32768:8:1$BHcIQX2ZNS7xrH59$b9b295a750d877e96bfbf33bf464111890d1a4ae8cf97372171cc1dd1185606addd857c3c497c4503f6e147f467579ff69e6be8e09e2bdc1229c4c2895f47f6c',
        'Administrador', NULL, 1),
    (2, 'Gabriel Navarro (Maestro)', 'gabriel.navarro@cutonala.udg.mx',
        'scrypt:32768:8:1$sPjU7guOix0kblil$c65fc336a22b27015a90b56358a36138a22b5a1fa5ffe1157e65aac0a6be79f1c23438b6d884c5c31fc144122e514801f656ae0b7814b225a60edd4e3a9dea66',
        'Docente', NULL, 1),
    (3, 'Psic. Ana Torres', 'ana.torres@cutonala.udg.mx',
        'scrypt:32768:8:1$UfKKymz7lsnGCeSv$b6615d66c8bccab3d5b00592ba4f7da2ddcff3317d7cc4a663b31a367f28b8a945abc91d869e016229aa05017d467ec089d2cf7f76ab758081d670d5fd214dfe',
        'Personal Responsable', NULL, 1),
    (4, 'Jocelyn Citlalli Silva Diaz', 'jocelyn.silva@alumnos.udg.mx',
        'scrypt:32768:8:1$diY6r2OUNYWKiigl$dc3a72970c998bfd42808cd83d18c88da75f2bc51f578618f90c7346790577798fcd9f1462c64a1df9ba0b97887341e0dc3363918f3d9edbc7cdaf42ebb49c8a',
        'Estudiante', 1, 1);

INSERT IGNORE INTO incidencias
    (id, id_estudiante, reportado, responsable, tipo, categoria, prioridad, estado, descripcion, departamento, fecha)
VALUES
    (1, 1, 2, 3, 'Falta de entrega de actividades', 'Académica', 'Media', 'Registrada',
     'El alumno no ha entregado los últimos 3 avances del proyecto final.', NULL, '2026-09-19 11:14:37');

-- El historial se deja vacío en la semilla de desarrollo.

-- ============================================================================
-- Verificación rápida
-- ============================================================================
SELECT 'Esquema y datos semilla creados correctamente.' AS mensaje;
SELECT COUNT(*) AS usuarios FROM usuarios;
SELECT COUNT(*) AS estudiantes FROM estudiantes;
SELECT COUNT(*) AS incidencias FROM incidencias;
