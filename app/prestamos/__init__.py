from flask import Blueprint

prestamos_bp = Blueprint(
    'prestamos',
    __name__,
    url_prefix='/api/v1/prestamos',
    template_folder='templates'
)

def init_app(app):

    from . import routes
    app.register_blueprint(prestamos_bp)
