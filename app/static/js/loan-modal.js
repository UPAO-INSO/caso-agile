// loan-modal.js - Gestión de préstamos

const DEFAULT_INTERES_TEA = window.DEFAULT_LOAN_TEA || 30;
const loanCurrencyFormatter = new Intl.NumberFormat('es-PE', {
  style: 'currency',
  currency: 'PEN',
  minimumFractionDigits: 2,
});

function setLoanFormState(disable, reason) {
  if (typeof disableLoanForm === 'function') {
    disableLoanForm(disable, reason);
  }
}

/**
 * Guardar cambios del préstamo
 */
async function saveLoanChanges() {
  if (!window.currentClient) {
    showAlert('Primero debe buscar y seleccionar un cliente', 'error');
    return;
  }

  if (window.currentClient.tiene_prestamo_activo) {
    showAlert('Este cliente ya tiene un préstamo activo. No se puede otorgar otro crédito.', 'error');
    setLoanFormState(true, 'Este cliente ya tiene un préstamo activo');
    return;
  }

  const monto = document.getElementById('monto')?.value;
  const cuotas = document.getElementById('cuotas')?.value;
  const email = document.getElementById('email')?.value || '';
  const teaInput = document.getElementById('interes-tea');
  const fechaInput = document.getElementById('fecha-otorgamiento');

  if (!monto || !cuotas) {
    showAlert('Por favor complete todos los campos requeridos (Monto y Cuotas)', 'error');
    return;
  }

  const montoValue = parseFloat(monto);
  const cuotasValue = parseInt(cuotas, 10);

  if (!Number.isFinite(montoValue) || montoValue <= 0) {
    showAlert('El monto debe ser mayor a 0', 'error');
    return;
  }

  if (!Number.isFinite(cuotasValue) || cuotasValue <= 0) {
    showAlert('El número de cuotas debe ser mayor a 0', 'error');
    return;
  }

  let interesTea = teaInput && teaInput.value ? parseFloat(teaInput.value) : DEFAULT_INTERES_TEA;
  if (!Number.isFinite(interesTea) || interesTea <= 0) {
    interesTea = DEFAULT_INTERES_TEA;
  }

  const fechaOtorgamiento = fechaInput && fechaInput.value
    ? fechaInput.value
    : new Date().toISOString().split('T')[0];

  const payload = {
    dni: window.currentClient.dni,
    monto: montoValue,
    interes_tea: interesTea,
    plazo: cuotasValue,
    f_otorgamiento: fechaOtorgamiento,
  };

  const saveButton = document.querySelector('.save-button');
  const originalButtonText = saveButton ? saveButton.textContent : '';

  if (saveButton) {
    saveButton.disabled = true;
    saveButton.textContent = 'Guardando...';
  }

  try {
    const response = await fetch('/api/v1/prestamos/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    const responseData = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(responseData.message || responseData.error || 'Error al guardar el préstamo');
    }

    const prestamo = responseData.prestamo || {};
    const montoPrestamo = parseFloat(prestamo.monto);

    const loanData = {
      prestamo_id: prestamo.id,
      monto: Number.isFinite(montoPrestamo) ? montoPrestamo : montoValue,
      cuotas: prestamo.plazo || cuotasValue,
      interes_tea: prestamo.interes_tea || interesTea,
      fecha_otorgamiento: prestamo.fecha_otorgamiento || fechaOtorgamiento,
      email,
      cliente: {
        dni: window.currentClient.dni,
        nombre_completo: `${window.currentClient.nombre_completo || ''} ${window.currentClient.apellido_paterno || ''} ${window.currentClient.apellido_materno || ''}`.replace(/\s+/g, ' ').trim(),
      },
    };

    window.currentClient.tiene_prestamo_activo = true;
    window.currentClient.prestamo_activo = {
      id: prestamo.id,
      monto: loanData.monto,
      plazo: loanData.cuotas,
      interes_tea: loanData.interes_tea,
      fecha_otorgamiento: loanData.fecha_otorgamiento,
      estado: prestamo.estado,
    };

    if (typeof window.displayClientInfo === 'function') {
      window.displayClientInfo(window.currentClient);
    }

  setLoanFormState(true, 'Este cliente ya tiene un préstamo activo');
    showAlert('Préstamo registrado exitosamente.', 'success');
    showLoanSuccessModal(loanData);
  } catch (error) {
    console.error('Error:', error);
    showAlert('Error al guardar el préstamo: ' + error.message, 'error');
  } finally {
    if (saveButton) {
      saveButton.disabled = false;
      saveButton.textContent = originalButtonText || 'Guardar Cambios';
    }
  }
}

/**
 * Mostrar modal de préstamo creado exitosamente
 */
function showLoanSuccessModal(loanData) {
  const modalOverlay = document.createElement('div');
  modalOverlay.className = 'modal-overlay';
  modalOverlay.id = 'loan-success-modal';

  const detailRows = [
    loanData.prestamo_id
      ? `
        <div class="modal-detail-row">
          <span class="modal-detail-label">ID del Préstamo</span>
          <span class="modal-detail-value">${loanData.prestamo_id}</span>
        </div>
      `
      : '',
    `
      <div class="modal-detail-row">
        <span class="modal-detail-label">Monto del Préstamo</span>
        <span class="modal-detail-value">${formatLoanCurrency(loanData.monto)}</span>
      </div>
    `,
    `
      <div class="modal-detail-row">
        <span class="modal-detail-label">Número de cuotas</span>
        <span class="modal-detail-value">${loanData.cuotas} cuotas</span>
      </div>
    `,
    loanData.interes_tea
      ? `
        <div class="modal-detail-row">
          <span class="modal-detail-label">Tasa TEA</span>
          <span class="modal-detail-value">${parseFloat(loanData.interes_tea).toFixed(2)} %</span>
        </div>
      `
      : '',
    loanData.fecha_otorgamiento
      ? `
        <div class="modal-detail-row">
          <span class="modal-detail-label">Fecha de otorgamiento</span>
          <span class="modal-detail-value">${formatLoanDate(loanData.fecha_otorgamiento)}</span>
        </div>
      `
      : '',
    `
      <div class="modal-detail-row">
        <span class="modal-detail-label">Cliente</span>
        <span class="modal-detail-value">${loanData.cliente.nombre_completo || loanData.cliente.dni}</span>
      </div>
    `,
    `
      <div class="modal-detail-row">
        <span class="modal-detail-label">DNI</span>
        <span class="modal-detail-value">${loanData.cliente.dni}</span>
      </div>
    `,
    loanData.email
      ? `
        <div class="modal-detail-row">
          <span class="modal-detail-label">Correo registrado</span>
          <span class="modal-detail-value">${loanData.email}</span>
        </div>
      `
      : '',
  ].join('');

  modalOverlay.innerHTML = `
    <div class="modal-content">
      <button class="modal-close" onclick="closeLoanModal()">✕</button>
      <div class="modal-icon modal-icon--success">✓</div>
      <h2 class="modal-title">Solicitud de Préstamo Creada</h2>
      <p class="modal-message">
        La solicitud de préstamo para ${loanData.cliente.nombre_completo || loanData.cliente.dni} ha sido creada exitosamente.
      </p>
      <div class="modal-details">
        ${detailRows}
      </div>
      <button class="modal-button" onclick="closeLoanModal()">Cerrar</button>
    </div>
  `;

  document.body.appendChild(modalOverlay);

  setTimeout(() => {
    modalOverlay.classList.add('active');
  }, 10);

  modalOverlay.addEventListener('click', function (e) {
    if (e.target === modalOverlay) {
      closeLoanModal();
    }
  });
}

/**
 * Cerrar modal de préstamo
 */
function closeLoanModal() {
  const modal = document.getElementById('loan-success-modal');
  if (modal) {
    modal.classList.remove('active');
    setTimeout(() => {
      modal.remove();
      const loanForm = document.getElementById('loan-form');
      if (loanForm) {
        loanForm.reset();
      }
      if (typeof window.resetClientSearchState === 'function') {
        window.resetClientSearchState();
      } else {
        window.currentClient = null;
      }
      setLoanFormState(true, 'Debe buscar y seleccionar un cliente');
    }, 300);
  }
}

function formatLoanCurrency(value) {
  const numericValue = typeof value === 'string' ? Number(value) : value;
  if (!Number.isFinite(numericValue)) {
    return loanCurrencyFormatter.format(0);
  }
  return loanCurrencyFormatter.format(numericValue);
}

function formatLoanDate(value) {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }
  return date.toLocaleDateString('es-PE');
}

// Cerrar modal con tecla Escape
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    closeLoanModal();
  }
});

console.log('loan-modal.js loaded');
