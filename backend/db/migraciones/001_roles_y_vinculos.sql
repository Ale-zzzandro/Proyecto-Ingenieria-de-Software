-- ============================================================================
-- Migración 001 — Roles y vínculos
-- Sistema de Gestión de Incidencias Escolares
--
-- Objetivo (solo cambios aditivos, sin borrar datos):
--   1. Agregar 'Estudiante' al ENUM usuarios.rol.
--   2. Agregar usuarios.id_estudiante (NULL, UNIQUE, FK -> estudiantes.id ON DELETE RESTRICT).
--   3. Agregar usuarios.activo (TINYINT(1) NOT NULL DEFAULT 1).
--   4. Agregar incidencias.departamento (VARCHAR(100) NULL).
--   5. Crear índices de consulta.
--
-- Requisitos:
--   * MySQL 8.
--   * Base existente con las tablas en minúscula (usuarios, estudiantes,
--     incidencias, historial_seguimiento). Si el servidor distingue mayúsculas,
--     ajustar los nombres antes de ejecutar.
--
-- ANTES DE EJECUTAR: hacer respaldo.
--   mysqldump -u root -p --result-file=respaldo_antes_001.sql sistema_incidencias
--
-- Este script NO ejecuta DROP TABLE, TRUNCATE ni DELETE.
-- Es idempotente en lo posible: puede re-ejecutarse sin error.
-- ============================================================================

USE sistema_incidencias;
SET NAMES utf8mb4;

-- ----------------------------------------------------------------------------
-- 1. Nuevo rol 'Estudiante'
--    MODIFY COLUMN es seguro al re-ejecutar.
-- ----------------------------------------------------------------------------
ALTER TABLE usuarios
    MODIFY COLUMN rol ENUM('Administrador', 'Docente', 'Personal Responsable', 'Estudiante') NOT NULL;

-- ----------------------------------------------------------------------------
-- 2. Procedimiento auxiliar: agregar columna solo si no existe
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_agregar_columna_si_no_existe;

DELIMITER $$
CREATE PROCEDURE sp_agregar_columna_si_no_existe(
    IN p_tabla VARCHAR(64),
    IN p_columna VARCHAR(64),
    IN p_definicion VARCHAR(255)
)
BEGIN
    IF (SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = p_tabla
          AND COLUMN_NAME = p_columna) = 0 THEN
        SET @sql_ddl = CONCAT(
            'ALTER TABLE `', p_tabla, '` ADD COLUMN `', p_columna, '` ', p_definicion
        );
        PREPARE stmt FROM @sql_ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$
DELIMITER ;

CALL sp_agregar_columna_si_no_existe(
    'usuarios',
    'id_estudiante',
    'INT NULL AFTER `rol`'
);

CALL sp_agregar_columna_si_no_existe(
    'usuarios',
    'activo',
    'TINYINT(1) NOT NULL DEFAULT 1 AFTER `contrasena`'
);

CALL sp_agregar_columna_si_no_existe(
    'incidencias',
    'departamento',
    'VARCHAR(100) NULL AFTER `responsable`'
);

DROP PROCEDURE IF EXISTS sp_agregar_columna_si_no_existe;

-- ----------------------------------------------------------------------------
-- 3. Procedimiento auxiliar: crear índice (normal o UNIQUE) solo si no existe
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_crear_indice_si_no_existe;

DELIMITER $$
CREATE PROCEDURE sp_crear_indice_si_no_existe(
    IN p_tabla VARCHAR(64),
    IN p_indice VARCHAR(64),
    IN p_columnas VARCHAR(255),
    IN p_unico TINYINT
)
BEGIN
    IF (SELECT COUNT(*)
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = p_tabla
          AND INDEX_NAME = p_indice) = 0 THEN
        SET @sql_ddl = CONCAT(
            'CREATE ', IF(p_unico = 1, 'UNIQUE ', ''),
            'INDEX `', p_indice, '` ON `', p_tabla, '` (', p_columnas, ')'
        );
        PREPARE stmt FROM @sql_ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$
DELIMITER ;

-- Una cuenta de estudiante por registro de estudiante
CALL sp_crear_indice_si_no_existe(
    'usuarios',
    'ux_usuarios_id_estudiante',
    '`id_estudiante`',
    1
);

-- Filtros de usuarios/responsables
CALL sp_crear_indice_si_no_existe(
    'usuarios',
    'idx_usuarios_rol_activo',
    '`rol`, `activo`',
    0
);

-- Filtros y orden del listado/panel
CALL sp_crear_indice_si_no_existe(
    'incidencias',
    'idx_incidencias_estado_fecha',
    '`estado`, `fecha`',
    0
);

CALL sp_crear_indice_si_no_existe(
    'incidencias',
    'idx_incidencias_categoria_prioridad',
    '`categoria`, `prioridad`',
    0
);

CALL sp_crear_indice_si_no_existe(
    'incidencias',
    'idx_incidencias_fecha',
    '`fecha`',
    0
);

-- Cronología de la bitácora por incidencia
CALL sp_crear_indice_si_no_existe(
    'historial_seguimiento',
    'idx_historial_incidencia_fecha',
    '`incidencia`, `fecha`',
    0
);

DROP PROCEDURE IF EXISTS sp_crear_indice_si_no_existe;

-- ----------------------------------------------------------------------------
-- 4. Procedimiento auxiliar: crear la FK usuarios.id_estudiante si no existe
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_agregar_fk_usuarios_estudiante;

DELIMITER $$
CREATE PROCEDURE sp_agregar_fk_usuarios_estudiante()
BEGIN
    IF (SELECT COUNT(*)
        FROM information_schema.TABLE_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = DATABASE()
          AND TABLE_NAME = 'usuarios'
          AND CONSTRAINT_NAME = 'fk_usuarios_estudiante'
          AND CONSTRAINT_TYPE = 'FOREIGN KEY') = 0 THEN
        SET @sql_ddl = CONCAT(
            'ALTER TABLE `usuarios` ADD CONSTRAINT `fk_usuarios_estudiante` ',
            'FOREIGN KEY (`id_estudiante`) REFERENCES `estudiantes` (`id`) ',
            'ON DELETE RESTRICT'
        );
        PREPARE stmt FROM @sql_ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$
DELIMITER ;

CALL sp_agregar_fk_usuarios_estudiante();

DROP PROCEDURE IF EXISTS sp_agregar_fk_usuarios_estudiante;

-- ----------------------------------------------------------------------------
-- 5. Verificación
-- ----------------------------------------------------------------------------
SELECT 'Migración 001 aplicada. Revisar las columnas, índices y FK.' AS mensaje;

SHOW COLUMNS FROM usuarios;
SHOW COLUMNS FROM incidencias;

SHOW INDEX FROM usuarios
    WHERE Key_name IN ('ux_usuarios_id_estudiante', 'idx_usuarios_rol_activo');

SHOW INDEX FROM incidencias
    WHERE Key_name IN (
        'idx_incidencias_estado_fecha',
        'idx_incidencias_categoria_prioridad',
        'idx_incidencias_fecha'
    );

SHOW INDEX FROM historial_seguimiento
    WHERE Key_name = 'idx_historial_incidencia_fecha';

SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = DATABASE()
  AND TABLE_NAME = 'usuarios'
  AND CONSTRAINT_NAME = 'fk_usuarios_estudiante';

-- ----------------------------------------------------------------------------
-- 6. Notas
-- ----------------------------------------------------------------------------
-- * La regla "id_estudiante obligatorio si rol = 'Estudiante'" se valida en la
--   aplicación (Fase 2); no se agrega CHECK para mantener compatibilidad.
-- * Las contraseñas existentes siguen en texto plano hasta ejecutar
--   backend/scripts/migrar_contrasenas.py (Fase 1).
-- * La cuenta de estudiante de desarrollo se crea con POST /api/usuarios
--   (Fase 2) o mediante un INSERT con hash generado por Werkzeug.
-- * Reversión: no se eliminan columnas automáticamente. Restaurar el respaldo
--   si fuera necesario.
-- ============================================================================
