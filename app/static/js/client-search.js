// client-search.js - Búsqueda y registro de clientes

// Estado global del cliente actual (compartido con loan-modal.js)
window.currentClient = null;

/**
 * Buscar cliente por DNI
 */
async function searchClient() {
  const dniInput = document.getElementById("dni-search");
  const dni = dniInput.value.trim();

  // Validar DNI
  if (!dni) {
    showAlert("Por favor ingrese un DNI", "error");
    return;
  }

  if (dni.length !== 8 || !/^\d+$/.test(dni)) {
    showAlert("El DNI debe tener 8 dígitos", "error");
    return;
  }

  // Mostrar loading
  const searchButton = document.querySelector(".search-button");
  const originalText = searchButton.textContent;
  searchButton.textContent = "Buscando...";
  searchButton.disabled = true;

  try {
    // Buscar cliente por DNI usando el endpoint correcto
    const response = await fetch(`/api/v1/clientes/dni/${dni}`);

    if (response.status === 404) {
      // Cliente no existe, consultar API de RENIEC
      await consultarYRegistrarCliente(dni);
    } else if (response.ok) {
      const cliente = await response.json();
      // Cliente existe en la BD
      window.currentClient = cliente;
      displayClientInfo(cliente);

      // Verificar si tiene préstamo activo
      if (cliente.tiene_prestamo_activo) {
        showAlert(
          "⚠️ Este cliente ya tiene un préstamo activo. No se puede otorgar otro crédito.",
          "warning"
        );
        // Deshabilitar el formulario de préstamo
        disableLoanForm(true);
      } else {
        showAlert("Cliente encontrado", "success");
        // Habilitar el formulario de préstamo
        disableLoanForm(false);
      }
    } else {
      throw new Error("Error al buscar el cliente");
    }
  } catch (error) {
    console.error("Error:", error);
    showAlert("Error al buscar el cliente: " + error.message, "error");
  } finally {
    searchButton.textContent = originalText;
    searchButton.disabled = false;
  }
}

/**
 * Consultar API de RENIEC (SIN registrar en BD)
 * El cliente se registrará cuando se cree el préstamo
 */
async function consultarYRegistrarCliente(dni) {
  try {
    // Consultar API de DNI
    const consultaResponse = await fetch(
      `/api/v1/clientes/consultar_dni/${dni}`
    );

    if (!consultaResponse.ok) {
      throw new Error("DNI no encontrado en RENIEC");
    }

    const dniData = await consultaResponse.json();

    // Validar si es PEP en el dataset
    let esPep = false;
    try {
      const pepResponse = await fetch(`/api/v1/clientes/test/pep/${dni}`);
      if (pepResponse.ok) {
        const pepData = await pepResponse.json();
        esPep = pepData.es_pep || false;
      }
    } catch (error) {
      console.warn("No se pudo validar PEP:", error);
    }

    // Crear objeto temporal del cliente (NO guardado en BD aún)
    const clienteTemporal = {
      dni: dni,
      nombre_completo: dniData.nombres,
      apellido_paterno: dniData.apellido_paterno,
      apellido_materno: dniData.apellido_materno,
      pep: esPep, // Validado contra el dataset
      _temp: true // Marca para indicar que no está en BD
    };

    // Guardar en variable global
    window.currentClient = clienteTemporal;

    // Mostrar mensaje informativo
    if (esPep) {
      showAlert("⚠️ Cliente encontrado en RENIEC. Este cliente es PEP (Persona Expuesta Políticamente).", "warning");
    } else {
      showAlert("Cliente encontrado en RENIEC. Complete el préstamo para registrar.", "info");
    }

    // Actualizar la interfaz con los datos del cliente
    displayClientInfo(clienteTemporal);
    
    // Habilitar el formulario de préstamo
    disableLoanForm(false);
  } catch (error) {
    console.error("Error:", error);
    showAlert("Error: " + error.message, "error");
  }
}

/**
 * Mostrar información del cliente en la interfaz
 */
function displayClientInfo(cliente) {
  // Actualizar DNI
  const dniElement = document.getElementById("client-dni");
  if (dniElement) {
    dniElement.textContent = cliente.dni;
  }

  // Actualizar nombre completo
  const nameElement = document.getElementById("client-name");
  if (nameElement) {
    const nombreCompleto = `${cliente.nombre_completo || ""} ${
      cliente.apellido_paterno || ""
    } ${cliente.apellido_materno || ""}`.trim();
    nameElement.textContent = nombreCompleto;
  }

  // Mostrar/ocultar aviso PEP
  const pepNotice = document.querySelector(".pep-notice");
  if (pepNotice) {
    pepNotice.style.display = cliente.pep ? "flex" : "none";
  }

  // Mostrar/ocultar aviso de préstamo activo
  const loanNotice = document.getElementById("loan-active-notice");
  const loanDetailsText = document.getElementById("loan-details-text");
  if (loanNotice && cliente.tiene_prestamo_activo) {
    loanNotice.classList.add("show");
    if (loanDetailsText && cliente.prestamo_activo) {
      const fechaOtorgamiento = new Date(
        cliente.prestamo_activo.fecha_otorgamiento
      ).toLocaleDateString("es-PE");
      loanDetailsText.innerHTML = `
        <strong>Préstamo #${cliente.prestamo_activo.id}</strong><br>
        Monto: S/ ${parseFloat(cliente.prestamo_activo.monto).toFixed(2)} | 
        Plazo: ${cliente.prestamo_activo.plazo} cuotas | 
        Fecha: ${fechaOtorgamiento}
      `;
    }
  } else if (loanNotice) {
    loanNotice.classList.remove("show");
  }

  // Actualizar badge de estado
  const statusBadge = document.querySelector(".status-badge");
  if (statusBadge && cliente.tiene_prestamo_activo) {
    statusBadge.textContent = "Préstamo Activo";
    statusBadge.style.background = "#FFF3CD";
    statusBadge.style.color = "#856404";
  } else if (statusBadge) {
    statusBadge.textContent = "Sin Préstamos";
    statusBadge.style.background = "#E8F5E9";
    statusBadge.style.color = "#2E7D32";
  }

  // Mostrar sección de resultados
  const resultsSection = document.querySelector(".results-section");
  if (resultsSection) {
    resultsSection.style.display = "block";
  }
}

/**
 * Deshabilitar/habilitar formulario de préstamo
 */
function disableLoanForm(disable) {
  const montoInput = document.getElementById("monto");
  const cuotasInput = document.getElementById("cuotas");
  const emailInput = document.getElementById("email");
  const saveButton = document.querySelector(".save-button");

  if (montoInput) montoInput.disabled = disable;
  if (cuotasInput) cuotasInput.disabled = disable;
  if (emailInput) emailInput.disabled = disable;
  if (saveButton) {
    saveButton.disabled = disable;
    if (disable) {
      saveButton.style.background = "#ccc";
      saveButton.style.cursor = "not-allowed";
      saveButton.title = "Este cliente ya tiene un préstamo activo";
    } else {
      saveButton.style.background = "";
      saveButton.style.cursor = "";
      saveButton.title = "";
    }
  }
}

/**
 * Modal de cliente registrado exitosamente
 */
function showClientRegisteredModal(cliente) {
  const modalOverlay = document.createElement("div");
  modalOverlay.className = "modal-overlay";
  modalOverlay.id = "client-registered-modal";

  const nombreCompleto = `${cliente.nombre_completo || ""} ${
    cliente.apellido_paterno || ""
  } ${cliente.apellido_materno || ""}`.trim();

  modalOverlay.innerHTML = `
    <div class="modal-content">
      <button class="modal-close" onclick="closeClientModal()">✕</button>
      
      <div class="modal-icon modal-icon--success">
        ✓
      </div>
      
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
          <span class="modal-detail-value">${cliente.pep ? "Sí" : "No"}</span>
        </div>
        
        <div class="modal-detail-row">
          <span class="modal-detail-label">Fecha de Registro</span>
          <span class="modal-detail-value">${new Date().toLocaleDateString(
            "es-PE"
          )}</span>
        </div>
      </div>
      
      <button class="modal-button" onclick="closeClientModal()">
        Continuar
      </button>
    </div>
  `;

  document.body.appendChild(modalOverlay);

  setTimeout(() => {
    modalOverlay.classList.add("active");
  }, 10);

  modalOverlay.addEventListener("click", function (e) {
    if (e.target === modalOverlay) {
      closeClientModal();
    }
  });
}

/**
 * Cerrar modal de cliente registrado
 */
function closeClientModal() {
  const modal = document.getElementById("client-registered-modal");
  if (modal) {
    modal.classList.remove("active");
    setTimeout(() => {
      modal.remove();
    }, 300);
  }
}

// Event listeners
document.addEventListener("DOMContentLoaded", function () {
  // Búsqueda con Enter
  const dniInput = document.getElementById("dni-search");
  if (dniInput) {
    dniInput.addEventListener("keypress", function (e) {
      if (e.key === "Enter") {
        searchClient();
      }
    });
  }

  // Botón de búsqueda
  const searchButton = document.querySelector(".search-button");
  if (searchButton) {
    searchButton.addEventListener("click", searchClient);
  }

  // Ocultar sección de resultados inicialmente
  const resultsSection = document.querySelector(".results-section");
  if (resultsSection) {
    resultsSection.style.display = "none";
  }
});

console.log("client-search.js loaded");
