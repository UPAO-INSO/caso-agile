/**
 * State Module
 * Gestión de estado de la aplicación
 */

class StateManager {
  constructor() {
    this.state = {
      currentClient: null,
      currentPrestamo: null,
      isLoading: false,
      filters: {},
      searchResults: []
    };
    this.listeners = [];
  }

  /**
   * Obtener todo el estado
   * @returns {Object}
   */
  getState() {
    return { ...this.state };
  }

  /**
   * Obtener un valor del estado
   * @param {string} key - Clave del estado
   * @returns {*}
   */
  get(key) {
    return this.state[key];
  }

  /**
   * Actualizar el estado
   * @param {string|Object} keyOrState - Clave o objeto con múltiples claves
   * @param {*} value - Valor (si se proporciona una clave)
   */
  set(keyOrState, value) {
    const previousState = { ...this.state };

    if (typeof keyOrState === 'object') {
      // Actualización múltiple
      this.state = { ...this.state, ...keyOrState };
    } else {
      // Actualización simple
      this.state[keyOrState] = value;
    }

    // Notificar a los listeners
    this.notify(previousState, this.state);
  }

  /**
   * Suscribirse a cambios del estado
   * @param {Function} listener - Función callback
   * @returns {Function} - Función para desuscribirse
   */
  subscribe(listener) {
    this.listeners.push(listener);
    
    // Retornar función para desuscribirse
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  /**
   * Notificar a todos los listeners
   * @param {Object} previousState - Estado anterior
   * @param {Object} currentState - Estado actual
   */
  notify(previousState, currentState) {
    this.listeners.forEach(listener => {
      try {
        listener(currentState, previousState);
      } catch (error) {
        console.error('Error en listener:', error);
      }
    });
  }

  /**
   * Resetear el estado
   */
  reset() {
    const previousState = { ...this.state };
    
    this.state = {
      currentClient: null,
      currentPrestamo: null,
      isLoading: false,
      filters: {},
      searchResults: []
    };

    this.notify(previousState, this.state);
  }

  /**
   * Establecer cliente actual
   * @param {Object|null} client - Datos del cliente
   */
  setCurrentClient(client) {
    this.set('currentClient', client);
  }

  /**
   * Obtener cliente actual
   * @returns {Object|null}
   */
  getCurrentClient() {
    return this.get('currentClient');
  }

  /**
   * Establecer préstamo actual
   * @param {Object|null} prestamo - Datos del préstamo
   */
  setCurrentPrestamo(prestamo) {
    this.set('currentPrestamo', prestamo);
  }

  /**
   * Obtener préstamo actual
   * @returns {Object|null}
   */
  getCurrentPrestamo() {
    return this.get('currentPrestamo');
  }

  /**
   * Establecer estado de carga
   * @param {boolean} loading - Estado de carga
   */
  setLoading(loading) {
    this.set('isLoading', loading);
  }

  /**
   * Verificar si está cargando
   * @returns {boolean}
   */
  isLoading() {
    return this.get('isLoading');
  }

  /**
   * Establecer filtros
   * @param {Object} filters - Filtros a aplicar
   */
  setFilters(filters) {
    this.set('filters', { ...this.state.filters, ...filters });
  }

  /**
   * Obtener filtros
   * @returns {Object}
   */
  getFilters() {
    return this.get('filters');
  }

  /**
   * Limpiar filtros
   */
  clearFilters() {
    this.set('filters', {});
  }

  /**
   * Establecer resultados de búsqueda
   * @param {Array} results - Resultados
   */
  setSearchResults(results) {
    this.set('searchResults', results);
  }

  /**
   * Obtener resultados de búsqueda
   * @returns {Array}
   */
  getSearchResults() {
    return this.get('searchResults');
  }

  /**
   * Limpiar resultados de búsqueda
   */
  clearSearchResults() {
    this.set('searchResults', []);
  }
}

// Instancia singleton del estado
const state = new StateManager();

// Exportar funciones principales
export const getState = () => state.getState();
export const get = (key) => state.get(key);
export const set = (keyOrState, value) => state.set(keyOrState, value);
export const subscribe = (listener) => state.subscribe(listener);
export const reset = () => state.reset();

// Exportar funciones específicas
export const setCurrentClient = (client) => state.setCurrentClient(client);
export const getCurrentClient = () => state.getCurrentClient();
export const setCurrentPrestamo = (prestamo) => state.setCurrentPrestamo(prestamo);
export const getCurrentPrestamo = () => state.getCurrentPrestamo();
export const setLoading = (loading) => state.setLoading(loading);
export const isLoading = () => state.isLoading();
export const setFilters = (filters) => state.setFilters(filters);
export const getFilters = () => state.getFilters();
export const clearFilters = () => state.clearFilters();
export const setSearchResults = (results) => state.setSearchResults(results);
export const getSearchResults = () => state.getSearchResults();
export const clearSearchResults = () => state.clearSearchResults();

// Exportar manager por defecto
export default state;
