/**
 * Client Search (Modernizado)
 * Búsqueda y gestión de clientes usando módulos ES6
 */

import { ClientesAPI, PrestamosAPI } from "./modules/api.js";
import {
  validarDNI,
  validarFormularioCliente,
  validarFormularioPrestamo,
} from "./modules/validation.js";
import {
  showAlert,
  setButtonLoading,
  showLoading,
  toggleElement,
  clearForm,
  showFormErrors,
  renderClienteInfo,
  showConfirmModal,
} from "./modules/ui.js";
import {
  setCurrentClient,
  getCurrentClient,
  setLoading,
  isLoading,
  reset,
} from "./modules/state.js";

/**
 * Inicializar la aplicación
 */
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  loadInitialData();
});

/**
 * Inicializar event listeners
 */
function initEventListeners() {
  // Búsqueda de cliente por DNI
  const searchButton = document.getElementById("search-client-btn");
  if (searchButton) {
    searchButton.addEventListener("click", handleSearchClient);
  }

  // Enter en el input de DNI
  const dniInput = document.getElementById("dni-search");
  if (dniInput) {
    dniInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        handleSearchClient();
      }
    });
  }

  // Formulario de préstamo
  const loanForm = document.getElementById("loan-form");
  if (loanForm) {
    loanForm.addEventListener("submit", handleCreateLoan);
  }

  // Formulario de registro de cliente
  const clientForm = document.getElementById("client-form");
  if (clientForm) {
    clientForm.addEventListener("submit", handleCreateClient);
  }

  // Botón de limpiar búsqueda
  const clearButton = document.getElementById("clear-search-btn");
  if (clearButton) {
    clearButton.addEventListener("click", handleClearSearch);
  }
}

/**
 * Cargar datos iniciales
 */
async function loadInitialData() {
  // Si hay un cliente en la URL (query param), cargarlo
  const urlParams = new URLSearchParams(window.location.search);
  const clienteDni = urlParams.get("dni");

  if (clienteDni) {
    const dniInput = document.getElementById("dni-search");
    if (dniInput) {
      dniInput.value = clienteDni;
      await handleSearchClient();
    }
  }
}

/**
 * Manejar búsqueda de cliente
 */
async function handleSearchClient() {
  const dniInput = document.getElementById("dni-search");
  const searchButton = document.getElementById("search-client-btn");

  if (!dniInput || !searchButton) return;

  const dni = dniInput.value.trim();

  // Validar DNI
  const validation = validarDNI(dni);
  if (!validation.valid) {
    showAlert(validation.message, "error");
    dniInput.focus();
    return;
  }

  // Mostrar estado de carga
  setButtonLoading(searchButton, true, "Buscando...");
  setLoading(true);

  try {
    // 1. Intentar buscar en BD
    let cliente = null;
    let existeEnBD = false;

    try {
      const response = await ClientesAPI.buscarPorDNI(dni);
      cliente = response.cliente || response;
      existeEnBD = true;
    } catch (error) {
      // Cliente no existe en BD, intentar consultar RENIEC
      console.log("Cliente no encontrado en BD, consultando RENIEC...");
    }

    // 2. Si no existe en BD, consultar RENIEC
    if (!existeEnBD) {
      cliente = await consultarRENIEC(dni);
      cliente._temp = true; // Marcar como temporal
    }

    // 3. Verificar préstamo activo si existe en BD
    if (existeEnBD) {
      try {
        const prestamoData = await ClientesAPI.verificarPrestamoActivo(
          cliente.id
        );

        if (prestamoData.tiene_prestamo_activo) {
          showAlert(
            "Este cliente ya tiene un préstamo activo. No se puede otorgar otro crédito.",
            "warning"
          );
          disableLoanForm(true);
        } else {
          showAlert("Cliente encontrado", "success");
          disableLoanForm(false);
        }

        cliente.tiene_prestamo_activo = prestamoData.tiene_prestamo_activo;
        cliente.prestamo_activo = prestamoData.prestamo;
      } catch (error) {
        console.warn("No se pudo verificar préstamo activo:", error);
        disableLoanForm(false);
      }
    }

    // 4. Guardar cliente en estado
    setCurrentClient(cliente);

    // 5. Mostrar información del cliente
    displayClientInfo(cliente);

    // 6. Mostrar sección de préstamo
    toggleElement("loan-section", true);
  } catch (error) {
    console.error("Error al buscar cliente:", error);
    showAlert(`Error al buscar el cliente: ${error.message}`, "error");
    reset();
    toggleElement("loan-section", false);
  } finally {
    setButtonLoading(searchButton, false);
    setLoading(false);
  }
}

/**
 * Consultar DNI en RENIEC
 */
async function consultarRENIEC(dni) {
  try {
    // Consultar API de DNI
    const dniData = await ClientesAPI.consultarDNI(dni);

    // Validar si es PEP
    let esPep = false;
    try {
      const pepData = await ClientesAPI.validarPEP(dni);
      esPep = pepData.es_pep || false;
    } catch (error) {
      console.warn("No se pudo validar PEP:", error);
    }

    // Crear objeto temporal del cliente
    const cliente = {
      dni: dni,
      nombre_completo:
        dniData.nombre_completo ||
        `${dniData.apellido_paterno} ${dniData.apellido_materno}, ${dniData.nombres}`.trim(),
      apellido_paterno: dniData.apellido_paterno,
      apellido_materno: dniData.apellido_materno,
      nombres: dniData.nombres,
      pep: esPep,
      tiene_prestamo_activo: false,
      _temp: true, // Marca para indicar que no está en BD
    };

    // Mostrar mensaje apropiado
    if (esPep) {
      showAlert(
        "ADVERTENCIA: Cliente encontrado en RENIEC. Este cliente es PEP (Persona Expuesta Políticamente).",
        "warning"
      );
    } else {
      showAlert(
        "ÉXITO: Cliente encontrado en RENIEC. Complete el préstamo para registrar.",
        "success"
      );
    }

    return cliente;
  } catch (error) {
    throw new Error(
      `El DNI no está en RENIEC o el servicio no está disponible: ${error.message}`
    );
  }
}

/**
 * Mostrar información del cliente
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
    const nombreCompleto =
      cliente.nombre_completo ||
      `${cliente.apellido_paterno || ""} ${cliente.apellido_materno || ""}, ${
        cliente.nombres || ""
      }`.trim();
    nameElement.textContent = nombreCompleto;
  }

  // Mostrar/ocultar aviso PEP
  const pepNotice = document.querySelector(".pep-notice");
  if (pepNotice) {
    pepNotice.style.display = cliente.pep ? "flex" : "none";
  }

  // Mostrar/ocultar aviso de préstamo activo
  const loanNotice = document.getElementById("loan-active-notice");
  if (loanNotice && cliente.tiene_prestamo_activo && cliente.prestamo_activo) {
    loanNotice.classList.add("show");

    const loanDetailsText = document.getElementById("loan-details-text");
    if (loanDetailsText) {
      const fechaOtorgamiento = new Date(
        cliente.prestamo_activo.f_otorgamiento
      ).toLocaleDateString("es-PE");

      loanDetailsText.innerHTML = `
        <strong>Préstamo Activo:</strong><br>
        Monto: S/ ${cliente.prestamo_activo.n_monto_prestamo.toFixed(2)}<br>
        Fecha: ${fechaOtorgamiento}<br>
        Cuotas: ${cliente.prestamo_activo.n_cuotas}
      `;
    }
  } else if (loanNotice) {
    loanNotice.classList.remove("show");
  }

  // Mostrar sección de información del cliente
  toggleElement("client-info", true);
}

/**
 * Habilitar/deshabilitar formulario de préstamo
 */
function disableLoanForm(disable) {
  const loanForm = document.getElementById("loan-form");
  if (!loanForm) return;

  const inputs = loanForm.querySelectorAll(
    'input, select, button[type="submit"]'
  );
  inputs.forEach((input) => {
    input.disabled = disable;
  });

  if (disable) {
    loanForm.classList.add("opacity-50", "pointer-events-none");
  } else {
    loanForm.classList.remove("opacity-50", "pointer-events-none");
  }
}

/**
 * Manejar creación de préstamo
 */
async function handleCreateLoan(e) {
  e.preventDefault();

  const form = e.target;
  const submitButton = form.querySelector('button[type="submit"]');

  // Obtener cliente actual
  const cliente = getCurrentClient();
  if (!cliente) {
    showAlert("Debe buscar un cliente primero", "error");
    return;
  }

  // Obtener datos del formulario
  const formData = {
    monto: form.monto.value,
    tea: form.tea.value,
    cuotas: form.cuotas.value,
    fecha_desembolso: form.fecha_desembolso.value,
  };

  // Validar formulario
  const validation = validarFormularioPrestamo(formData);
  if (!validation.valid) {
    showFormErrors(form, validation.errors);
    showAlert("Por favor corrija los errores en el formulario", "error");
    return;
  }

  // Mostrar estado de carga
  setButtonLoading(submitButton, true, "Registrando préstamo...");

  try {
    // Si el cliente es temporal, registrarlo primero
    let clienteId = cliente.id;

    if (cliente._temp) {
      // Aquí deberías recopilar más datos del cliente
      // Por ahora, simulamos con datos mínimos
      const clienteData = {
        dni: cliente.dni,
        nombre: cliente.nombres,
        apellido:
          `${cliente.apellido_paterno} ${cliente.apellido_materno}`.trim(),
        email: form.cliente_email?.value || `${cliente.dni}@temp.com`,
        telefono: form.cliente_telefono?.value || "000000000",
        direccion: form.cliente_direccion?.value || "Sin dirección",
        pep: cliente.pep,
      };

      const nuevoCliente = await ClientesAPI.crear(clienteData);
      clienteId = nuevoCliente.id;

      // Actualizar cliente en estado
      setCurrentClient(nuevoCliente);
    }

    // Registrar préstamo
    const prestamoData = {
      cliente_id: clienteId,
      ...formData,
    };

    const prestamo = await PrestamosAPI.registrar(prestamoData);

    showAlert("Préstamo registrado exitosamente", "success");

    // Limpiar formulario y resetear
    clearForm(form);
    setTimeout(() => {
      window.location.href = `/prestamos/${prestamo.id}`;
    }, 1500);
  } catch (error) {
    console.error("Error al crear préstamo:", error);
    showAlert(`Error al registrar el préstamo: ${error.message}`, "error");
  } finally {
    setButtonLoading(submitButton, false);
  }
}

/**
 * Manejar creación de cliente
 */
async function handleCreateClient(e) {
  e.preventDefault();

  const form = e.target;
  const submitButton = form.querySelector('button[type="submit"]');

  // Obtener datos del formulario
  const formData = {
    dni: form.dni.value,
    nombre: form.nombre.value,
    apellido: form.apellido.value,
    email: form.email.value,
    telefono: form.telefono.value,
    direccion: form.direccion.value,
  };

  // Validar formulario
  const validation = validarFormularioCliente(formData);
  if (!validation.valid) {
    showFormErrors(form, validation.errors);
    showAlert("Por favor corrija los errores en el formulario", "error");
    return;
  }

  // Mostrar estado de carga
  setButtonLoading(submitButton, true, "Registrando cliente...");

  try {
    const cliente = await ClientesAPI.crear(formData);

    showAlert("Cliente registrado exitosamente", "success");

    // Limpiar formulario
    clearForm(form);

    // Redirigir o actualizar vista
    setTimeout(() => {
      window.location.href = `/clientes/${cliente.id}`;
    }, 1500);
  } catch (error) {
    console.error("Error al crear cliente:", error);
    showAlert(`Error al registrar el cliente: ${error.message}`, "error");
  } finally {
    setButtonLoading(submitButton, false);
  }
}

/**
 * Manejar limpiar búsqueda
 */
function handleClearSearch() {
  // Limpiar input
  const dniInput = document.getElementById("dni-search");
  if (dniInput) {
    dniInput.value = "";
    dniInput.focus();
  }

  // Resetear estado
  reset();

  // Ocultar secciones
  toggleElement("client-info", false);
  toggleElement("loan-section", false);

  showAlert("Búsqueda limpiada", "info");
}

// Exportar funciones principales para uso global
window.ClientSearch = {
  handleSearchClient,
  handleClearSearch,
};
