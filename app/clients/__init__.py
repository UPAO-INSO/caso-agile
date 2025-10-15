from flask import Blueprint

clientes_bp = Blueprint('clientes', __name__, url_prefix='/api/v1/clientes', template_folder='templates')

def init_app(app):
    from . import routes
    app.register_blueprint(clientes_bp)

