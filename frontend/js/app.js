/* Lógica de las pantallas: panel, incidencias, estudiantes y usuarios. */

let usuarioActualApp = null;
let incidenciaDetalleActual = null;
let mensajeListaPendiente = null;

const SECCIONES_APP = [
    'sec-panel',
    'sec-incidencias',
    'sec-crear-incidencia',
    'sec-estudiantes',
    'sec-detalle-incidencia',
    'sec-usuarios'
];

/* -------------------------------------------------------------------------
 * Rol y permisos visuales
 * ---------------------------------------------------------------------- */

function rolActual() {
    return usuarioActualApp ? usuarioActualApp.rol : '';
}

function esAdministrador() {
    return rolActual() === 'Administrador';
}

function esDocente() {
    return rolActual() === 'Docente';
}

function esEstudiante() {
    return rolActual() === 'Estudiante';
}

function esResponsable() {
    return rolActual() === 'Personal Responsable';
}

function puedeCrearIncidencia() {
    return ['Administrador', 'Docente', 'Estudiante'].includes(rolActual());
}

/** Ajusta menú, formularios y textos según el rol autenticado. */
function aplicarPermisosUI() {
    document.getElementById('nav-nueva').classList.toggle('hidden', !puedeCrearIncidencia());
    document.getElementById('nav-usuarios').classList.toggle('hidden', !esAdministrador());
    document.getElementById('form-estudiante').classList.toggle('hidden', !esAdministrador());
    document.getElementById('grupo-filtro-estudiante')
        .classList.toggle('hidden', !(esAdministrador() || esDocente()));
    document.getElementById('grupo-filtro-responsable')
        .classList.toggle('hidden', !esAdministrador());

    const tituloPanel = document.getElementById('panel-titulo');
    const descripcionPanel = document.getElementById('panel-descripcion');

    if (esEstudiante()) {
        tituloPanel.textContent = 'Resumen de mis reportes';
        descripcionPanel.textContent = 'Incidencias que usted ha reportado.';
    } else if (esDocente()) {
        tituloPanel.textContent = 'Resumen de mis reportes';
        descripcionPanel.textContent = 'Incidencias registradas por usted.';
    } else if (esResponsable()) {
        tituloPanel.textContent = 'Resumen de mis casos asignados';
        descripcionPanel.textContent = 'Incidencias asignadas a su usuario.';
    } else {
        tituloPanel.textContent = 'Panel principal';
        descripcionPanel.textContent = 'Resumen general de incidencias.';
    }

    document.getElementById('estudiantes-descripcion').textContent = esEstudiante()
        ? 'Su registro de estudiante.'
        : 'Catálogo de estudiantes registrados.';
}

/** Punto de entrada llamado desde auth.js tras validar la sesión. */
function iniciarAplicacion(usuario) {
    usuarioActualApp = usuario;
    incidenciaDetalleActual = null;
    mensajeListaPendiente = null;

    aplicarPermisosUI();
    document.getElementById('form-filtros').reset();
    document.getElementById('form-filtros-usuarios').reset();

    if (esAdministrador() || esDocente()) {
        cargarEstudiantesSelect('filtro-estudiante', 'Todos los estudiantes');
    }
    if (esAdministrador()) {
        cargarResponsablesSelect('filtro-responsable', 'Todos los responsables');
        cargarEstudiantesSelect('usu-estudiante', 'Seleccione un estudiante');
    }

    navegarA('sec-panel');
}

/* -------------------------------------------------------------------------
 * Navegación
 * ---------------------------------------------------------------------- */

function navegarA(idSeccion) {
    if (idSeccion === 'sec-usuarios' && !esAdministrador()) {
        idSeccion = 'sec-panel';
    }
    if (idSeccion === 'sec-crear-incidencia' && !puedeCrearIncidencia()) {
        idSeccion = 'sec-panel';
    }

    SECCIONES_APP.forEach((id) => {
        const seccion = document.getElementById(id);
        if (seccion) {
            seccion.classList.toggle('hidden', id !== idSeccion);
        }
    });

    document.querySelectorAll('.nav-link').forEach((boton) => {
        const activo = boton.dataset.seccion === idSeccion
            || (idSeccion === 'sec-detalle-incidencia'
                && boton.dataset.seccion === 'sec-incidencias');
        boton.classList.toggle('activo', activo);
    });

    if (idSeccion === 'sec-panel') {
        cargarPanel();
    } else if (idSeccion === 'sec-incidencias') {
        cargarIncidencias();
    } else if (idSeccion === 'sec-crear-incidencia') {
        prepararFormularioIncidencia();
    } else if (idSeccion === 'sec-estudiantes') {
        cargarEstudiantes();
    } else if (idSeccion === 'sec-usuarios') {
        cargarUsuarios();
        cargarEstudiantesSelect('usu-estudiante', 'Seleccione un estudiante');
    }
}

/* -------------------------------------------------------------------------
 * Panel
 * ---------------------------------------------------------------------- */

async function cargarPanel() {
    ocultarMensaje('panel-mensaje');

    try {
        const respuesta = await fetchAPI('/panel/metricas');
        const datos = respuesta.datos || {};

        document.getElementById('panel-total-valor').textContent = String(datos.total ?? 0);
        renderizarMetricas('panel-metricas-estado', datos.por_estado);
        renderizarMetricas('panel-metricas-prioridad', datos.por_prioridad);
        renderizarMetricas('panel-metricas-categoria', datos.por_categoria);
        renderizarRecientesPanel(Array.isArray(datos.recientes) ? datos.recientes : []);
    } catch (error) {
        mostrarMensaje('panel-mensaje', error.message, 'error');
    }
}

function renderizarMetricas(idLista, mapa) {
    const lista = document.getElementById(idLista);
    lista.replaceChildren();

    const entradas = Object.entries(mapa || {});
    if (entradas.length === 0) {
        const item = document.createElement('li');
        item.textContent = 'Sin datos';
        lista.appendChild(item);
        return;
    }

    entradas.forEach(([etiqueta, valor]) => {
        const item = document.createElement('li');
        const nombre = document.createElement('span');
        nombre.textContent = etiqueta;
        const cantidad = document.createElement('strong');
        cantidad.textContent = String(valor);
        item.append(nombre, cantidad);
        lista.appendChild(item);
    });
}

function renderizarRecientesPanel(recientes) {
    const cuerpo = document.getElementById('panel-recientes-body');
    cuerpo.replaceChildren();

    recientes.forEach((incidencia) => {
        const fila = document.createElement('tr');
        fila.appendChild(crearCelda(incidencia.id));
        fila.appendChild(crearCelda(incidencia.estudiante_nombre));
        fila.appendChild(crearCelda(incidencia.categoria));
        fila.appendChild(crearCelda(incidencia.prioridad));

        const celdaEstado = document.createElement('td');
        celdaEstado.appendChild(crearBadgeEstado(incidencia.estado));
        fila.appendChild(celdaEstado);

        fila.appendChild(crearCelda(formatearFecha(incidencia.fecha)));

        const celdaAccion = document.createElement('td');
        celdaAccion.appendChild(crearBoton(
            'Ver detalle',
            'btn btn-secondary btn-sm',
            { accion: 'ver', id: incidencia.id }
        ));
        fila.appendChild(celdaAccion);

        cuerpo.appendChild(fila);
    });

    document.getElementById('panel-vacio').classList.toggle('hidden', recientes.length > 0);
}

/* -------------------------------------------------------------------------
 * Lista de incidencias
 * ---------------------------------------------------------------------- */

async function cargarIncidencias() {
    ocultarMensaje('lista-mensaje');

    const query = construirQuery({
        q: valorCampo('filtro-q'),
        estudiante: valorCampo('filtro-estudiante'),
        desde: valorCampo('filtro-desde'),
        hasta: valorCampo('filtro-hasta'),
        categoria: valorCampo('filtro-categoria'),
        prioridad: valorCampo('filtro-prioridad'),
        responsable: valorCampo('filtro-responsable'),
        estado: valorCampo('filtro-estado')
    });

    try {
        const respuesta = await fetchAPI(`/incidencias${query ? `?${query}` : ''}`);
        const incidencias = Array.isArray(respuesta.datos) ? respuesta.datos : [];

        renderizarTablaIncidencias(incidencias);
        document.getElementById('lista-vacio').classList.toggle('hidden', incidencias.length > 0);

        if (mensajeListaPendiente) {
            mostrarMensaje('lista-mensaje', mensajeListaPendiente, 'exito');
            mensajeListaPendiente = null;
        }
    } catch (error) {
        document.getElementById('tabla-incidencias-body').replaceChildren();
        document.getElementById('lista-vacio').classList.add('hidden');
        mostrarMensaje('lista-mensaje', error.message, 'error');
    }
}

function renderizarTablaIncidencias(incidencias) {
    const cuerpo = document.getElementById('tabla-incidencias-body');
    cuerpo.replaceChildren();

    incidencias.forEach((incidencia) => {
        const fila = document.createElement('tr');
        fila.appendChild(crearCelda(incidencia.id));
        fila.appendChild(crearCelda(incidencia.estudiante_nombre));
        fila.appendChild(crearCelda(incidencia.categoria));
        fila.appendChild(crearCelda(incidencia.prioridad));

        const celdaEstado = document.createElement('td');
        celdaEstado.appendChild(crearBadgeEstado(incidencia.estado));
        fila.appendChild(celdaEstado);

        fila.appendChild(crearCelda(formatearFecha(incidencia.fecha)));

        const celdaAccion = document.createElement('td');
        celdaAccion.appendChild(crearBoton(
            'Ver detalle',
            'btn btn-secondary btn-sm',
            { accion: 'ver', id: incidencia.id }
        ));
        fila.appendChild(celdaAccion);

        cuerpo.appendChild(fila);
    });
}

function manejarClicDetalle(evento) {
    const boton = evento.target.closest('button[data-accion="ver"]');
    if (!boton) {
        return;
    }

    const id = Number(boton.dataset.id);
    if (Number.isInteger(id) && id > 0) {
        abrirDetalle(id);
    }
}

/* -------------------------------------------------------------------------
 * Formulario de incidencia
 * ---------------------------------------------------------------------- */

async function prepararFormularioIncidencia() {
    ocultarMensaje('incidencia-mensaje');

    if (!puedeCrearIncidencia()) {
        mostrarMensaje(
            'incidencia-mensaje',
            'Su rol no puede registrar incidencias.',
            'error'
        );
        return;
    }

    const estudiante = esEstudiante();
    document.getElementById('grupo-inc-estudiante').classList.toggle('hidden', estudiante);
    document.getElementById('inc-nota-estudiante').classList.toggle('hidden', !estudiante);
    document.getElementById('grupo-inc-responsable')
        .classList.toggle('hidden', estudiante);

    if (!estudiante) {
        await Promise.all([
            cargarEstudiantesSelect('inc-estudiante', 'Seleccione un estudiante'),
            cargarResponsablesSelect('inc-responsable', 'Sin asignar')
        ]);
    }
}

/* -------------------------------------------------------------------------
 * Detalle y seguimiento
 * ---------------------------------------------------------------------- */

function abrirDetalle(id) {
    incidenciaDetalleActual = id;
    navegarA('sec-detalle-incidencia');
    cargarDetalle(id);
}

async function cargarDetalle(id) {
    ocultarMensaje('detalle-mensaje');
    ocultarMensaje('asignacion-mensaje');
    ocultarMensaje('seguimiento-mensaje');

    try {
        const respuesta = await fetchAPI(`/incidencias/${id}`);
        const datos = respuesta.datos || {};

        incidenciaDetalleActual = datos.id;
        renderizarDetalle(datos);
        configurarAsignacion(datos);
        configurarBitacora(datos);
        configurarSeguimiento(datos);
    } catch (error) {
        document.getElementById('detalle-info').replaceChildren();
        document.getElementById('bloque-asignacion').classList.add('hidden');
        document.getElementById('bloque-seguimiento').classList.add('hidden');
        mostrarMensaje('detalle-mensaje', error.message, 'error');
    }
}

function crearItemDetalle(etiqueta, valor) {
    const item = document.createElement('div');
    item.className = 'detalle-item';

    const nombre = document.createElement('span');
    nombre.className = 'detalle-etiqueta';
    nombre.textContent = etiqueta;

    const contenido = document.createElement('span');
    contenido.className = 'detalle-valor';
    contenido.textContent = valor === null || valor === undefined || valor === ''
        ? '—'
        : String(valor);

    item.append(nombre, contenido);
    return item;
}

function renderizarDetalle(datos) {
    const contenedor = document.getElementById('detalle-info');
    contenedor.replaceChildren();

    const campos = [
        ['Incidencia', `#${datos.id}`],
        ['Estudiante', datos.estudiante_nombre],
        ['Reportado por', datos.reportado_nombre],
        ['Responsable', datos.responsable_nombre || 'Sin asignar'],
        ['Departamento o persona', datos.departamento || 'No especificado'],
        ['Tipo', datos.tipo],
        ['Categoría', datos.categoria],
        ['Prioridad', datos.prioridad],
        ['Fecha de registro', formatearFecha(datos.fecha)]
    ];

    campos.forEach(([etiqueta, valor]) => {
        contenedor.appendChild(crearItemDetalle(etiqueta, valor));
    });

    const itemEstado = document.createElement('div');
    itemEstado.className = 'detalle-item';

    const etiquetaEstado = document.createElement('span');
    etiquetaEstado.className = 'detalle-etiqueta';
    etiquetaEstado.textContent = 'Estado';

    const valorEstado = document.createElement('span');
    valorEstado.className = 'detalle-valor';
    valorEstado.appendChild(crearBadgeEstado(datos.estado));

    itemEstado.append(etiquetaEstado, valorEstado);
    contenedor.appendChild(itemEstado);

    const itemDescripcion = document.createElement('div');
    itemDescripcion.className = 'detalle-item detalle-item-completo';

    const etiquetaDescripcion = document.createElement('span');
    etiquetaDescripcion.className = 'detalle-etiqueta';
    etiquetaDescripcion.textContent = 'Descripción';

    const valorDescripcion = document.createElement('span');
    valorDescripcion.className = 'detalle-valor';
    valorDescripcion.textContent = datos.descripcion || '—';

    itemDescripcion.append(etiquetaDescripcion, valorDescripcion);
    contenedor.appendChild(itemDescripcion);
}

async function configurarAsignacion(datos) {
    const bloque = document.getElementById('bloque-asignacion');
    const puedeAsignar = esAdministrador() && datos.estado !== 'Cerrada';
    bloque.classList.toggle('hidden', !puedeAsignar);

    if (!puedeAsignar) {
        return;
    }

    await cargarResponsablesSelect(
        'det-responsable',
        'Seleccione un responsable',
        datos.responsable || null
    );

    const boton = document.getElementById('btn-asignar-responsable');
    const hayOpciones = document.getElementById('det-responsable').options.length > 1;
    boton.disabled = !hayOpciones;

    if (!hayOpciones) {
        mostrarMensaje(
            'asignacion-mensaje',
            'No hay usuarios activos con rol Personal Responsable.',
            'info'
        );
    }
}

function configurarBitacora(datos) {
    const visible = datos.bitacora_visible === true;
    const contenedor = document.getElementById('bitacora-contenedor');
    const privada = document.getElementById('bitacora-privada');
    const vacia = document.getElementById('bitacora-vacia');
    const cuerpo = document.getElementById('bitacora-body');

    cuerpo.replaceChildren();
    privada.classList.toggle('hidden', visible);
    contenedor.classList.toggle('hidden', !visible);

    if (!visible) {
        vacia.classList.add('hidden');
        return;
    }

    const bitacora = Array.isArray(datos.bitacora) ? datos.bitacora : [];
    bitacora.forEach((entrada) => {
        const fila = document.createElement('tr');
        fila.appendChild(crearCelda(formatearFecha(entrada.fecha)));
        fila.appendChild(crearCelda(entrada.usuario_nombre));
        fila.appendChild(crearCelda(entrada.accion_realizada));
        fila.appendChild(crearCelda(entrada.observacion));
        cuerpo.appendChild(fila);
    });

    vacia.classList.toggle('hidden', bitacora.length > 0);
}

function configurarSeguimiento(datos) {
    const bloque = document.getElementById('bloque-seguimiento');
    const esResponsableAsignado = esResponsable()
        && datos.responsable === (usuarioActualApp ? usuarioActualApp.id : null);
    const puedeSeguir = (esAdministrador() || esResponsableAsignado)
        && datos.estado !== 'Cerrada';

    bloque.classList.toggle('hidden', !puedeSeguir);

    if (!puedeSeguir) {
        return;
    }

    document.getElementById('seg-incidencia-id').value = String(datos.id);
    document.getElementById('seg-observacion').value = '';

    const select = document.getElementById('seg-estado');
    select.replaceChildren();

    const soloObservacion = document.createElement('option');
    soloObservacion.value = '';
    soloObservacion.textContent = 'Solo registrar observación';
    select.appendChild(soloObservacion);

    if (datos.estado === 'Registrada' && datos.responsable) {
        const opcion = document.createElement('option');
        opcion.value = 'En seguimiento';
        opcion.textContent = 'Pasar a En seguimiento';
        select.appendChild(opcion);
    }

    if (datos.estado === 'En seguimiento') {
        const opcion = document.createElement('option');
        opcion.value = 'Cerrada';
        opcion.textContent = 'Cerrar incidencia';
        select.appendChild(opcion);
    }

    select.value = '';

    const ayuda = document.getElementById('seg-ayuda');
    if (datos.estado === 'Registrada' && !datos.responsable) {
        ayuda.textContent = 'Asigne un responsable para poder pasar la incidencia a En seguimiento.';
        ayuda.classList.remove('hidden');
    } else {
        ayuda.textContent = '';
        ayuda.classList.add('hidden');
    }
}

/* -------------------------------------------------------------------------
 * Estudiantes
 * ---------------------------------------------------------------------- */

async function cargarEstudiantesSelect(idSelect, textoInicial = 'Seleccione un estudiante',
    valorSeleccionado = null) {
    const select = document.getElementById(idSelect);
    if (!select) {
        return;
    }

    try {
        const respuesta = await fetchAPI('/estudiantes');
        const estudiantes = Array.isArray(respuesta.datos) ? respuesta.datos : [];
        const opciones = estudiantes.map((estudiante) => ({
            valor: estudiante.id,
            texto: `${estudiante.nombre} (${estudiante.matricula})`
        }));

        llenarSelect(select, opciones, textoInicial, valorSeleccionado);
    } catch (error) {
        llenarSelect(select, [], textoInicial, null);
        console.error(error);
    }
}

async function cargarResponsablesSelect(idSelect, textoInicial = 'Sin asignar',
    valorSeleccionado = null) {
    const select = document.getElementById(idSelect);
    if (!select) {
        return;
    }

    try {
        const respuesta = await fetchAPI('/responsables');
        const responsables = Array.isArray(respuesta.datos) ? respuesta.datos : [];
        const opciones = responsables.map((responsable) => ({
            valor: responsable.id,
            texto: responsable.nombre
        }));

        llenarSelect(select, opciones, textoInicial, valorSeleccionado);
    } catch (error) {
        llenarSelect(select, [], textoInicial, null);
        console.error(error);
    }
}

async function cargarEstudiantes() {
    ocultarMensaje('estudiantes-mensaje');

    const estudiante = esEstudiante();
    const columnas = estudiante
        ? ['ID', 'Nombre', 'Matrícula']
        : ['ID', 'Matrícula', 'Nombre', 'Grado', 'Correo', 'Teléfono'];

    const cabecera = document.getElementById('tabla-estudiantes-head');
    cabecera.replaceChildren();
    columnas.forEach((titulo) => {
        const celda = document.createElement('th');
        celda.textContent = titulo;
        cabecera.appendChild(celda);
    });

    try {
        const respuesta = await fetchAPI('/estudiantes');
        const estudiantes = Array.isArray(respuesta.datos) ? respuesta.datos : [];
        const cuerpo = document.getElementById('tabla-estudiantes-body');
        cuerpo.replaceChildren();

        estudiantes.forEach((registro) => {
            const fila = document.createElement('tr');
            fila.appendChild(crearCelda(registro.id));

            if (estudiante) {
                fila.appendChild(crearCelda(registro.nombre));
                fila.appendChild(crearCelda(registro.matricula));
            } else {
                fila.appendChild(crearCelda(registro.matricula));
                fila.appendChild(crearCelda(registro.nombre));
                fila.appendChild(crearCelda(registro.grado));
                fila.appendChild(crearCelda(registro.correo));
                fila.appendChild(crearCelda(registro.telefono));
            }

            cuerpo.appendChild(fila);
        });

        document.getElementById('estudiantes-vacio')
            .classList.toggle('hidden', estudiantes.length > 0);
    } catch (error) {
        document.getElementById('tabla-estudiantes-body').replaceChildren();
        document.getElementById('estudiantes-vacio').classList.add('hidden');
        mostrarMensaje('estudiantes-mensaje', error.message, 'error');
    }
}

/* -------------------------------------------------------------------------
 * Usuarios
 * ---------------------------------------------------------------------- */

async function cargarUsuarios() {
    if (!esAdministrador()) {
        return;
    }

    ocultarMensaje('usuarios-mensaje');

    const query = construirQuery({
        rol: valorCampo('filtro-usu-rol'),
        activo: valorCampo('filtro-usu-activo')
    });

    try {
        const respuesta = await fetchAPI(`/usuarios${query ? `?${query}` : ''}`);
        const usuarios = Array.isArray(respuesta.datos) ? respuesta.datos : [];
        const cuerpo = document.getElementById('tabla-usuarios-body');
        cuerpo.replaceChildren();

        usuarios.forEach((usuario) => {
            const fila = document.createElement('tr');
            fila.appendChild(crearCelda(usuario.id));
            fila.appendChild(crearCelda(usuario.nombre));
            fila.appendChild(crearCelda(usuario.correo));
            fila.appendChild(crearCelda(usuario.rol));
            fila.appendChild(crearCelda(
                usuario.id_estudiante ? `#${usuario.id_estudiante}` : '—'
            ));
            fila.appendChild(crearCelda(usuario.activo ? 'Sí' : 'No'));

            const celdaAccion = document.createElement('td');
            const esPropio = usuarioActualApp && usuario.id === usuarioActualApp.id;
            const boton = crearBoton(
                usuario.activo ? 'Desactivar' : 'Activar',
                `btn btn-sm ${usuario.activo ? 'btn-danger' : 'btn-success'}`,
                {
                    accion: 'estado',
                    id: usuario.id,
                    activo: usuario.activo ? '0' : '1'
                }
            );

            if (esPropio) {
                boton.disabled = true;
                boton.title = 'No puede desactivar su propia cuenta.';
            }

            celdaAccion.appendChild(boton);
            fila.appendChild(celdaAccion);
            cuerpo.appendChild(fila);
        });

        document.getElementById('usuarios-vacio')
            .classList.toggle('hidden', usuarios.length > 0);
    } catch (error) {
        document.getElementById('tabla-usuarios-body').replaceChildren();
        document.getElementById('usuarios-vacio').classList.add('hidden');
        mostrarMensaje('usuarios-mensaje', error.message, 'error');
    }
}

/* -------------------------------------------------------------------------
 * Eventos de la interfaz
 * ---------------------------------------------------------------------- */

document.querySelector('.nav-menu').addEventListener('click', (evento) => {
    const boton = evento.target.closest('.nav-link');
    if (boton && boton.dataset.seccion) {
        navegarA(boton.dataset.seccion);
    }
});

document.getElementById('form-filtros').addEventListener('submit', (evento) => {
    evento.preventDefault();
    mensajeListaPendiente = null;
    cargarIncidencias();
});

document.getElementById('btn-limpiar-filtros').addEventListener('click', () => {
    document.getElementById('form-filtros').reset();
    mensajeListaPendiente = null;
    cargarIncidencias();
});

document.getElementById('panel-recientes-body').addEventListener('click', manejarClicDetalle);
document.getElementById('tabla-incidencias-body').addEventListener('click', manejarClicDetalle);

document.getElementById('btn-volver-lista').addEventListener('click', () => {
    navegarA('sec-incidencias');
});

document.getElementById('form-incidencia').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    ocultarMensaje('incidencia-mensaje');

    if (!puedeCrearIncidencia()) {
        mostrarMensaje(
            'incidencia-mensaje',
            'Su rol no puede registrar incidencias.',
            'error'
        );
        return;
    }

    const tipo = valorCampo('inc-tipo').trim();
    const descripcion = valorCampo('inc-descripcion').trim();
    const categoria = valorCampo('inc-categoria');
    const prioridad = valorCampo('inc-prioridad');

    if (!tipo) {
        mostrarMensaje('incidencia-mensaje', 'El tipo de incidencia es obligatorio.', 'error');
        return;
    }
    if (!descripcion) {
        mostrarMensaje('incidencia-mensaje', 'La descripción es obligatoria.', 'error');
        return;
    }
    if (!categoria) {
        mostrarMensaje('incidencia-mensaje', 'Seleccione una categoría.', 'error');
        return;
    }

    const payload = { tipo, categoria, prioridad, descripcion };

    const departamento = valorCampo('inc-departamento').trim();
    if (departamento) {
        payload.departamento = departamento;
    }

    // Un Estudiante no envía id_estudiante ni responsable: el backend usa
    // su vínculo y rechaza el campo responsable con 403.
    if (!esEstudiante()) {
        const idEstudiante = valorCampo('inc-estudiante');
        if (!idEstudiante) {
            mostrarMensaje('incidencia-mensaje', 'Seleccione un estudiante.', 'error');
            return;
        }
        payload.id_estudiante = Number(idEstudiante);

        const responsable = valorCampo('inc-responsable');
        if (responsable) {
            payload.responsable = Number(responsable);
        }
    }

    const boton = evento.submitter || evento.target.querySelector('button[type="submit"]');
    if (boton) {
        boton.disabled = true;
    }

    try {
        const respuesta = await fetchAPI('/incidencias', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        evento.target.reset();
        document.getElementById('inc-prioridad').value = 'Media';
        mensajeListaPendiente = respuesta.mensaje;
        navegarA('sec-incidencias');
        cargarPanel();
    } catch (error) {
        mostrarMensaje('incidencia-mensaje', error.message, 'error');
    } finally {
        if (boton) {
            boton.disabled = false;
        }
    }
});

document.getElementById('btn-asignar-responsable').addEventListener('click', async () => {
    ocultarMensaje('asignacion-mensaje');

    const id = incidenciaDetalleActual;
    if (!id) {
        return;
    }

    const responsable = valorCampo('det-responsable');
    if (!responsable) {
        mostrarMensaje('asignacion-mensaje', 'Seleccione un responsable.', 'error');
        return;
    }

    const boton = document.getElementById('btn-asignar-responsable');
    boton.disabled = true;

    try {
        const respuesta = await fetchAPI(`/incidencias/${id}/responsable`, {
            method: 'PUT',
            body: JSON.stringify({ responsable: Number(responsable) })
        });

        await cargarDetalle(id);
        mostrarMensaje('asignacion-mensaje', respuesta.mensaje, 'exito');
        cargarIncidencias();
        cargarPanel();
    } catch (error) {
        mostrarMensaje('asignacion-mensaje', error.message, 'error');
        boton.disabled = false;
    }
});

document.getElementById('form-seguimiento').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    ocultarMensaje('seguimiento-mensaje');

    const id = incidenciaDetalleActual;
    if (!id) {
        mostrarMensaje('seguimiento-mensaje', 'No hay una incidencia seleccionada.', 'error');
        return;
    }

    const observacion = valorCampo('seg-observacion').trim();
    if (!observacion) {
        mostrarMensaje('seguimiento-mensaje', 'La observación es obligatoria.', 'error');
        return;
    }

    const payload = { observacion };
    const nuevoEstado = valorCampo('seg-estado');
    if (nuevoEstado) {
        payload.nuevo_estado = nuevoEstado;
    }

    const boton = evento.submitter || evento.target.querySelector('button[type="submit"]');
    if (boton) {
        boton.disabled = true;
    }

    try {
        const respuesta = await fetchAPI(`/incidencias/${id}/seguimiento`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        await cargarDetalle(id);
        mostrarMensaje('seguimiento-mensaje', respuesta.mensaje, 'exito');
        cargarIncidencias();
        cargarPanel();
    } catch (error) {
        mostrarMensaje('seguimiento-mensaje', error.message, 'error');
    } finally {
        if (boton) {
            boton.disabled = false;
        }
    }
});

document.getElementById('form-estudiante').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    ocultarMensaje('estudiante-mensaje');

    if (!esAdministrador()) {
        return;
    }

    const matricula = valorCampo('est-matricula').trim();
    const nombre = valorCampo('est-nombre').trim();
    const grado = valorCampo('est-grado').trim();
    const correo = valorCampo('est-correo').trim();
    const telefono = valorCampo('est-telefono').trim();

    if (!matricula || !nombre || !grado || !correo) {
        mostrarMensaje(
            'estudiante-mensaje',
            'Matrícula, nombre, grado y correo son obligatorios.',
            'error'
        );
        return;
    }

    const payload = { matricula, nombre, grado, correo };
    if (telefono) {
        payload.telefono = telefono;
    }

    const boton = evento.submitter || evento.target.querySelector('button[type="submit"]');
    if (boton) {
        boton.disabled = true;
    }

    try {
        const respuesta = await fetchAPI('/estudiantes', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        evento.target.reset();
        await cargarEstudiantes();
        mostrarMensaje('estudiante-mensaje', respuesta.mensaje, 'exito');

        cargarEstudiantesSelect('inc-estudiante', 'Seleccione un estudiante');
        cargarEstudiantesSelect('usu-estudiante', 'Seleccione un estudiante');
        cargarEstudiantesSelect('filtro-estudiante', 'Todos los estudiantes');
    } catch (error) {
        mostrarMensaje('estudiante-mensaje', error.message, 'error');
    } finally {
        if (boton) {
            boton.disabled = false;
        }
    }
});

document.getElementById('usu-rol').addEventListener('change', () => {
    const esEstudianteSeleccionado = valorCampo('usu-rol') === 'Estudiante';
    document.getElementById('grupo-usu-estudiante')
        .classList.toggle('hidden', !esEstudianteSeleccionado);

    if (esEstudianteSeleccionado) {
        cargarEstudiantesSelect('usu-estudiante', 'Seleccione un estudiante');
    }
});

document.getElementById('form-usuario').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    ocultarMensaje('usuario-mensaje');

    if (!esAdministrador()) {
        return;
    }

    const nombre = valorCampo('usu-nombre').trim();
    const correo = valorCampo('usu-correo').trim();
    const contrasena = valorCampo('usu-contrasena');
    const rol = valorCampo('usu-rol');

    if (!nombre || !correo || !contrasena || !rol) {
        mostrarMensaje(
            'usuario-mensaje',
            'Complete todos los campos obligatorios.',
            'error'
        );
        return;
    }

    if (contrasena.length < 8) {
        mostrarMensaje(
            'usuario-mensaje',
            'La contraseña debe tener al menos 8 caracteres.',
            'error'
        );
        return;
    }

    const payload = {
        nombre,
        correo,
        contrasena,
        rol,
        activo: Number(valorCampo('usu-activo'))
    };

    if (rol === 'Estudiante') {
        const idEstudiante = valorCampo('usu-estudiante');
        if (!idEstudiante) {
            mostrarMensaje(
                'usuario-mensaje',
                'Seleccione el estudiante vinculado.',
                'error'
            );
            return;
        }
        payload.id_estudiante = Number(idEstudiante);
    }

    const boton = evento.submitter || evento.target.querySelector('button[type="submit"]');
    if (boton) {
        boton.disabled = true;
    }

    try {
        const respuesta = await fetchAPI('/usuarios', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        evento.target.reset();
        document.getElementById('grupo-usu-estudiante').classList.add('hidden');
        await cargarUsuarios();
        mostrarMensaje('usuario-mensaje', respuesta.mensaje, 'exito');
        cargarEstudiantesSelect('usu-estudiante', 'Seleccione un estudiante');
    } catch (error) {
        mostrarMensaje('usuario-mensaje', error.message, 'error');
    } finally {
        if (boton) {
            boton.disabled = false;
        }
    }
});

document.getElementById('form-filtros-usuarios').addEventListener('submit', (evento) => {
    evento.preventDefault();
    cargarUsuarios();
});

document.getElementById('tabla-usuarios-body').addEventListener('click', async (evento) => {
    const boton = evento.target.closest('button[data-accion="estado"]');
    if (!boton) {
        return;
    }

    const id = Number(boton.dataset.id);
    const activo = boton.dataset.activo === '1';
    boton.disabled = true;

    try {
        const respuesta = await fetchAPI(`/usuarios/${id}/estado`, {
            method: 'PUT',
            body: JSON.stringify({ activo })
        });

        await cargarUsuarios();
        mostrarMensaje('usuarios-mensaje', respuesta.mensaje, 'exito');
    } catch (error) {
        mostrarMensaje('usuarios-mensaje', error.message, 'error');
        boton.disabled = false;
    }
});
