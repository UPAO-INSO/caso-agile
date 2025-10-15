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
    cerrarModalCronograma();
  }
});

/**
 * Ver cronograma de pagos
 */
async function verCronogramaPagos() {
  const monto = document.getElementById('monto')?.value;
  const cuotas = document.getElementById('cuotas')?.value;
  
  if (!monto || !cuotas) {
    alert('Por favor ingrese el monto y numero de cuotas primero');
    return;
  }
  
  if (parseFloat(monto) <= 0) {
    alert('El monto debe ser mayor a 0');
    return;
  }
  
  if (parseInt(cuotas) <= 0) {
    alert('El numero de cuotas debe ser mayor a 0');
    return;
  }
  
  // Calcular cronograma (metodo frances - cuota fija)
  const montoTotal = parseFloat(monto);
  const numCuotas = parseInt(cuotas);
  const tasaAnual = 0.20; // 20% TEA
  const tasaMensual = Math.pow(1 + tasaAnual, 1/12) - 1;
  
  // Calcular cuota fija
  const cuotaFija = montoTotal * (tasaMensual * Math.pow(1 + tasaMensual, numCuotas)) / (Math.pow(1 + tasaMensual, numCuotas) - 1);
  
  let saldo = montoTotal;
  const cronograma = [];
  const fechaBase = new Date();
  
  for (let i = 1; i <= numCuotas; i++) {
    const interes = saldo * tasaMensual;
    const capital = cuotaFija - interes;
    saldo -= capital;
    
    const fechaVencimiento = new Date(fechaBase);
    fechaVencimiento.setMonth(fechaBase.getMonth() + i);
    
    cronograma.push({
      numero_cuota: i,
      fecha_vencimiento: fechaVencimiento.toLocaleDateString('es-PE'),
      monto_cuota: cuotaFija,
      monto_capital: capital,
      monto_interes: interes,
      saldo_capital: Math.max(0, saldo)
    });
  }
  
  // Llenar modal con datos
  document.getElementById('cronograma-monto').textContent = `S/ ${montoTotal.toFixed(2)}`;
  document.getElementById('cronograma-cuotas').textContent = `${numCuotas} meses`;
  
  const tbody = document.getElementById('cronograma-table-body');
  tbody.innerHTML = '';
  
  cronograma.forEach(cuota => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-gray-50';
    tr.innerHTML = `
      <td class="px-4 py-3 text-gray-900 font-medium">${cuota.numero_cuota}</td>
      <td class="px-4 py-3 text-gray-600">${cuota.fecha_vencimiento}</td>
      <td class="px-4 py-3 text-right font-semibold text-gray-900">S/ ${cuota.monto_cuota.toFixed(2)}</td>
      <td class="px-4 py-3 text-right text-gray-600">S/ ${cuota.monto_capital.toFixed(2)}</td>
      <td class="px-4 py-3 text-right text-gray-600">S/ ${cuota.monto_interes.toFixed(2)}</td>
      <td class="px-4 py-3 text-right text-blue-600 font-medium">S/ ${cuota.saldo_capital.toFixed(2)}</td>
    `;
    tbody.appendChild(tr);
  });
  
  // Mostrar modal
  const modal = document.getElementById('modalCronograma');
  modal.style.display = 'flex';
  setTimeout(() => {
    modal.classList.remove('hidden');
  }, 10);
}

/**
 * Cerrar modal de cronograma
 */
function cerrarModalCronograma() {
  const modal = document.getElementById('modalCronograma');
  if (modal) {
    modal.classList.add('hidden');
    setTimeout(() => {
      modal.style.display = 'none';
    }, 300);
  }
}

// Cerrar modal al hacer clic fuera
document.addEventListener('click', function(e) {
  const modal = document.getElementById('modalCronograma');
  if (modal && e.target === modal) {
    cerrarModalCronograma();
  }
});

console.log('loan-modal.js loaded');
