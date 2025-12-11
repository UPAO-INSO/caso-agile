"""
Routes - Autenticación
Endpoints para login y gestión de sesiones
Credenciales hardcodeadas en el sistema
"""
from flask import render_template, request, redirect, url_for, flash, session
import logging
from datetime import datetime

from app.common.extensions import db
from app.models.usuario import Usuario
from app.routes import auth_bp
from app.common.error_handler import ErrorHandler

logger = logging.getLogger(__name__)
error_handler = ErrorHandler(logger)

# Credenciales hardcodeadas
VALID_CREDENTIALS = {
    'admin': 'admin123',
    'operador': 'operador123'
}


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Endpoint de login"""
    if request.method == 'GET':
        # Si ya está autenticado, redirige al inicio
        if 'usuario_id' in session:
            return redirect(url_for('prestamos_view.index_view'))
        return render_template('auth/login.html')
    
    # POST: Procesar login
    usuario = request.form.get('usuario', '').strip()
    password = request.form.get('password', '').strip()
    
    if not usuario or not password:
        flash('Usuario y contraseña son requeridos', 'error')
        return render_template('auth/login.html')
    
    try:
        # Validar credenciales contra las hardcodeadas
        if usuario not in VALID_CREDENTIALS:
            logger.warning(f"Intento de login fallido: usuario '{usuario}' no encontrado")
            flash('Usuario o contraseña incorrectos', 'error')
            return render_template('auth/login.html')
        
        if VALID_CREDENTIALS[usuario] != password:
            logger.warning(f"Intento de login fallido: contraseña incorrecta para '{usuario}'")
            flash('Usuario o contraseña incorrectos', 'error')
            return render_template('auth/login.html')
        
        # Obtener usuario de la BD (para datos como nombre_completo y rol)
        user = Usuario.query.filter_by(usuario=usuario).first()
        
        if not user or not user.activo:
            logger.warning(f"Usuario '{usuario}' no está activo o no existe en BD")
            flash('La cuenta no está disponible', 'error')
            return render_template('auth/login.html')
        
        # Login exitoso
        session['usuario_id'] = user.usuario_id
        session['usuario'] = user.usuario
        session['nombre_completo'] = user.nombre_completo
        session['rol'] = user.rol
        
        # Actualizar fecha de última conexión
        user.fecha_ultima_conexion = datetime.now()
        db.session.commit()
        
        logger.info(f"Login exitoso para usuario: {usuario}")
        flash(f'Bienvenido, {user.nombre_completo}!', 'success')
        
        return redirect(url_for('prestamos_view.index_view'))
    
    except Exception as e:
        logger.error(f"Error durante login: {str(e)}")
        flash('Error durante el login. Intenta de nuevo.', 'error')
        return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Endpoint para cerrar sesión"""
    try:
        if 'usuario_id' in session:
            usuario = session.get('usuario', 'desconocido')
            session.clear()
            logger.info(f"Logout exitoso para usuario: {usuario}")
            flash('Sesión cerrada correctamente', 'success')
        return redirect(url_for('auth.login'))
    except Exception as e:
        logger.error(f"Error durante logout: {str(e)}")
        flash('Error al cerrar sesión', 'error')
        return redirect(url_for('auth.login'))

