from flask import Blueprint

from . import routes  # noqa: ensure routes module is loaded


def init_app(app, api_prefix='/api'):
    from .routes import cuotas_bp
    app.register_blueprint(cuotas_bp, url_prefix=f"{api_prefix}/cuotas")
