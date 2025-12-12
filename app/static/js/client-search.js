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
      // Cliente no existe en DB, consultar RENIEC
      await consultarYRegistrarCliente(dni);
    } else if (response.ok) {
      // Cliente existe en DB
      const cliente = await response.json();
      window.currentClient = cliente;

      // El endpoint ya devuelve tiene_prestamo_activo y prestamo_activo
      displayClientInfo(cliente, {
        tiene_prestamo_activo: cliente.tiene_prestamo_activo,
        prestamo: cliente.prestamo_activo,
      });

      if (cliente.tiene_prestamo_activo) {
        showAlert(
          "Este cliente ya tiene un préstamo activo. No se puede otorgar otro crédito.",
          "warning"
        );
        disableLoanForm(true);
      } else {
        showAlert("Cliente encontrado en base de datos", "success");
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

  const emailElement = document.getElementById("email");
  if (emailElement && cliente.correo_electronico) {
    emailElement.textContent = cliente.correo_electronico;
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

  if (
    loanNotice &&
    prestamoData &&
    prestamoData.tiene_prestamo_activo &&
    prestamoData.prestamo
  ) {
    loanNotice.classList.remove("hidden");
    loanNotice.style.display = "block";

    if (loanDetailsText) {
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
    loanNotice.classList.add("hidden");
    loanNotice.style.display = "none";
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

  // Solo validar si el campo no está vacío Y el usuario no está escribiendo
  // No validar mientras está escribiendo (permite escribir números grandes)
  if (montoInput.value === "" || isNaN(monto)) {
    // Si está vacío, ocultar mensajes y actualizar botón
    if (validationMessage) validationMessage.classList.add("hidden");
    if (uitWarning) uitWarning.classList.add("hidden");
    if (declaracionContainer) {
      const esPep = window.currentClient && window.currentClient.pep;
      if (esPep) {
        declaracionContainer.classList.remove("hidden");
      } else {
        declaracionContainer.classList.add("hidden");
      }
    }
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

/**
 * Crear nuevo préstamo
 */
async function crearNuevoPrestamo(event) {
  event.preventDefault();
  if (!window.currentClient) {
    showAlert("No hay cliente seleccionado", "error");
    return;
  }

  const monto = document.getElementById("monto").value;
  const cuotas = document.getElementById("cuotas").value;
  const email = document.getElementById("email").value;
  const interes_tea = document.getElementById("interes_tea").value;

  if (!monto || !cuotas || !email || !interes_tea) {
    showAlert("Complete todos los campos requeridos", "error");
    return;
  }

  // Validaciones finales antes de enviar
  const montoNumerico = parseFloat(monto);
  const cuotasNumerico = parseInt(cuotas);
  const teaNumerico = parseFloat(interes_tea);

  if (montoNumerico < 0) {
    showAlert("El monto no puede ser negativo", "error");
    return;
  }

  if (cuotasNumerico < 2) {
    showAlert("El número mínimo de cuotas es 3", "error");
    return;
  }

  if (cuotasNumerico < 0) {
    showAlert("El número de cuotas no puede ser negativo", "error");
    return;
  }

  if (teaNumerico <= 0) {
    showAlert("La tasa de interés debe ser mayor a 0%", "error");
    return;
  }

  if (teaNumerico > 100) {
    showAlert("La tasa de interés no puede ser mayor a 100%", "error");
    return;
  }

  const UIT = 5350;
  const esPep = window.currentClient.pep;
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

  try {
    // Tomar la fecha seleccionada por el usuario en el input
    // Leer el valor actual del input de fecha justo antes de enviar
    let fechaOtorgamiento = "";
    const fOtorgamientoInput = document.getElementById("f_otorgamiento");
    if (fOtorgamientoInput) {
      fechaOtorgamiento = fOtorgamientoInput.value;
    }
    if (!fechaOtorgamiento) {
      // Si el usuario no selecciona fecha, usar la fecha actual
      const hoy = new Date();
      fechaOtorgamiento = `${hoy.getFullYear()}-${String(
        hoy.getMonth() + 1
      ).padStart(2, "0")}-${String(hoy.getDate()).padStart(2, "0")}`;
    }

    const prestamoData = {
      dni: window.currentClient.dni,
      correo_electronico: email,
      monto: parseFloat(monto),
      interes_tea: teaNumerico, // Usar el TEA ingresado por el usuario
      plazo: parseInt(cuotas),
      f_otorgamiento: fechaOtorgamiento,
    };

    const response = await fetch("/api/v1/prestamos", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(prestamoData),
    });

    if (response.ok) {
      const data = await response.json();
      console.log("Response data:", data);

      // Verificar que realmente fue exitoso
      if (!data.success || !data.prestamo) {
        throw new Error(data.message || "Respuesta del servidor incompleta");
      }

      // Mostrar mensaje de éxito inmediato
      showAlert("Préstamo registrado exitosamente", "success");

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
      // Manejar errores HTTP
      let error;
      try {
        error = await response.json();
      } catch (e) {
        // Si no se puede parsear el JSON, crear un objeto de error genérico
        error = {
          mensaje: `Error HTTP ${response.status}: ${response.statusText}`,
        };
      }

      console.error("Error del servidor:", error);

      // Mensajes detallados según el tipo de error
      if (error.estado) {
        // Error de préstamo activo
        alert(
          `${error.error || "ERROR"}\n\n` +
            `${error.mensaje}\n\n` +
            `Préstamo ID: ${error.prestamo_id}\n` +
            `Monto: S/ ${error.monto?.toFixed(2) || "N/A"}\n` +
            `Estado: ${error.estado}\n\n` +
            `${error.detalle || ""}`
        );
      } else if (error.errors) {
        // Errores de validación de Pydantic
        const erroresList = error.errors
          .map((e) => `- ${e.loc.join(".")}: ${e.msg}`)
          .join("\n");
        showAlert(`Errores de validación:\n\n${erroresList}`, "error");
      } else {
        // Otros errores
        showAlert(
          `ERROR: ${
            error.error ||
            error.mensaje ||
            error.message ||
            "Error al crear el préstamo"
          }`,
          "error"
        );
      }
    }
  } catch (error) {
    console.error("Error en la petición:", error);
    showAlert("❌ Error al crear el préstamo: " + error.message, "error");
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

    // Validar monto mínimo cuando el usuario sale del campo
    montoInput.addEventListener("blur", function () {
      const monto = parseFloat(montoInput.value);
      if (montoInput.value && !isNaN(monto)) {
        if (monto < 0) {
          showAlert("El monto no puede ser negativo", "error");
          montoInput.value = "";
          montoInput.focus();
        } 
      }
    });
  }

  const cuotasInput = document.getElementById("cuotas");
  if (cuotasInput) {
    // Validar cuotas mínimas cuando el usuario sale del campo
    cuotasInput.addEventListener("blur", function () {
      const cuotas = parseInt(cuotasInput.value);
      if (cuotasInput.value && !isNaN(cuotas)) {
        if (cuotas < 0) {
          showAlert("El número de cuotas no puede ser negativo", "error");
          cuotasInput.value = "";
        } else if (cuotas < 3) {
          showAlert("El número mínimo de cuotas es 3", "error");
          cuotasInput.value = "";
        }
      }
    });
  }

  const teaInput = document.getElementById("interes_tea");
  if (teaInput) {
    // Validar TEA cuando el usuario sale del campo
    teaInput.addEventListener("blur", function () {
      const tea = parseFloat(teaInput.value);
      if (teaInput.value && !isNaN(tea)) {
        if (tea < 0) {
          showAlert("La tasa de interés no puede ser negativa", "error");
          teaInput.value = "10";
        } else if (tea <= 0) {
          showAlert("La tasa de interés debe ser mayor a 0%", "error");
          teaInput.value = "10";
        } else if (tea > 100) {
          showAlert("La tasa de interés no puede ser mayor a 100%", "error");
          teaInput.value = "10";
        }
      }
    });
  }

  const checkbox = document.getElementById("declaracion-jurada-check");
  if (checkbox) {
    checkbox.addEventListener("change", actualizarEstadoBoton);
  }
});

console.log("client-search.js loaded");
