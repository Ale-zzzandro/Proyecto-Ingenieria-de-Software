/* Utilidades compartidas: sesión, llamadas a la API y renderizado seguro. */

const TOKEN_KEY = 'token';
const USUARIO_KEY = 'usuario';

/** Error con el código HTTP y el mensaje devuelto por el servidor. */
class ErrorAPI extends Error {
    constructor(mensaje, codigo = 0, datos = null) {
        super(mensaje);
        this.name = 'ErrorAPI';
        this.codigo = codigo;
        this.datos = datos;
    }
}

/* -------------------------------------------------------------------------
 * Sesión
 * ---------------------------------------------------------------------- */

function obtenerToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function obtenerUsuarioGuardado() {
    const texto = localStorage.getItem(USUARIO_KEY);
    if (!texto) {
        return null;
    }
    try {
        const usuario = JSON.parse(texto);
        return usuario && typeof usuario === 'object' ? usuario : null;
    } catch (error) {
        return null;
    }
}

function guardarSesion(token, usuario) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USUARIO_KEY, JSON.stringify(usuario));
}

function limpiarSesion() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USUARIO_KEY);
}

/* -------------------------------------------------------------------------
 * API
 * ---------------------------------------------------------------------- */

/**
 * Realiza una petición a la API con el token de sesión.
 *
 * @param {string} ruta Ruta relativa, por ejemplo "/incidencias".
 * @param {object} opciones Opciones de fetch. `sinSesion` evita enviar token.
 * @returns {Promise<object|null>} Cuerpo JSON de la respuesta.
 */
async function fetchAPI(ruta, opciones = {}) {
    const { sinSesion = false, ...resto } = opciones;
    const cabeceras = new Headers(resto.headers || {});
    const token = obtenerToken();

    if (!sinSesion && token) {
        cabeceras.set('Authorization', `Bearer ${token}`);
    }

    if (resto.body !== undefined && resto.body !== null
        && !cabeceras.has('Content-Type')) {
        cabeceras.set('Content-Type', 'application/json');
    }

    let respuesta;
    try {
        respuesta = await fetch(`${API_URL}${ruta}`, { ...resto, headers: cabeceras });
    } catch (error) {
        throw new ErrorAPI(
            'No se pudo conectar con el servidor. Verifique que el backend esté en ejecución.',
            0
        );
    }

    let datos = null;
    const texto = await respuesta.text();
    if (texto) {
        try {
            datos = JSON.parse(texto);
        } catch (error) {
            datos = null;
        }
    }

    if (!respuesta.ok) {
        const mensaje = (datos && datos.mensaje)
            || `Error ${respuesta.status} al procesar la solicitud.`;

        if (respuesta.status === 401 && !sinSesion && token) {
            limpiarSesion();
            window.dispatchEvent(new CustomEvent('sesion-expirada', { detail: mensaje }));
        }

        throw new ErrorAPI(mensaje, respuesta.status, datos);
    }

    return datos;
}

/* -------------------------------------------------------------------------
 * Formato y DOM seguro
 * ---------------------------------------------------------------------- */

/** Construye un query string omitiendo valores vacíos. */
function construirQuery(parametros) {
    const busqueda = new URLSearchParams();

    Object.entries(parametros).forEach(([clave, valor]) => {
        if (valor !== undefined && valor !== null && String(valor).trim() !== '') {
            busqueda.append(clave, String(valor).trim());
        }
    });

    return busqueda.toString();
}

/** Convierte "YYYY-MM-DD HH:MM:SS" a una fecha local legible. */
function formatearFecha(valor) {
    if (!valor) {
        return '—';
    }

    const coincidencia = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/
        .exec(String(valor));

    if (!coincidencia) {
        return String(valor);
    }

    const [, anio, mes, dia, hora = '00', minuto = '00', segundo = '00'] = coincidencia;
    const fecha = new Date(
        Number(anio),
        Number(mes) - 1,
        Number(dia),
        Number(hora),
        Number(minuto),
        Number(segundo)
    );

    if (Number.isNaN(fecha.getTime())) {
        return String(valor);
    }

    return fecha.toLocaleString('es-MX', {
        dateStyle: 'short',
        timeStyle: 'short'
    });
}

/** Escapa texto para usarlo dentro de HTML si fuera necesario. */
function escaparHTML(valor) {
    return String(valor === null || valor === undefined ? '' : valor)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/** Muestra u oculta un mensaje de la interfaz. */
function mostrarMensaje(idElemento, texto, tipo = 'info') {
    const elemento = document.getElementById(idElemento);
    if (!elemento) {
        return;
    }

    elemento.textContent = texto || '';
    elemento.classList.remove('error', 'exito', 'info');
    elemento.classList.toggle('hidden', !texto);

    if (texto) {
        elemento.classList.add(tipo);
    }
}

function ocultarMensaje(idElemento) {
    mostrarMensaje(idElemento, '', 'info');
}

function valorCampo(idElemento) {
    const elemento = document.getElementById(idElemento);
    return elemento ? elemento.value : '';
}

/** Crea una celda de tabla con texto seguro. */
function crearCelda(texto) {
    const celda = document.createElement('td');
    celda.textContent = texto === null || texto === undefined || texto === ''
        ? '—'
        : String(texto);
    return celda;
}

/** Crea un botón con atributos data-* para delegación de eventos. */
function crearBoton(texto, clases, datos = {}) {
    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = clases;
    boton.textContent = texto;

    Object.entries(datos).forEach(([clave, valor]) => {
        boton.dataset[clave] = String(valor);
    });

    return boton;
}

/** Devuelve la clase CSS del badge según el estado. */
function claseBadgeEstado(estado) {
    switch (estado) {
        case 'En seguimiento':
            return 'badge-Seguimiento';
        case 'Cerrada':
            return 'badge-Cerrada';
        case 'Registrada':
        default:
            return 'badge-Registrada';
    }
}

function crearBadgeEstado(estado) {
    const badge = document.createElement('span');
    badge.className = `badge ${claseBadgeEstado(estado)}`;
    badge.textContent = estado || '—';
    return badge;
}

/** Rellena un <select> con opciones y un texto inicial opcional. */
function llenarSelect(select, opciones, textoInicial, valorSeleccionado = null) {
    if (!select) {
        return;
    }

    select.replaceChildren();

    if (textoInicial !== null) {
        const inicial = document.createElement('option');
        inicial.value = '';
        inicial.textContent = textoInicial;
        select.appendChild(inicial);
    }

    opciones.forEach((opcion) => {
        const elemento = document.createElement('option');
        elemento.value = String(opcion.valor);
        elemento.textContent = opcion.texto;
        select.appendChild(elemento);
    });

    if (valorSeleccionado !== null && valorSeleccionado !== undefined) {
        select.value = String(valorSeleccionado);
    }
}
