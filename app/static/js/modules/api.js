/**
 * API Module
 * Maneja todas las llamadas a la API REST
 */

const API_BASE_URL = '/api/v1';

/**
 * Realiza una petición fetch con manejo de errores
 * @param {string} url - URL del endpoint
 * @param {Object} options - Opciones de fetch
 * @returns {Promise<Object>} - Respuesta JSON
 */
async function fetchAPI(url, options = {}) {
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  };

  try {
    const response = await fetch(url, defaultOptions);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    // Si es un DELETE o no hay contenido, retornar success
    if (response.status === 204 || response.headers.get('content-length') === '0') {
      return { success: true };
    }

    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

/**
 * API de Clientes
 */
export const ClientesAPI = {
  /**
   * Buscar cliente por DNI
   * @param {string} dni - DNI del cliente
   * @returns {Promise<Object>}
   */
  async buscarPorDNI(dni) {
    return fetchAPI(`${API_BASE_URL}/clientes/dni/${dni}`);
  },

  /**
   * Obtener cliente por ID
   * @param {number} id - ID del cliente
   * @returns {Promise<Object>}
   */
  async obtenerPorId(id) {
    return fetchAPI(`${API_BASE_URL}/clientes/${id}`);
  },

  /**
   * Listar todos los clientes
   * @returns {Promise<Array>}
   */
  async listarTodos() {
    return fetchAPI(`${API_BASE_URL}/clientes`);
  },

  /**
   * Crear nuevo cliente
   * @param {Object} clienteData - Datos del cliente
   * @returns {Promise<Object>}
   */
  async crear(clienteData) {
    return fetchAPI(`${API_BASE_URL}/clientes`, {
      method: 'POST',
      body: JSON.stringify(clienteData)
    });
  },

  /**
   * Actualizar cliente
   * @param {number} id - ID del cliente
   * @param {Object} clienteData - Datos actualizados
   * @returns {Promise<Object>}
   */
  async actualizar(id, clienteData) {
    return fetchAPI(`${API_BASE_URL}/clientes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(clienteData)
    });
  },

  /**
   * Eliminar cliente
   * @param {number} id - ID del cliente
   * @returns {Promise<Object>}
   */
  async eliminar(id) {
    return fetchAPI(`${API_BASE_URL}/clientes/${id}`, {
      method: 'DELETE'
    });
  },

  /**
   * Verificar préstamo activo
   * @param {number} id - ID del cliente
   * @returns {Promise<Object>}
   */
  async verificarPrestamoActivo(id) {
    return fetchAPI(`${API_BASE_URL}/clientes/verificar-prestamo/${id}`);
  },

  /**
   * Consultar DNI en RENIEC
   * @param {string} dni - DNI a consultar
   * @returns {Promise<Object>}
   */
  async consultarDNI(dni) {
    return fetchAPI(`${API_BASE_URL}/clientes/consultar-dni/${dni}`);
  },

  /**
   * Validar PEP
   * @param {string} dni - DNI a validar
   * @returns {Promise<Object>}
   */
  async validarPEP(dni) {
    return fetchAPI(`${API_BASE_URL}/clientes/validar-pep/${dni}`);
  }
};

/**
 * API de Préstamos
 */
export const PrestamosAPI = {
  /**
   * Registrar nuevo préstamo
   * @param {Object} prestamoData - Datos del préstamo
   * @returns {Promise<Object>}
   */
  async registrar(prestamoData) {
    return fetchAPI(`${API_BASE_URL}/prestamos`, {
      method: 'POST',
      body: JSON.stringify(prestamoData)
    });
  },

  /**
   * Obtener préstamo por ID
   * @param {number} id - ID del préstamo
   * @returns {Promise<Object>}
   */
  async obtenerPorId(id) {
    return fetchAPI(`${API_BASE_URL}/prestamos/${id}`);
  },

  /**
   * Listar préstamos de un cliente
   * @param {number} clienteId - ID del cliente
   * @returns {Promise<Array>}
   */
  async listarPorCliente(clienteId) {
    return fetchAPI(`${API_BASE_URL}/clientes/${clienteId}/prestamos`);
  },

  /**
   * Obtener préstamos con cronogramas
   * @param {number} clienteId - ID del cliente
   * @returns {Promise<Array>}
   */
  async obtenerConCronogramas(clienteId) {
    return fetchAPI(`${API_BASE_URL}/clientes/${clienteId}/prestamos/detalle`);
  },

  /**
   * Actualizar estado del préstamo
   * @param {number} id - ID del préstamo
   * @param {string} estado - Nuevo estado (VIGENTE/CANCELADO)
   * @returns {Promise<Object>}
   */
  async actualizarEstado(id, estado) {
    return fetchAPI(`${API_BASE_URL}/prestamos/${id}/estado`, {
      method: 'PUT',
      body: JSON.stringify({ estado })
    });
  }
};

export default {
  ClientesAPI,
  PrestamosAPI,
  fetchAPI
};
