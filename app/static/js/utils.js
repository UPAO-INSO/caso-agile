// utils.js - Utilidades compartidas entre módulos

/**
 * Mostrar alerta temporal
 * @param {string} message - Mensaje a mostrar
 * @param {string} type - Tipo de alerta: 'success', 'error', 'info', 'warning'
 */
function showAlert(message, type = 'info') {
  const alert = document.createElement('div');
  alert.className = `alert alert-${type}`;
  alert.textContent = message;
  
  // Colores según tipo
  const colors = {
    'success': '#34C759',
    'error': '#FF3B30',
    'info': '#007AFF',
    'warning': '#FF9500'
  };
  
  alert.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 16px 24px;
    background: ${colors[type] || colors['info']};
    color: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 10000;
    font-weight: 500;
  `;
  
  document.body.appendChild(alert);
  
  setTimeout(() => {
    alert.remove();
  }, 4000); // 4 segundos para warnings (más tiempo para leer)
}

console.log('utils.js loaded');
