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
      const errorData = await consultaResponse.json();
      throw new Error(
        errorData.mensaje || errorData.error || "DNI no encontrado en RENIEC"
      );
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
      nombre_completo:
        dniData.nombre_completo ||
        `${dniData.apellido_paterno} ${dniData.apellido_materno}, ${dniData.nombres}`.trim(),
      apellido_paterno: dniData.apellido_paterno,
      apellido_materno: dniData.apellido_materno,
      nombres: dniData.nombres, // Agregar nombres también
      pep: esPep, // Validado contra el dataset
      _temp: true, // Marca para indicar que no está en BD
    };

    // Guardar en variable global
    window.currentClient = clienteTemporal;

    // Mostrar mensaje informativo
    if (esPep) {
      showAlert(
        "ADVERTENCIA: Cliente encontrado en RENIEC. Este cliente es PEP (Persona Expuesta Politicamente).",
        "warning"
      );
    } else {
      showAlert(
        "EXITO: Cliente encontrado en RENIEC. Complete el prestamo para registrar.",
        "success"
      );
    }

    // Actualizar la interfaz con los datos del cliente
    // Cliente temporal no tiene préstamo activo
    const prestamoDataTemp = { tiene_prestamo_activo: false };
    displayClientInfo(clienteTemporal, prestamoDataTemp);

    // Habilitar el formulario de prestamo
    disableLoanForm(false);
  } catch (error) {
    console.error("Error:", error);
    showAlert(
      "ERROR: " +
        error.message +
        "\n\nEl DNI no esta en RENIEC o el servicio no esta disponible.",
      "error"
    );
  }
}

/**
 * Mostrar información del cliente en la interfaz
 */
function displayClientInfo(
  cliente,
  prestamoData = { tiene_prestamo_activo: false }
) {
  console.log({ cliente, prestamoData });

  const dniElement = document.getElementById("client-dni");
  if (dniElement) {
    dniElement.textContent = cliente.dni;
  }

  const nameElement = document.getElementById("client-name");
  if (nameElement) {
    // Usar nombre_completo si existe, sino construir desde las partes
    const nombreCompleto =
      cliente.nombre_completo ||
      `${cliente.apellido_paterno || ""} ${cliente.apellido_materno || ""}, ${
        cliente.nombres || ""
      }`.trim();
    nameElement.textContent = nombreCompleto;
  }

  const pepNotice = document.querySelector(".pep-notice");
  if (pepNotice) {
    pepNotice.style.display = cliente.pep ? "flex" : "none";
  }

  const loanNotice = document.getElementById("loan-active-notice");
  const loanDetailsText = document.getElementById("loan-details-text");
  if (loanNotice && prestamoData && prestamoData.tiene_prestamo_activo) {
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
  if (statusBadge) {
    if (prestamoData && prestamoData.tiene_prestamo_activo) {
      statusBadge.textContent = "Préstamo Activo";
      statusBadge.style.background = "#FFF3CD";
      statusBadge.style.color = "#856404";
    } else {
      statusBadge.textContent = "Sin Préstamos";
      statusBadge.style.background = "#E8F5E9";
      statusBadge.style.color = "#2E7D32";
    }
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
    cliente.apellido_paterno
  } ${cliente.apellido_materno}`;

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

  // Validaciones de monto
  if (montoInput.value && monto < 0) {
    showAlert("El monto no puede ser negativo", "error");
    montoInput.value = "";
    return;
  }

  if (montoInput.value && monto > 0 && monto < 300) {
    showAlert("El monto mínimo es S/ 300.00", "error");
    montoInput.value = "";
    return;
  }

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

  // Validaciones de cuotas
  if (cuotasInput.value) {
    if (cuotas < 0) {
      showAlert("El número de cuotas no puede ser negativo", "error");
      cuotasInput.value = "";
      cronogramaButton.disabled = true;
      return;
    }

    if (cuotas > 0 && cuotas < 3) {
      showAlert("El número mínimo de cuotas es 3", "error");
      cuotasInput.value = "";
      cronogramaButton.disabled = true;
      return;
    }
  }

  if (monto >= 300 && cuotas >= 3) {
    cronogramaButton.disabled = false;
  } else {
    cronogramaButton.disabled = true;
  }
}

async function verCronogramaPagos() {
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

  // Abrir modal
  const modal = document.getElementById("modalCronograma");
  const modalMonto = document.getElementById("cronograma-monto");
  const modalCuotas = document.getElementById("cronograma-cuotas");
  const tableBody = document.getElementById("cronograma-table-body");

  if (!modal || !tableBody) {
    showAlert("Error: No se encontró el modal de cronograma", "error");
    return;
  }

  modal.style.display = "flex";

  // Actualizar información del modal
  if (modalMonto) modalMonto.textContent = `S/ ${monto.toFixed(2)}`;
  if (modalCuotas) modalCuotas.textContent = `${cuotas} meses`;

  // Mostrar loading
  tableBody.innerHTML = `
    <tr>
      <td colspan="6" class="px-4 py-8 text-center text-gray-500">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-2"></div>
        <p>Generando cronograma...</p>
      </td>
    </tr>
  `;

  try {
    // Calcular cronograma localmente (simulación)
    const teaDecimal = 10 / 100; // Convertir 10% a 0.10
    const tasaMensual = teaDecimal / 12; // TEA convertida a mensual
    const cuotaMensual =
      (monto * (tasaMensual * Math.pow(1 + tasaMensual, cuotas))) /
      (Math.pow(1 + tasaMensual, cuotas) - 1);

    let saldo = monto;
    let html = "";
    const fechaInicio = new Date();

    for (let i = 1; i <= cuotas; i++) {
      const interes = saldo * tasaMensual;
      const capital = cuotaMensual - interes;
      saldo = Math.max(0, saldo - capital);

      // Calcular fecha de vencimiento
      const fechaVencimiento = new Date(fechaInicio);
      fechaVencimiento.setMonth(fechaVencimiento.getMonth() + i);

      // Estilo alternado para filas
      const rowClass = i % 2 === 0 ? "bg-gray-50" : "bg-white";

      html += `
        <tr class="${rowClass} hover:bg-blue-50 transition-colors">
          <td class="px-4 py-3 text-center">
            <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-700 font-bold text-sm">
              ${i}
            </span>
          </td>
          <td class="px-4 py-3 text-gray-700">
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
              </svg>
              <span class="font-medium">${fechaVencimiento.toLocaleDateString(
                "es-PE",
                {
                  day: "2-digit",
                  month: "short",
                  year: "numeric",
                }
              )}</span>
            </div>
          </td>
          <td class="px-4 py-3 text-right">
            <span class="text-gray-900 font-bold text-base">S/ ${cuotaMensual.toFixed(
              2
            )}</span>
          </td>
          <td class="px-4 py-3 text-right">
            <span class="text-blue-600 font-semibold">S/ ${capital.toFixed(
              2
            )}</span>
          </td>
          <td class="px-4 py-3 text-right">
            <span class="text-amber-600 font-semibold">S/ ${interes.toFixed(
              2
            )}</span>
          </td>
          <td class="px-4 py-3 text-right">
            <span class="inline-block px-3 py-1 rounded-full text-sm font-bold ${
              saldo === 0
                ? "bg-green-100 text-green-700"
                : "bg-gray-100 text-gray-700"
            }">
              S/ ${saldo.toFixed(2)}
            </span>
          </td>
        </tr>
      `;
    }

    tableBody.innerHTML = html;
  } catch (error) {
    console.error("Error al generar cronograma:", error);
    tableBody.innerHTML = `
      <tr>
        <td colspan="6" class="px-4 py-8 text-center text-red-600">
          <p class="font-semibold">Error al generar el cronograma</p>
          <p class="text-sm text-gray-600 mt-2">${error.message}</p>
        </td>
      </tr>
    `;
  }
}

/**
 * Cerrar modal de cronograma
 */
function cerrarModalCronograma() {
  const modal = document.getElementById("modalCronograma");
  if (modal) {
    modal.style.display = "none";
  }
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

  // Validaciones finales antes de enviar
  const montoNumerico = parseFloat(monto);
  const cuotasNumerico = parseInt(cuotas);

  if (montoNumerico < 300) {
    showAlert("El monto mínimo es S/ 300.00", "error");
    return;
  }

  if (montoNumerico < 0) {
    showAlert("El monto no puede ser negativo", "error");
    return;
  }

  if (cuotasNumerico < 3) {
    showAlert("El número mínimo de cuotas es 3", "error");
    return;
  }

  if (cuotasNumerico < 0) {
    showAlert("El número de cuotas no puede ser negativo", "error");
    return;
  }

  const UIT = 5350;
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

  interes_tea = 10; // TEA en porcentaje (10%)

  try {
    // Obtener fecha actual en formato YYYY-MM-DD (zona horaria local)
    const hoy = new Date();
    const fechaLocal = `${hoy.getFullYear()}-${String(
      hoy.getMonth() + 1
    ).padStart(2, "0")}-${String(hoy.getDate()).padStart(2, "0")}`;

    const prestamoData = {
      dni: window.currentClient.dni,
      correo_electronico: email,
      monto: parseFloat(monto),
      interes_tea: interes_tea,
      plazo: parseInt(cuotas),
      f_otorgamiento: fechaLocal,
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
      console.log("Response data:", data);
      showAlert("EXITO: Prestamo creado exitosamente", "success");

      // Resetear formulario
      document.getElementById("loan-form").reset();
      document.getElementById("declaracion-jurada-check").checked = false;
      document.getElementById("validation-message").classList.add("hidden");

      window.currentClient.tiene_prestamo_activo = true;

      displayClientInfo(window.currentClient);
      disableLoanForm(true);

      const prestamo = data.prestamo || {};
      const cliente = data.cliente || {};
      const cronograma = data.cronograma || [];

      setTimeout(() => {
        alert(
          `EXITO: Prestamo registrado exitosamente\n\n` +
            `ID: ${prestamo.prestamo_id}\n` +
            `Cliente: ${
              cliente.nombre_completo || window.currentClient.nombre_completo
            }\n` +
            `Monto: S/ ${
              prestamo.monto_total ? prestamo.monto_total.toFixed(2) : "N/A"
            }\n` +
            `Plazo: ${prestamo.plazo} meses\n` +
            `Interes TEA: ${prestamo.interes_tea}%\n` +
            `${
              prestamo.requiere_declaracion
                ? "NOTA: Requiere Declaracion Jurada"
                : ""
            }\n\n` +
            `Cronograma de ${cronograma.length} cuotas generado.`
        );
      }, 500);
    } else {
      const error = await response.json();

      // Mensajes detallados segun el tipo de error
      if (error.estado) {
        // Error de prestamo activo
        alert(
          `${error.error}\n\n` +
            `${error.mensaje}\n\n` +
            `Prestamo ID: ${error.prestamo_id}\n` +
            `Monto: S/ ${error.monto?.toFixed(2) || "N/A"}\n` +
            `Estado: ${error.estado}\n\n` +
            `${error.detalle || ""}`
        );
      } else {
        // Otros errores
        showAlert(
          `ERROR: ${
            error.error || error.mensaje || "Error al crear el prestamo"
          }`,
          "error"
        );
      }
    }
  } catch (error) {
    console.error("Error:", error);
    showAlert("ERROR: Error al crear el prestamo: " + error.message, "error");
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
