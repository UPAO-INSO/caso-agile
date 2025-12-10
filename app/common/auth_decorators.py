"""
Decoradores de Autenticación y Autorización
Controla el acceso a rutas protegidas
"""
from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    """Decorador que requiere autenticación para acceder a una ruta"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorador que requiere rol de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('auth.login'))
        
        if session.get('rol') != 'admin':
            flash('No tienes permisos para acceder a esta página', 'error')
            return redirect(url_for('prestamos_view.index_view'))
        
        return f(*args, **kwargs)
    return decorated_function


def operador_required(f):
    """Decorador que requiere rol de operador o administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('auth.login'))
        
        rol = session.get('rol')
        if rol not in ['operador', 'admin']:
            flash('No tienes permisos para acceder a esta página', 'error')
            return redirect(url_for('prestamos_view.index_view'))
        
        return f(*args, **kwargs)
    return decorated_function
