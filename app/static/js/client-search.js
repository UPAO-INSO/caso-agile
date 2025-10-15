// client-search.js - Búsqueda y registro de clientes

// Estado global del cliente actual (compartido con loan-modal.js)
window.currentClient = null;
window.DEFAULT_LOAN_TEA = 30;

let pendingClientSelection = null;
const currencyFormatter = new Intl.NumberFormat('es-PE', {
  style: 'currency',
  currency: 'PEN',
  minimumFractionDigits: 2,
});

/**
 * Buscar cliente por DNI
 */
async function searchClient() {
  const dniInput = document.getElementById('dni-search');
  if (!dniInput) {
    showAlert('No se encontró el campo de búsqueda de DNI.', 'error');
    return;
  }

  const dni = dniInput.value.trim();

  if (!dni) {
    showAlert('Por favor ingrese un DNI', 'error');
    return;
  }

  if (dni.length !== 8 || !/^\d+$/.test(dni)) {
    showAlert('El DNI debe tener 8 dígitos', 'error');
    return;
  }

  const searchButton = document.querySelector('.search-button');
  const originalText = searchButton ? searchButton.textContent : '';

  if (searchButton) {
    searchButton.textContent = 'Buscando...';
    searchButton.disabled = true;
  }

  try {
    const response = await fetch(`/api/v1/clientes/dni/${dni}`);

    if (response.status === 404) {
      await consultarYRegistrarCliente(dni);
      return;
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || 'Error al buscar el cliente');
    }

    const cliente = await response.json();
    promptClientSelection(cliente, { source: 'database' });
  } catch (error) {
    console.error('Error:', error);
    showAlert('Error al buscar el cliente: ' + error.message, 'error');
  } finally {
    if (searchButton) {
      searchButton.textContent = originalText || 'Buscar';
      searchButton.disabled = false;
    }
  }
}

/**
 * Consultar API de RENIEC (SIN registrar en BD)
 * El cliente se registrará cuando se cree el préstamo
 */
async function consultarYRegistrarCliente(dni) {
  try {
    const consultaResponse = await fetch(`/api/v1/clientes/consultar_dni/${dni}`);

    if (!consultaResponse.ok) {
      const errorData = await consultaResponse.json().catch(() => ({}));
      throw new Error(errorData.error || 'DNI no encontrado en RENIEC');
    }

    const dniData = await consultaResponse.json();

    let esPep = false;
    try {
      const pepResponse = await fetch(`/api/v1/clientes/consultar_pep/${dni}`);
      if (pepResponse.ok) {
        const pepData = await pepResponse.json();
        esPep = pepData.es_pep || false;
      }
    } catch (error) {
      console.warn('No se pudo validar PEP:', error);
    }

    const clienteTemporal = {
      id: null,
      cliente_id: null,
      dni,
      nombre_completo: dniData.nombres || '',
      apellido_paterno: dniData.apellido_paterno || '',
      apellido_materno: dniData.apellido_materno || '',
      pep: esPep,
      tiene_prestamo_activo: false,
      prestamo_activo: null,
      _temp: true,
    };

    promptClientSelection(clienteTemporal, { source: 'external' });
  } catch (error) {
    console.error('Error:', error);
    showAlert('Error: ' + error.message, 'error');
  }
}

function promptClientSelection(cliente, meta = {}) {
  pendingClientSelection = { cliente, meta };
  closeClientSelectionModal();

  const modalOverlay = document.createElement('div');
  modalOverlay.className = 'modal-overlay';
  modalOverlay.id = 'client-selection-modal';

  const fullName = buildFullName(cliente);

  modalOverlay.innerHTML = `
    <div class="modal-content">
      <button class="modal-close" type="button">✕</button>
      <h2 class="modal-title">Cliente encontrado</h2>
      <p class="modal-message">
        Se encontró al cliente <strong>${fullName}</strong> con DNI <strong>${cliente.dni}</strong>.
        ¿Desea continuar con este registro?
      </p>
      <div class="modal-details">
        <div class="modal-detail-row">
          <span class="modal-detail-label">Nombres</span>
          <span class="modal-detail-value">${cliente.nombre_completo || '—'}</span>
        </div>
        <div class="modal-detail-row">
          <span class="modal-detail-label">Apellido paterno</span>
          <span class="modal-detail-value">${cliente.apellido_paterno || '—'}</span>
        </div>
        <div class="modal-detail-row">
          <span class="modal-detail-label">Apellido materno</span>
          <span class="modal-detail-value">${cliente.apellido_materno || '—'}</span>
        </div>
        <div class="modal-detail-row">
          <span class="modal-detail-label">Estado PEP</span>
          <span class="modal-detail-value">${cliente.pep ? 'Sí' : 'No'}</span>
        </div>
      </div>
      <div class="modal-actions" style="display:flex; gap:12px; margin-top:12px; flex-direction:column;">
        <button class="modal-button" data-action="confirm" type="button">Registrar</button>
        <button class="modal-button" data-action="cancel" type="button" style="background:#e5e7eb;color:#1f2937;">
          Intentar de nuevo
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(modalOverlay);

  requestAnimationFrame(() => {
    modalOverlay.classList.add('active');
  });

  const confirmButton = modalOverlay.querySelector('[data-action="confirm"]');
  const cancelButton = modalOverlay.querySelector('[data-action="cancel"]');
  const closeButton = modalOverlay.querySelector('.modal-close');

  confirmButton?.addEventListener('click', confirmClientSelection);
  cancelButton?.addEventListener('click', cancelClientSelection);
  closeButton?.addEventListener('click', cancelClientSelection);

  modalOverlay.addEventListener('click', (event) => {
    if (event.target === modalOverlay) {
      cancelClientSelection();
    }
  });
}

function confirmClientSelection() {
  if (!pendingClientSelection) {
    closeClientSelectionModal();
    return;
  }

  const { cliente, meta } = pendingClientSelection;
  pendingClientSelection = null;

  window.currentClient = {
    ...cliente,
    tiene_prestamo_activo: Boolean(cliente.tiene_prestamo_activo),
  };

  displayClientInfo(window.currentClient);

  if (window.currentClient.tiene_prestamo_activo) {
    disableLoanForm(true, 'Este cliente ya tiene un préstamo activo');
    showAlert('⚠️ Este cliente ya tiene un préstamo activo. No se puede otorgar otro crédito.', 'warning');
  } else {
    disableLoanForm(false);
    if (meta.source === 'external') {
      showAlert('Cliente encontrado en RENIEC. Complete el préstamo para registrar.', 'info');
    } else {
      showAlert('Cliente listo para registrar préstamo.', 'success');
    }
  }

  if (window.currentClient.pep) {
    showAlert('⚠️ Este cliente es una Persona Expuesta Políticamente (PEP).', 'warning');
  }

  closeClientSelectionModal();
}

function cancelClientSelection(showMessage = true) {
  const hadPending = Boolean(pendingClientSelection);
  pendingClientSelection = null;
  closeClientSelectionModal();
  if (hadPending && showMessage) {
    showAlert('Búsqueda cancelada. Puede ingresar un nuevo DNI.', 'info');
  }
}

function closeClientSelectionModal() {
  const modal = document.getElementById('client-selection-modal');
  if (modal) {
    modal.classList.remove('active');
    setTimeout(() => {
      modal.remove();
    }, 200);
  }
}

/**
 * Mostrar información del cliente en la interfaz
 */
function displayClientInfo(cliente) {
  const dniElement = document.getElementById('client-dni');
  if (dniElement) {
    dniElement.textContent = cliente.dni || '—';
  }

  const nameElement = document.getElementById('client-name');
  if (nameElement) {
    nameElement.textContent = buildFullName(cliente);
  }

  const pepNotice = document.querySelector('.pep-notice');
  if (pepNotice) {
    if (cliente.pep) {
      pepNotice.style.display = 'flex';
      pepNotice.classList.remove('hidden');
    } else {
      pepNotice.style.display = 'none';
      pepNotice.classList.add('hidden');
    }
  }

  const loanNotice = document.getElementById('loan-active-notice');
  const loanDetailsText = document.getElementById('loan-details-text');
  const loan = cliente.prestamo_activo;

  if (loanNotice) {
    if (cliente.tiene_prestamo_activo && loan) {
      loanNotice.classList.remove('hidden');
      if (loanDetailsText) {
        loanDetailsText.innerHTML = `
          <strong>Préstamo #${loan.id}</strong><br>
          Monto: ${formatCurrency(loan.monto)} |
          Plazo: ${loan.plazo} cuotas |
          Fecha: ${formatDate(loan.fecha_otorgamiento)}
        `;
      }
    } else {
      loanNotice.classList.add('hidden');
      if (loanDetailsText) {
        loanDetailsText.textContent = '';
      }
    }
  }

  const statusBadge = document.querySelector('.status-badge');
  if (statusBadge) {
    if (cliente.tiene_prestamo_activo && loan) {
      statusBadge.textContent = 'Préstamo Activo';
      statusBadge.classList.remove('bg-green-100', 'text-green-700');
      statusBadge.classList.add('bg-amber-100', 'text-amber-700');
    } else {
      statusBadge.textContent = 'Sin Préstamos';
      statusBadge.classList.remove('bg-amber-100', 'text-amber-700');
      statusBadge.classList.add('bg-green-100', 'text-green-700');
    }
  }

  updateLoanSummary(cliente);

  const resultsSection = document.querySelector('.results-section');
  if (resultsSection) {
    resultsSection.style.display = 'block';
  }
}

function updateLoanSummary(cliente) {
  const loan = cliente.prestamo_activo || null;

  const amountElement = document.getElementById('loan-amount');
  if (amountElement) {
    amountElement.textContent = loan ? formatCurrency(loan.monto) : 'S/ 0.00';
  }

  const installmentsElement = document.getElementById('loan-installments');
  if (installmentsElement) {
    installmentsElement.textContent = loan ? `${loan.plazo} cuotas` : '0 cuotas';
  }

  const teaElement = document.getElementById('loan-tea');
  if (teaElement) {
    teaElement.textContent = loan ? `${parseFloat(loan.interes_tea).toFixed(2)} %` : '—';
  }

  const dateElement = document.getElementById('loan-date');
  if (dateElement) {
    dateElement.textContent = loan ? formatDate(loan.fecha_otorgamiento) : '—';
  }

  const emailElement = document.getElementById('loan-email');
  if (emailElement) {
    emailElement.textContent = cliente.email || '—';
  }

  updateActionLinks(cliente);
}

function updateActionLinks(cliente) {
  const loan = cliente.prestamo_activo;

  const scheduleLink = document.getElementById('view-schedule');
  if (scheduleLink) {
    if (loan && loan.id) {
      const baseHref = scheduleLink.dataset.baseHref || scheduleLink.href;
      scheduleLink.href = `${baseHref}?prestamo_id=${loan.id}`;
      scheduleLink.classList.remove('pointer-events-none', 'opacity-60');
    } else {
      scheduleLink.href = scheduleLink.dataset.defaultHref || scheduleLink.href;
      scheduleLink.classList.add('pointer-events-none', 'opacity-60');
    }
  }

  const historyLink = document.getElementById('view-history');
  if (historyLink) {
    if (loan && loan.id) {
      historyLink.classList.remove('pointer-events-none', 'opacity-60');
    } else {
      historyLink.classList.add('pointer-events-none', 'opacity-60');
    }
  }
}

/**
 * Deshabilitar/habilitar formulario de préstamo
 */
function disableLoanForm(disable, reason = '') {
  const montoInput = document.getElementById('monto');
  const cuotasInput = document.getElementById('cuotas');
  const emailInput = document.getElementById('email');
  const saveButton = document.querySelector('.save-button');

  if (montoInput) montoInput.disabled = disable;
  if (cuotasInput) cuotasInput.disabled = disable;
  if (emailInput) emailInput.disabled = disable;
  if (saveButton) {
    saveButton.disabled = disable;
    if (disable) {
      saveButton.style.background = '#ccc';
      saveButton.style.cursor = 'not-allowed';
      saveButton.title = reason || 'Debe buscar y seleccionar un cliente';
    } else {
      saveButton.style.background = '';
      saveButton.style.cursor = '';
      saveButton.title = '';
    }
  }
}

function resetClientSearchState() {
  const dniInput = document.getElementById('dni-search');
  if (dniInput) {
    dniInput.value = '';
  }

  window.currentClient = null;
  pendingClientSelection = null;

  const resultsSection = document.querySelector('.results-section');
  if (resultsSection) {
    resultsSection.style.display = 'none';
  }

  const statusBadge = document.querySelector('.status-badge');
  if (statusBadge) {
    statusBadge.textContent = 'Sin Préstamos';
    statusBadge.classList.remove('bg-amber-100', 'text-amber-700');
    statusBadge.classList.add('bg-green-100', 'text-green-700');
  }

  const dniElement = document.getElementById('client-dni');
  if (dniElement) dniElement.textContent = '—';

  const nameElement = document.getElementById('client-name');
  if (nameElement) nameElement.textContent = '—';

  const pepNotice = document.querySelector('.pep-notice');
  if (pepNotice) {
    pepNotice.style.display = 'none';
    pepNotice.classList.add('hidden');
  }

  const loanNotice = document.getElementById('loan-active-notice');
  if (loanNotice) {
    loanNotice.classList.add('hidden');
  }

  const loanDetailsText = document.getElementById('loan-details-text');
  if (loanDetailsText) loanDetailsText.textContent = '';

  const amountElement = document.getElementById('loan-amount');
  if (amountElement) amountElement.textContent = 'S/ 0.00';

  const installmentsElement = document.getElementById('loan-installments');
  if (installmentsElement) installmentsElement.textContent = '0 cuotas';

  const teaElement = document.getElementById('loan-tea');
  if (teaElement) teaElement.textContent = '—';

  const dateElement = document.getElementById('loan-date');
  if (dateElement) dateElement.textContent = '—';

  const emailElement = document.getElementById('loan-email');
  if (emailElement) emailElement.textContent = '—';

  updateActionLinks({ prestamo_activo: null });
  disableLoanForm(true, 'Debe buscar y seleccionar un cliente');
}

function buildFullName(cliente) {
  const nombre = cliente.nombre_completo || '';
  const apellidoPaterno = cliente.apellido_paterno || '';
  const apellidoMaterno = cliente.apellido_materno || '';
  return `${nombre} ${apellidoPaterno} ${apellidoMaterno}`.replace(/\s+/g, ' ').trim() || '—';
}

function formatCurrency(value) {
  const numericValue = typeof value === 'string' ? Number(value) : value;
  if (!numericValue || Number.isNaN(numericValue)) {
    return 'S/ 0.00';
  }
  return currencyFormatter.format(numericValue);
}

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }
  return date.toLocaleDateString('es-PE');
}

/**
 * Modal de cliente registrado exitosamente (mantener compatibilidad)
 */
function showClientRegisteredModal(cliente) {
  const modalOverlay = document.createElement('div');
  modalOverlay.className = 'modal-overlay';
  modalOverlay.id = 'client-registered-modal';

  const nombreCompleto = buildFullName(cliente);

  modalOverlay.innerHTML = `
    <div class="modal-content">
      <button class="modal-close" onclick="closeClientModal()">✕</button>
      <div class="modal-icon modal-icon--success">✓</div>
      <h2 class="modal-title">Cliente Registrado Exitosamente</h2>
      <p class="modal-message">
        El cliente ha sido registrado en el sistema correctamente.
      </p>
      <div class="modal-details">
        <div class="modal-detail-row">
          <span class="modal-detail-label">DNI</span>
          <span class="modal-detail-value">${cliente.dni}</span>
        </div>
        <div class="modal-detail-row">
          <span class="modal-detail-label">Nombre Completo</span>
          <span class="modal-detail-value">${nombreCompleto}</span>
        </div>
        <div class="modal-detail-row">
          <span class="modal-detail-label">Estado PEP</span>
          <span class="modal-detail-value">${cliente.pep ? 'Sí' : 'No'}</span>
        </div>
        <div class="modal-detail-row">
          <span class="modal-detail-label">Fecha de Registro</span>
          <span class="modal-detail-value">${new Date().toLocaleDateString('es-PE')}</span>
        </div>
      </div>
      <button class="modal-button" onclick="closeClientModal()">Continuar</button>
    </div>
  `;

  document.body.appendChild(modalOverlay);

  setTimeout(() => {
    modalOverlay.classList.add('active');
  }, 10);

  modalOverlay.addEventListener('click', function (e) {
    if (e.target === modalOverlay) {
      closeClientModal();
    }
  });
}

function closeClientModal() {
  const modal = document.getElementById('client-registered-modal');
  if (modal) {
    modal.classList.remove('active');
    setTimeout(() => {
      modal.remove();
    }, 300);
  }
}

document.addEventListener('DOMContentLoaded', function () {
  const dniInput = document.getElementById('dni-search');
  if (dniInput) {
    dniInput.addEventListener('keypress', function (e) {
      if (e.key === 'Enter') {
        searchClient();
      }
    });
  }

  const searchButton = document.querySelector('.search-button');
  if (searchButton) {
    searchButton.addEventListener('click', searchClient);
  }

  const resultsSection = document.querySelector('.results-section');
  if (resultsSection) {
    resultsSection.style.display = 'none';
  }

  disableLoanForm(true, 'Debe buscar y seleccionar un cliente');
});

document.addEventListener('keydown', function (event) {
  if (event.key === 'Escape') {
    cancelClientSelection(false);
  }
});

window.resetClientSearchState = resetClientSearchState;
window.displayClientInfo = displayClientInfo;

console.log('client-search.js loaded');
