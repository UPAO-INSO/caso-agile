from flask import Blueprint

bp = Blueprint('declaraciones', __name__, url_prefix='/declaraciones', template_folder='templates')

from . import routes  # noqa

def init_app(app):
    app.register_blueprint(bp)
