/**
 * UI Module
 * Manejo de interfaz de usuario y DOM
 */

/**
 * Mostrar alerta/toast
 * @param {string} message - Mensaje a mostrar
 * @param {string} type - Tipo de alerta (success, error, warning, info)
 * @param {number} duration - Duración en ms (default: 3000)
 */
export function showAlert(message, type = 'info', duration = 3000) {
  // Remover alertas previas
  const existingAlert = document.getElementById('custom-alert');
  if (existingAlert) {
    existingAlert.remove();
  }

  // Colores según tipo
  const colors = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    warning: 'bg-yellow-500',
    info: 'bg-blue-500'
  };

  const bgColor = colors[type] || colors.info;

  // Crear alerta
  const alert = document.createElement('div');
  alert.id = 'custom-alert';
  alert.className = `fixed top-4 right-4 ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-fade-in`;
  alert.textContent = message;

  document.body.appendChild(alert);

  // Auto-remover después de duration
  setTimeout(() => {
    alert.classList.add('animate-fade-out');
    setTimeout(() => alert.remove(), 300);
  }, duration);
}

/**
 * Mostrar estado de carga en un botón
 * @param {HTMLElement} button - Botón a modificar
 * @param {boolean} loading - Si está cargando
 * @param {string} loadingText - Texto durante carga (default: "Cargando...")
 */
export function setButtonLoading(button, loading, loadingText = 'Cargando...') {
  if (!button) return;

  if (loading) {
    button.dataset.originalText = button.textContent;
    button.disabled = true;
    button.innerHTML = `
      <svg class="animate-spin h-5 w-5 inline-block mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      ${loadingText}
    `;
  } else {
    button.disabled = false;
    button.textContent = button.dataset.originalText || 'Enviar';
  }
}

/**
 * Mostrar spinner de carga en un elemento
 * @param {HTMLElement} element - Elemento contenedor
 * @param {boolean} show - Mostrar u ocultar
 */
export function showLoading(element, show = true) {
  if (!element) return;

  if (show) {
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner flex items-center justify-center p-8';
    spinner.innerHTML = `
      <svg class="animate-spin h-12 w-12 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    `;
    element.appendChild(spinner);
  } else {
    const spinner = element.querySelector('.loading-spinner');
    if (spinner) spinner.remove();
  }
}

/**
 * Mostrar/ocultar elemento
 * @param {HTMLElement|string} element - Elemento o ID del elemento
 * @param {boolean} show - Mostrar u ocultar
 */
export function toggleElement(element, show) {
  const el = typeof element === 'string' ? document.getElementById(element) : element;
  if (!el) return;

  if (show) {
    el.classList.remove('hidden');
  } else {
    el.classList.add('hidden');
  }
}

/**
 * Limpiar formulario
 * @param {HTMLFormElement|string} form - Formulario o ID del formulario
 */
export function clearForm(form) {
  const formEl = typeof form === 'string' ? document.getElementById(form) : form;
  if (!formEl) return;

  formEl.reset();
  
  // Limpiar errores de validación
  const errorElements = formEl.querySelectorAll('.error-message');
  errorElements.forEach(el => el.remove());

  const inputsWithError = formEl.querySelectorAll('.border-red-500');
  inputsWithError.forEach(input => {
    input.classList.remove('border-red-500');
    input.classList.add('border-gray-300');
  });
}

/**
 * Mostrar errores de validación en formulario
 * @param {HTMLFormElement|string} form - Formulario o ID del formulario
 * @param {Object} errors - Objeto con errores { campo: 'mensaje' }
 */
export function showFormErrors(form, errors) {
  const formEl = typeof form === 'string' ? document.getElementById(form) : form;
  if (!formEl) return;

  // Limpiar errores previos
  const errorElements = formEl.querySelectorAll('.error-message');
  errorElements.forEach(el => el.remove());

  const inputsWithError = formEl.querySelectorAll('.border-red-500');
  inputsWithError.forEach(input => {
    input.classList.remove('border-red-500');
    input.classList.add('border-gray-300');
  });

  // Mostrar nuevos errores
  Object.keys(errors).forEach(fieldName => {
    const input = formEl.querySelector(`[name="${fieldName}"]`);
    if (input) {
      input.classList.add('border-red-500');
      input.classList.remove('border-gray-300');

      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-message text-red-500 text-sm mt-1';
      errorDiv.textContent = errors[fieldName];

      input.parentElement.appendChild(errorDiv);
    }
  });

  // Scroll al primer error
  const firstError = formEl.querySelector('.border-red-500');
  if (firstError) {
    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
    firstError.focus();
  }
}

/**
 * Renderizar información de cliente
 * @param {Object} cliente - Datos del cliente
 * @param {HTMLElement|string} container - Contenedor o ID del contenedor
 */
export function renderClienteInfo(cliente, container) {
  const containerEl = typeof container === 'string' ? document.getElementById(container) : container;
  if (!containerEl) return;

  containerEl.innerHTML = `
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-gray-800">Información del Cliente</h3>
        <span class="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
          ${cliente.es_pep ? 'PEP' : 'Regular'}
        </span>
      </div>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <p class="text-sm text-gray-600">DNI</p>
          <p class="font-semibold text-gray-800">${cliente.dni}</p>
        </div>
        
        <div>
          <p class="text-sm text-gray-600">Nombre Completo</p>
          <p class="font-semibold text-gray-800">${cliente.nombre} ${cliente.apellido}</p>
        </div>
        
        <div>
          <p class="text-sm text-gray-600">Email</p>
          <p class="font-semibold text-gray-800">${cliente.email}</p>
        </div>
        
        <div>
          <p class="text-sm text-gray-600">Teléfono</p>
          <p class="font-semibold text-gray-800">${cliente.telefono}</p>
        </div>
        
        <div class="md:col-span-2">
          <p class="text-sm text-gray-600">Dirección</p>
          <p class="font-semibold text-gray-800">${cliente.direccion}</p>
        </div>
      </div>
    </div>
  `;
}

/**
 * Renderizar lista de préstamos
 * @param {Array} prestamos - Array de préstamos
 * @param {HTMLElement|string} container - Contenedor o ID del contenedor
 */
export function renderPrestamosList(prestamos, container) {
  const containerEl = typeof container === 'string' ? document.getElementById(container) : container;
  if (!containerEl) return;

  if (prestamos.length === 0) {
    containerEl.innerHTML = `
      <div class="text-center py-12">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900">No hay préstamos</h3>
        <p class="mt-1 text-sm text-gray-500">No se encontraron préstamos para este cliente.</p>
      </div>
    `;
    return;
  }

  const prestamosHTML = prestamos.map(prestamo => `
    <div class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
      <div class="flex justify-between items-start mb-4">
        <div>
          <h4 class="text-lg font-semibold text-gray-800">Préstamo #${prestamo.id}</h4>
          <p class="text-sm text-gray-600">${new Date(prestamo.fecha_desembolso).toLocaleDateString('es-PE')}</p>
        </div>
        <span class="px-3 py-1 rounded-full text-sm font-medium ${
          prestamo.estado === 'VIGENTE' 
            ? 'bg-green-100 text-green-800' 
            : 'bg-gray-100 text-gray-800'
        }">
          ${prestamo.estado}
        </span>
      </div>
      
      <div class="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p class="text-sm text-gray-600">Monto</p>
          <p class="text-lg font-bold text-gray-800">S/ ${prestamo.monto.toFixed(2)}</p>
        </div>
        <div>
          <p class="text-sm text-gray-600">TEA</p>
          <p class="text-lg font-bold text-gray-800">${prestamo.tea}%</p>
        </div>
        <div>
          <p class="text-sm text-gray-600">Cuotas</p>
          <p class="text-lg font-bold text-gray-800">${prestamo.num_cuotas}</p>
        </div>
        <div>
          <p class="text-sm text-gray-600">Deuda Total</p>
          <p class="text-lg font-bold text-gray-800">S/ ${prestamo.deuda_total.toFixed(2)}</p>
        </div>
      </div>
      
      <a href="/prestamos/${prestamo.id}" 
         class="block text-center bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600 transition-colors">
        Ver Detalles
      </a>
    </div>
  `).join('');

  containerEl.innerHTML = `
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      ${prestamosHTML}
    </div>
  `;
}

/**
 * Modal de confirmación
 * @param {string} title - Título del modal
 * @param {string} message - Mensaje del modal
 * @param {Function} onConfirm - Callback al confirmar
 * @param {Function} onCancel - Callback al cancelar
 */
export function showConfirmModal(title, message, onConfirm, onCancel = null) {
  const modal = document.createElement('div');
  modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
  modal.innerHTML = `
    <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
      <h3 class="text-lg font-semibold text-gray-800 mb-2">${title}</h3>
      <p class="text-gray-600 mb-6">${message}</p>
      
      <div class="flex justify-end space-x-3">
        <button id="modal-cancel" class="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 transition-colors">
          Cancelar
        </button>
        <button id="modal-confirm" class="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors">
          Confirmar
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  const confirmBtn = modal.querySelector('#modal-confirm');
  const cancelBtn = modal.querySelector('#modal-cancel');

  confirmBtn.addEventListener('click', () => {
    modal.remove();
    if (onConfirm) onConfirm();
  });

  cancelBtn.addEventListener('click', () => {
    modal.remove();
    if (onCancel) onCancel();
  });

  // Cerrar al hacer click fuera del modal
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
      if (onCancel) onCancel();
    }
  });
}

/**
 * Formatear número como moneda
 * @param {number} amount - Monto a formatear
 * @returns {string} - Monto formateado
 */
export function formatCurrency(amount) {
  return new Intl.NumberFormat('es-PE', {
    style: 'currency',
    currency: 'PEN'
  }).format(amount);
}

/**
 * Formatear fecha
 * @param {string|Date} date - Fecha a formatear
 * @returns {string} - Fecha formateada
 */
export function formatDate(date) {
  return new Date(date).toLocaleDateString('es-PE', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
}

export default {
  showAlert,
  setButtonLoading,
  showLoading,
  toggleElement,
  clearForm,
  showFormErrors,
  renderClienteInfo,
  renderPrestamosList,
  showConfirmModal,
  formatCurrency,
  formatDate
};
