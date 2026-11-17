/* Autenticación, restauración de sesión y cierre de sesión. */

let usuarioSesion = null;

/** Devuelve el usuario autenticado en memoria (o null). */
function obtenerUsuarioActual() {
    return usuarioSesion;
}

/** Decodifica el payload de un JWT sin validar la firma. */
function decodificarPayloadJWT(token) {
    try {
        const partes = String(token).split('.');
        if (partes.length !== 3) {
            return null;
        }

        const base64 = partes[1].replace(/-/g, '+').replace(/_/g, '/');
        const relleno = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
        const binario = atob(relleno);
        const bytes = Uint8Array.from(binario, (caracter) => caracter.charCodeAt(0));

        return JSON.parse(new TextDecoder().decode(bytes));
    } catch (error) {
        return null;
    }
}

/** Comprueba localmente la expiración del token. */
function tokenExpirado(token) {
    const payload = decodificarPayloadJWT(token);
    if (!payload || typeof payload.exp !== 'number') {
        return false;
    }

    return payload.exp * 1000 <= Date.now();
}

/** Muestra la pantalla de login y limpia el estado en memoria. */
function mostrarLogin(mensaje = '', tipo = 'info') {
    usuarioSesion = null;
    document.getElementById('main-app').classList.add('hidden');
    document.getElementById('login-screen').classList.remove('hidden');
    mostrarMensaje('login-error', mensaje, tipo);

    const campo = document.getElementById('login-correo');
    if (campo) {
        campo.focus();
    }
}

/** Muestra la aplicación y arranca la interfaz según el rol. */
function mostrarAplicacion(usuario) {
    usuarioSesion = usuario;
    document.getElementById('login-screen').classList.add('hidden');
    document.getElementById('main-app').classList.remove('hidden');
    document.getElementById('user-info').textContent = `${usuario.nombre} (${usuario.rol})`;
    ocultarMensaje('login-error');
    iniciarAplicacion(usuario);
}

/** Restaura la sesión guardada y la valida contra el backend. */
async function restaurarSesion() {
    const token = obtenerToken();
    const usuario = obtenerUsuarioGuardado();

    if (!token || !usuario) {
        mostrarLogin();
        return;
    }

    if (tokenExpirado(token)) {
        limpiarSesion();
        mostrarLogin('Su sesión ha expirado. Vuelva a iniciar sesión.', 'error');
        return;
    }

    try {
        await fetchAPI('/panel/metricas');
        mostrarAplicacion(usuario);
    } catch (error) {
        if (error.codigo === 401) {
            return;
        }
        mostrarLogin(
            error.message || 'No se pudo validar la sesión. Intente de nuevo.',
            'error'
        );
    }
}

/* -------------------------------------------------------------------------
 * Eventos
 * ---------------------------------------------------------------------- */

document.getElementById('form-login').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    ocultarMensaje('login-error');

    const identificador = valorCampo('login-correo').trim();
    const contrasena = valorCampo('login-password');

    if (!identificador || !contrasena) {
        mostrarMensaje(
            'login-error',
            'Ingrese su correo o matrícula y su contraseña.',
            'error'
        );
        return;
    }

    const boton = evento.target.querySelector('button[type="submit"]');
    if (boton) {
        boton.disabled = true;
    }

    try {
        const respuesta = await fetchAPI('/login', {
            method: 'POST',
            body: JSON.stringify({ correo: identificador, contrasena }),
            sinSesion: true
        });

        guardarSesion(respuesta.token, respuesta.usuario);
        evento.target.reset();
        mostrarAplicacion(respuesta.usuario);
    } catch (error) {
        mostrarMensaje(
            'login-error',
            error.message || 'No se pudo iniciar sesión.',
            'error'
        );
    } finally {
        if (boton) {
            boton.disabled = false;
        }
    }
});

document.getElementById('btn-logout').addEventListener('click', () => {
    limpiarSesion();
    mostrarLogin('Sesión cerrada correctamente.', 'exito');
});

window.addEventListener('sesion-expirada', (evento) => {
    mostrarLogin(
        evento.detail || 'La sesión ha expirado. Vuelva a iniciar sesión.',
        'error'
    );
});

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', restaurarSesion);
} else {
    restaurarSesion();
}
