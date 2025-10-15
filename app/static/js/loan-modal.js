// loan-modal.js - Gestión de préstamos

/**
 * Guardar cambios del préstamo
 */
function saveLoanChanges() {
  console.log('saveLoanChanges called');
  
  // Verificar que hay un cliente seleccionado
  if (!window.currentClient) {
    showAlert('Primero debe buscar y seleccionar un cliente', 'error');
    return;
  }
  
  // Verificar si el cliente ya tiene un préstamo activo
  if (window.currentClient.tiene_prestamo_activo) {
    showAlert('Este cliente ya tiene un préstamo activo. No se puede otorgar otro crédito.', 'error');
    return;
  }
  
  // Obtener los datos del formulario
  const monto = document.getElementById('monto')?.value;
  const cuotas = document.getElementById('cuotas')?.value;
  const email = document.getElementById('email')?.value || '';
  
  console.log('Datos obtenidos:', { monto, cuotas, email });
  
  // Validar campos
  if (!monto || !cuotas) {
    showAlert('Por favor complete todos los campos requeridos (Monto y Cuotas)', 'error');
    return;
  }
  
  if (parseFloat(monto) <= 0) {
    showAlert('El monto debe ser mayor a 0', 'error');
    return;
  }
  
  if (parseInt(cuotas) <= 0) {
    showAlert('El número de cuotas debe ser mayor a 0', 'error');
    return;
  }
  
  // Datos del préstamo
  const loanData = {
    cliente_id: window.currentClient.id,
    monto: parseFloat(monto),
    cuotas: parseInt(cuotas),
    email: email,
    // Información del cliente para mostrar en el modal
    cliente: {
      dni: window.currentClient.dni,
      nombre_completo: `${window.currentClient.nombre_completo || ''} ${window.currentClient.apellido_paterno || ''} ${window.currentClient.apellido_materno || ''}`.trim()
    }
  };
  
  console.log('Enviando datos del préstamo:', loanData);
  
  // Mostrar modal de confirmación
  showLoanSuccessModal(loanData);
  
  // TODO: Implementar guardado en la base de datos
  /*
  fetch('/api/v1/prestamos', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(loanData)
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Error al guardar el préstamo');
    }
    return response.json();
  })
  .then(data => {
    showLoanSuccessModal({
      ...loanData,
      id: data.id
    });
  })
  .catch(error => {
    console.error('Error:', error);
    showAlert('Error al guardar el préstamo: ' + error.message, 'error');
  });
  */
}

/**
 * Mostrar modal de préstamo creado exitosamente
 */
function showLoanSuccessModal(loanData) {
  const modalOverlay = document.createElement('div');
  modalOverlay.className = 'modal-overlay';
  modalOverlay.id = 'loan-success-modal';
  
  modalOverlay.innerHTML = `
    <div class="modal-content">
      <button class="modal-close" onclick="closeLoanModal()">✕</button>
      
      <div class="modal-icon modal-icon--success">
        ✓
      </div>
      
      <h2 class="modal-title">Solicitud de Préstamo Creada</h2>
      
      <p class="modal-message">
        La solicitud de préstamo para ${loanData.cliente.nombre_completo} ha sido creada exitosamente.
      </p>
      
      <div class="modal-details">
        <div class="modal-detail-row">
          <span class="modal-detail-label">Monto del Préstamo</span>
          <span class="modal-detail-value">S/ ${parseFloat(loanData.monto).toFixed(2)}</span>
        </div>
        
        <div class="modal-detail-row">
          <span class="modal-detail-label">Número de cuotas</span>
          <span class="modal-detail-value">${loanData.cuotas} Cuotas</span>
        </div>
        
        <div class="modal-detail-row">
          <span class="modal-detail-label">Cliente</span>
          <span class="modal-detail-value">${loanData.cliente.nombre_completo}</span>
        </div>
        
        <div class="modal-detail-row">
          <span class="modal-detail-label">DNI</span>
          <span class="modal-detail-value">${loanData.cliente.dni}</span>
        </div>
      </div>
      
      <button class="modal-button" onclick="closeLoanModal()">
        Cerrar
      </button>
    </div>
  `;
  
  document.body.appendChild(modalOverlay);
  
  setTimeout(() => {
    modalOverlay.classList.add('active');
  }, 10);
  
  // Cerrar al hacer click fuera del modal
  modalOverlay.addEventListener('click', function(e) {
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
      // Limpiar el formulario después de cerrar
      const loanForm = document.getElementById('loan-form');
      if (loanForm) {
        loanForm.reset();
      }
    }, 300);
  }
}

// Cerrar modal con tecla Escape
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    closeLoanModal();
  }
});

console.log('loan-modal.js loaded');
