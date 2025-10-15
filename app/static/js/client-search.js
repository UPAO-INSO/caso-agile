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
      await consultarYRegistrarCliente(dni);
    } else if (response.ok) {
      const cliente = await response.json();
      window.currentClient = cliente;

      try {
        const prestamoResponse = await fetch(
          `/api/v1/clientes/verificar_prestamo/${cliente.cliente_id}`
        );

        if (prestamoResponse.ok) {
          const prestamoData = await prestamoResponse.json();

          displayClientInfo(cliente, prestamoData);

          if (prestamoData.tiene_prestamo_activo) {
            showAlert(
              "Este cliente ya tiene un préstamo activo. No se puede otorgar otro crédito.",
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
          showAlert("Cliente encontrado", "success");
          disableLoanForm(false);
        }
      } catch (error) {
        console.warn("No se pudo verificar préstamo activo:", error);
        showAlert("Cliente encontrado", "success");
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
      _temp: true, // Marca para indicar que no está en BD
    };

    // Guardar en variable global
    window.currentClient = clienteTemporal;

    // Mostrar mensaje informativo
    if (esPep) {
      showAlert(
        "Cliente encontrado en RENIEC. Este cliente es PEP (Persona Expuesta Políticamente).",
        "warning"
      );
    } else {
      showAlert(
        "Cliente encontrado en RENIEC. Complete el préstamo para registrar.",
        "info"
      );
    }

    // Actualizar la interfaz con los datos del cliente
    displayClientInfo(clienteTemporal, prestamoData);

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
function displayClientInfo(cliente, prestamoData) {
  console.log({ prestamoData });

  const dniElement = document.getElementById("client-dni");
  if (dniElement) {
    dniElement.textContent = cliente.dni;
  }

  const nameElement = document.getElementById("client-name");
  if (nameElement) {
    const nombreCompleto = `${cliente.nombre_completo || ""} ${
      cliente.apellido_paterno || ""
    } ${cliente.apellido_materno || ""}`.trim();
    nameElement.textContent = nombreCompleto;
  }

  const pepNotice = document.querySelector(".pep-notice");
  if (pepNotice) {
    pepNotice.style.display = cliente.pep ? "flex" : "none";
  }

  const loanNotice = document.getElementById("loan-active-notice");
  const loanDetailsText = document.getElementById("loan-details-text");
  if (loanNotice && prestamoData.tiene_prestamo_activo) {
    loanNotice.classList.add("show");
    if (loanDetailsText && prestamoData.tiene_prestamo_activo) {
      const fechaOtorgamiento = new Date(
        prestamoData.prestamo.f_otorgamiento
      ).toLocaleDateString("es-PE");
      loanDetailsText.innerHTML = `
        <strong>Préstamo #${prestamoData.prestamo.prestamo_id}</strong><br>
        Monto: S/ ${parseFloat(prestamoData.prestamo.monto_total).toFixed(2)} | 
        Plazo: ${prestamoData.prestamo.plazo} cuotas | 
        Fecha: ${fechaOtorgamiento}
      `;
    }
  } else if (loanNotice) {
    loanNotice.classList.remove("show");
  }

  const statusBadge = document.querySelector(".status-badge");
  if (statusBadge && prestamoData.tiene_prestamo_activo) {
    statusBadge.textContent = "Préstamo Activo";
    statusBadge.style.background = "#FFF3CD";
    statusBadge.style.color = "#856404";
  } else if (statusBadge) {
    statusBadge.textContent = "Sin Préstamos";
    statusBadge.style.background = "#E8F5E9";
    statusBadge.style.color = "#2E7D32";
  }

  const resultsSection = document.querySelector(".results-section");
  if (resultsSection) {
    resultsSection.classList.remove("hidden");
    resultsSection.style.display = "block";
  }

  validarMonto();
}

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

/**
 * Validar monto del préstamo (simulación de validación SBS)
 */
function validarMonto() {
  const montoInput = document.getElementById("monto");
  const validationMessage = document.getElementById("validation-message");
  const uitWarning = document.getElementById("uit-warning");
  const declaracionContainer = document.getElementById(
    "declaracion-jurada-container"
  );

  if (!montoInput) return;

  const monto = parseFloat(montoInput.value);
  const UIT = 5350; // 1 UIT en soles (2025)

  // Verificar si el cliente es PEP
  const esPep = window.currentClient && window.currentClient.pep;

  if (monto > 0) {
    if (monto <= UIT) {
      // Monto menor o igual a 1 UIT
      if (validationMessage) validationMessage.classList.remove("hidden");
      if (uitWarning) uitWarning.classList.add("hidden");

      // Mostrar declaración jurada solo si es PEP
      if (declaracionContainer) {
        if (esPep) {
          declaracionContainer.classList.remove("hidden");
        } else {
          declaracionContainer.classList.add("hidden");
        }
      }
    } else {
      // Monto mayor a 1 UIT
      if (validationMessage) validationMessage.classList.add("hidden");
      if (uitWarning) uitWarning.classList.remove("hidden");

      // Mostrar declaración jurada (obligatorio)
      if (declaracionContainer) {
        declaracionContainer.classList.remove("hidden");
      }
    }

    // Actualizar estado del botón
    actualizarEstadoBoton();
  } else {
    // Sin monto
    if (validationMessage) validationMessage.classList.add("hidden");
    if (uitWarning) uitWarning.classList.add("hidden");

    // Mostrar declaración solo si es PEP
    if (declaracionContainer && esPep) {
      declaracionContainer.classList.remove("hidden");
    } else if (declaracionContainer) {
      declaracionContainer.classList.add("hidden");
    }

    actualizarEstadoBoton();
  }

  // Validar botón de cronograma
  validarCronogramaButton();
}

/**
 * Actualizar estado del botón de crear préstamo
 */
function actualizarEstadoBoton() {
  const submitButton = document.querySelector(".save-button");
  const checkbox = document.getElementById("declaracion-jurada-check");
  const declaracionContainer = document.getElementById(
    "declaracion-jurada-container"
  );

  if (!submitButton) return;

  // Si la declaración jurada está visible, el checkbox debe estar marcado
  const declaracionVisible =
    declaracionContainer && !declaracionContainer.classList.contains("hidden");

  if (declaracionVisible) {
    submitButton.disabled = !(checkbox && checkbox.checked);
  } else {
    submitButton.disabled = false;
  }
}

function validarCronogramaButton() {
  const cronogramaButton = document.getElementById("cronograma-button");
  const montoInput = document.getElementById("monto");
  const cuotasInput = document.getElementById("cuotas");

  if (!cronogramaButton) return;

  const monto = parseFloat(montoInput?.value || 0);
  const cuotas = parseInt(cuotasInput?.value || 0);

  if (monto > 0 && cuotas > 0) {
    cronogramaButton.disabled = false;
  } else {
    cronogramaButton.disabled = true;
  }
}

function verCronogramaPagos() {
  const montoInput = document.getElementById("monto");
  const cuotasInput = document.getElementById("cuotas");

  const monto = parseFloat(montoInput?.value || 0);
  const cuotas = parseInt(cuotasInput?.value || 0);

  if (!monto || !cuotas) {
    showAlert("Ingrese monto y número de cuotas", "error");
    return;
  }

  if (!window.currentClient) {
    showAlert("No hay cliente seleccionado", "error");
    return;
  }

  showAlert("Generando cronograma de pagos...", "info");

  setTimeout(() => {
    alert(`Cronograma para:\nMonto: S/ ${monto.toFixed(2)}\nCuotas: ${cuotas}`);
  }, 500);
}

function imprimirDeclaracionJurada() {
  if (!window.currentClient) {
    showAlert("No hay cliente seleccionado", "error");
    return;
  }

  showAlert("Generando Declaración Jurada para imprimir...", "info");

  setTimeout(() => {
    window.print();
  }, 500);
}

async function crearNuevoPrestamo(event) {
  event.preventDefault();

  if (!window.currentClient) {
    showAlert("No hay cliente seleccionado", "error");
    return;
  }

  const monto = document.getElementById("monto").value;
  const cuotas = document.getElementById("cuotas").value;
  const email = document.getElementById("email").value;

  if (!monto || !cuotas || !email) {
    showAlert("Complete todos los campos requeridos", "error");
    return;
  }

  const UIT = 5350;
  const montoNumerico = parseFloat(monto);
  const esPep = window.currentClient.pep;
  const declaracionContainer = document.getElementById(
    "declaracion-jurada-container"
  );
  const checkbox = document.getElementById("declaracion-jurada-check");

  const requiereDeclaracion = esPep || montoNumerico > UIT;

  if (requiereDeclaracion) {
    if (!checkbox || !checkbox.checked) {
      showAlert("Debe aceptar la Declaración Jurada", "error");
      return;
    }
  }

  const saveButton = document.querySelector(".save-button");
  const originalText = saveButton.innerHTML;
  saveButton.innerHTML =
    '<svg class="animate-spin w-5 h-5 mr-2 inline" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Creando...';
  saveButton.disabled = true;

  interes_tea = 0.1;

  try {
    const today = new Date();
    const fechaOtorgamiento = today.toISOString().split("T")[0]; // "2025-10-15"

    const prestamoData = {
      dni: window.currentClient.dni,
      monto: parseFloat(monto),
      plazo: parseInt(cuotas),
      interes_tea: interes_tea,
      f_otorgamiento: fechaOtorgamiento,
    };

    const response = await fetch("/api/v1/prestamos/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(prestamoData),
    });

    if (response.ok) {
      const data = await response.json();
      showAlert("Préstamo creado exitosamente", "success");

      document.getElementById("loan-form").reset();
      document.getElementById("declaracion-jurada-check").checked = false;
      document.getElementById("validation-message").classList.add("hidden");

      window.currentClient.tiene_prestamo_activo = true;
      window.currentClient.prestamo_activo = data;

      displayClientInfo(window.currentClient);
      disableLoanForm(true);

      setTimeout(() => {
        alert(
          `Préstamo #${data.id} creado exitosamente\nMonto: S/ ${data.monto}\nCuotas: ${data.plazo}`
        );
      }, 500);
    } else {
      const error = await response.json();
      showAlert(error.error || "Error al crear el préstamo", "error");
    }
  } catch (error) {
    console.error("Error:", error);
    showAlert("Error al crear el préstamo: " + error.message, "error");
  } finally {
    saveButton.innerHTML = originalText;
    saveButton.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", function () {
  const dniInput = document.getElementById("dni-search");
  if (dniInput) {
    dniInput.addEventListener("keypress", function (e) {
      if (e.key === "Enter") {
        searchClient();
      }
    });
  }

  const searchButton = document.querySelector(".search-button");
  if (searchButton) {
    searchButton.addEventListener("click", searchClient);
  }

  const resultsSection = document.querySelector(".results-section");
  if (resultsSection) {
    resultsSection.classList.add("hidden");
    resultsSection.style.display = "none";
  }

  const montoInput = document.getElementById("monto");
  if (montoInput) {
    montoInput.addEventListener("input", validarMonto);
  }

  const cuotasInput = document.getElementById("cuotas");
  if (cuotasInput) {
    cuotasInput.addEventListener("input", validarCronogramaButton);
  }

  const checkbox = document.getElementById("declaracion-jurada-check");

  if (checkbox) {
    checkbox.addEventListener("change", function () {
      actualizarEstadoBoton();
    });
  }
});

console.log("client-search.js loaded");
