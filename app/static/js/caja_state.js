/**
 * Gestión global de estado de cierre de caja
 * Este script mantiene el estado de cierre de caja persistente en localStorage
 * y muestra un banner global cuando la caja está cerrada
 */

// Variables globales
let estadoCajaCerrada = null;
let estadoCajaYaVerificado = false; // Bandera para evitar múltiples verificaciones

/**
 * Crear y mostrar el banner de caja cerrada
 */
function crearBannerCajaCerrada(info = null) {
    // Remover banner anterior si existe
    const bannerExistente = document.getElementById('caja_cerrada_banner_global');
    if (bannerExistente) {
        bannerExistente.remove();
    }

    const banner = document.createElement('div');
    banner.id = 'caja_cerrada_banner_global';
    banner.style.cssText = `
        position: fixed;
        top: 64px;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 12px 20px;
        z-index: 40;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        font-weight: 600;
        font-size: 14px;
    `;

    let mensaje = '⚠️ CAJA CERRADA - No se pueden registrar pagos';
    if (info && info.incidencia) {
        mensaje += ` | Incidencia: ${info.incidencia} (S/ ${parseFloat(info.diferencia).toFixed(2)})`;
    }

    banner.innerHTML = `
        <span>${mensaje}</span>
        <button onclick="abrirCajaDesdeGlobal()" style="
            background: white;
            color: #ef4444;
            border: none;
            padding: 6px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 700;
            font-size: 12px;
            transition: all 0.2s;
        " onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='white'">
            ABRIR CAJA
        </button>
    `;

    document.body.insertBefore(banner, document.body.firstChild);
    
    // Agregar margen al main para que no se oculte bajo el banner
    const main = document.querySelector('main');
    if (main) {
        main.style.marginTop = '50px';
    }
    
    // Si estamos en registro_pago.html, deshabilitar botón
    const btnSubmit = document.getElementById('btn-submit');
    if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.classList.add('opacity-50', 'cursor-not-allowed');
        btnSubmit.title = 'No se pueden registrar pagos cuando la caja está cerrada';
    }
    
    // Si estamos en cuadre.html, mostrar overlay de cierre
    const overlayQuadre = document.getElementById('caja_cerrada_overlay');
    if (overlayQuadre) {
        overlayQuadre.style.display = 'flex';
        // Mostrar texto en el overlay
        const texto = document.getElementById('caja_cerrada_texto');
        if (texto) {
            texto.textContent = 'Caja cerrada';
        }
        // Mostrar detalle si hay incidencia
        const detalle = document.getElementById('caja_cerrada_detalle');
        if (detalle && info && info.incidencia) {
            detalle.textContent = `Incidencia: ${info.incidencia} — Diferencia S/ ${parseFloat(info.diferencia).toFixed(2)}`;
            detalle.style.display = 'block';
        } else if (detalle) {
            detalle.style.display = 'none';
        }
    }
}

/**
 * Remover el banner de caja cerrada
 */
function removerBannerCajaCerrada() {
    const banner = document.getElementById('caja_cerrada_banner_global');
    if (banner) {
        banner.remove();
    }
    
    // Remover margen del main
    const main = document.querySelector('main');
    if (main) {
        main.style.marginTop = '0';
    }
    
    // Si estamos en registro_pago.html, habilitar botón
    const btnSubmit = document.getElementById('btn-submit');
    if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.classList.remove('opacity-50', 'cursor-not-allowed');
        btnSubmit.title = '';
    }
    
    // Si estamos en cuadre.html, ocultar overlay de cierre
    const overlayQuadre = document.getElementById('caja_cerrada_overlay');
    if (overlayQuadre) {
        overlayQuadre.style.display = 'none';
    }
}

/**
 * Guardar estado de cierre en localStorage
 */
function guardarEstadoCajaCerrada(info) {
    localStorage.setItem('caja_cerrada', JSON.stringify({
        cerrada: true,
        fecha: new Date().toISOString().split('T')[0],
        info: info,
        timestamp: Date.now()
    }));
    estadoCajaCerrada = info;
    crearBannerCajaCerrada(info);
}

/**
 * Limpiar estado de cierre en localStorage
 */
function limpiarEstadoCajaCerrada() {
    localStorage.removeItem('caja_cerrada');
    estadoCajaCerrada = null;
    estadoCajaYaVerificado = false; // Resetear bandera para permitir nueva verificación
    removerBannerCajaCerrada();
}

/**
 * Obtener el estado guardado en localStorage
 */
function obtenerEstadoCajaCerrada() {
    const stored = localStorage.getItem('caja_cerrada');
    if (!stored) return null;
    
    try {
        const data = JSON.parse(stored);
        return data;
    } catch (e) {
        return null;
    }
}

/**
 * Verificar y restaurar estado de caja al cargar la página
 */
function verificarYRestaurarEstadoCaja() {
    // Evitar múltiples ejecuciones de esta función
    if (estadoCajaYaVerificado) {
        return;
    }
    estadoCajaYaVerificado = true;
    
    const estado = obtenerEstadoCajaCerrada();
    
    if (estado && estado.cerrada) {
        estadoCajaCerrada = estado.info;
        crearBannerCajaCerrada(estado.info);
    } else {
        estadoCajaCerrada = null;
        removerBannerCajaCerrada();
    }
}

/**
 * Abrir caja desde el banner global
 */
async function abrirCajaDesdeGlobal() {
    const hoy = new Date().toISOString().split('T')[0];
    
    try {
        const response = await fetch('/caja/abrir', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fecha: hoy })
        });
        
        const data = await response.json();
        
        if (data && data.success) {
            limpiarEstadoCajaCerrada();
            alert('✅ Caja reabierta correctamente');
            
            // Recargar página actual para actualizar todo
            window.location.reload();
        } else {
            alert('❌ Error al abrir caja');
        }
    } catch (err) {
        console.error('Error:', err);
        alert('❌ Error al abrir caja');
    }
}

/**
 * Prevenir submit del formulario si caja está cerrada
 */
function protegerFormuarioDePagos() {
    const form = document.getElementById('form-pago');
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        if (estadoCajaCerrada) {
            e.preventDefault();
            alert('❌ No se pueden registrar pagos cuando la caja está cerrada.\n\nUsa el botón "ABRIR CAJA" en el banner rojo.');
        }
    });
}

/**
 * Inicializar: restaurar estado y configurar protecciones
 */
document.addEventListener('DOMContentLoaded', function() {
    verificarYRestaurarEstadoCaja();
    protegerFormuarioDePagos();
});
