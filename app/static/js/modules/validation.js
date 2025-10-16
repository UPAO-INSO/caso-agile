/**
 * Validation Module
 * Validaciones del lado del cliente
 */

/**
 * Validar DNI peruano (8 dígitos)
 * @param {string} dni - DNI a validar
 * @returns {Object} - { valid: boolean, message: string }
 */
export function validarDNI(dni) {
  if (!dni || dni.trim().length === 0) {
    return { valid: false, message: 'El DNI es obligatorio' };
  }

  const dniLimpio = dni.trim();

  if (dniLimpio.length !== 8) {
    return { valid: false, message: 'El DNI debe tener 8 dígitos' };
  }

  if (!/^\d{8}$/.test(dniLimpio)) {
    return { valid: false, message: 'El DNI solo debe contener números' };
  }

  return { valid: true, message: '' };
}

/**
 * Validar email
 * @param {string} email - Email a validar
 * @returns {Object} - { valid: boolean, message: string }
 */
export function validarEmail(email) {
  if (!email || email.trim().length === 0) {
    return { valid: false, message: 'El email es obligatorio' };
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  
  if (!emailRegex.test(email.trim())) {
    return { valid: false, message: 'El email no es válido' };
  }

  return { valid: true, message: '' };
}

/**
 * Validar teléfono peruano (9 dígitos)
 * @param {string} telefono - Teléfono a validar
 * @returns {Object} - { valid: boolean, message: string }
 */
export function validarTelefono(telefono) {
  if (!telefono || telefono.trim().length === 0) {
    return { valid: false, message: 'El teléfono es obligatorio' };
  }

  const telefonoLimpio = telefono.trim();

  if (telefonoLimpio.length !== 9) {
    return { valid: false, message: 'El teléfono debe tener 9 dígitos' };
  }

  if (!/^9\d{8}$/.test(telefonoLimpio)) {
    return { valid: false, message: 'El teléfono debe iniciar con 9' };
  }

  return { valid: true, message: '' };
}

/**
 * Validar nombre (solo letras y espacios)
 * @param {string} nombre - Nombre a validar
 * @returns {Object} - { valid: boolean, message: string }
 */
export function validarNombre(nombre) {
  if (!nombre || nombre.trim().length === 0) {
    return { valid: false, message: 'El nombre es obligatorio' };
  }

  if (nombre.trim().length < 2) {
    return { valid: false, message: 'El nombre debe tener al menos 2 caracteres' };
  }

  if (!/^[a-záéíóúñü\s]+$/i.test(nombre.trim())) {
    return { valid: false, message: 'El nombre solo debe contener letras' };
  }

  return { valid: true, message: '' };
}

/**
 * Validar dirección
 * @param {string} direccion - Dirección a validar
 * @returns {Object} - { valid: boolean, message: string }
 */
export function validarDireccion(direccion) {
  if (!direccion || direccion.trim().length === 0) {
    return { valid: false, message: 'La dirección es obligatoria' };
  }

  if (direccion.trim().length < 5) {
    return { valid: false, message: 'La dirección debe tener al menos 5 caracteres' };
  }

  return { valid: true, message: '' };
}

/**
 * Validar monto (número positivo)
 * @param {string|number} monto - Monto a validar
 * @returns {Object} - { valid: boolean, message: string }
 */
export function validarMonto(monto) {
  if (!monto || monto.toString().trim().length === 0) {
    return { valid: false, message: 'El monto es obligatorio' };
  }

  const montoNumero = parseFloat(monto);

  if (isNaN(montoNumero)) {
    return { valid: false, message: 'El monto debe ser un número' };
  }

  if (montoNumero <= 0) {
    return { valid: false, message: 'El monto debe ser mayor a 0' };
  }

  if (montoNumero > 50000) {
    return { valid: false, message: 'El monto no puede superar S/ 50,000' };
  }

  return { valid: true, message: '' };
}

/**
 * Validar TEA (Tasa Efectiva Anual)
 * @param {string|number} tea - TEA a validar
 * @returns {Object} - { valid: boolean, message: string }
 */
export function validarTEA(tea) {
  if (!tea || tea.toString().trim().length === 0) {
    return { valid: false, message: 'La TEA es obligatoria' };
  }

  const teaNumero = parseFloat(tea);

  if (isNaN(teaNumero)) {
    return { valid: false, message: 'La TEA debe ser un número' };
  }

  if (teaNumero <= 0) {
    return { valid: false, message: 'La TEA debe ser mayor a 0' };
  }

  if (teaNumero > 100) {
    return { valid: false, message: 'La TEA no puede superar 100%' };
  }

  return { valid: true, message: '' };
}

/**
 * Validar número de cuotas
 * @param {string|number} cuotas - Número de cuotas a validar
 * @returns {Object} - { valid: boolean, message: string }
 */
export function validarCuotas(cuotas) {
  if (!cuotas || cuotas.toString().trim().length === 0) {
    return { valid: false, message: 'El número de cuotas es obligatorio' };
  }

  const cuotasNumero = parseInt(cuotas);

  if (isNaN(cuotasNumero)) {
    return { valid: false, message: 'El número de cuotas debe ser un número entero' };
  }

  if (cuotasNumero < 1) {
    return { valid: false, message: 'Debe haber al menos 1 cuota' };
  }

  if (cuotasNumero > 36) {
    return { valid: false, message: 'El número máximo de cuotas es 36' };
  }

  return { valid: true, message: '' };
}

/**
 * Validar fecha (formato YYYY-MM-DD)
 * @param {string} fecha - Fecha a validar
 * @returns {Object} - { valid: boolean, message: string }
 */
export function validarFecha(fecha) {
  if (!fecha || fecha.trim().length === 0) {
    return { valid: false, message: 'La fecha es obligatoria' };
  }

  const fechaRegex = /^\d{4}-\d{2}-\d{2}$/;
  
  if (!fechaRegex.test(fecha)) {
    return { valid: false, message: 'Formato de fecha inválido (YYYY-MM-DD)' };
  }

  const fechaObj = new Date(fecha);
  
  if (isNaN(fechaObj.getTime())) {
    return { valid: false, message: 'Fecha inválida' };
  }

  return { valid: true, message: '' };
}

/**
 * Validar formulario de cliente
 * @param {Object} formData - Datos del formulario
 * @returns {Object} - { valid: boolean, errors: Object }
 */
export function validarFormularioCliente(formData) {
  const errors = {};

  const dniValidation = validarDNI(formData.dni);
  if (!dniValidation.valid) errors.dni = dniValidation.message;

  const nombreValidation = validarNombre(formData.nombre);
  if (!nombreValidation.valid) errors.nombre = nombreValidation.message;

  const apellidoValidation = validarNombre(formData.apellido);
  if (!apellidoValidation.valid) errors.apellido = apellidoValidation.message;

  const emailValidation = validarEmail(formData.email);
  if (!emailValidation.valid) errors.email = emailValidation.message;

  const telefonoValidation = validarTelefono(formData.telefono);
  if (!telefonoValidation.valid) errors.telefono = telefonoValidation.message;

  const direccionValidation = validarDireccion(formData.direccion);
  if (!direccionValidation.valid) errors.direccion = direccionValidation.message;

  return {
    valid: Object.keys(errors).length === 0,
    errors
  };
}

/**
 * Validar formulario de préstamo
 * @param {Object} formData - Datos del formulario
 * @returns {Object} - { valid: boolean, errors: Object }
 */
export function validarFormularioPrestamo(formData) {
  const errors = {};

  const montoValidation = validarMonto(formData.monto);
  if (!montoValidation.valid) errors.monto = montoValidation.message;

  const teaValidation = validarTEA(formData.tea);
  if (!teaValidation.valid) errors.tea = teaValidation.message;

  const cuotasValidation = validarCuotas(formData.cuotas);
  if (!cuotasValidation.valid) errors.cuotas = cuotasValidation.message;

  const fechaValidation = validarFecha(formData.fecha_desembolso);
  if (!fechaValidation.valid) errors.fecha_desembolso = fechaValidation.message;

  return {
    valid: Object.keys(errors).length === 0,
    errors
  };
}

export default {
  validarDNI,
  validarEmail,
  validarTelefono,
  validarNombre,
  validarDireccion,
  validarMonto,
  validarTEA,
  validarCuotas,
  validarFecha,
  validarFormularioCliente,
  validarFormularioPrestamo
};
