

def init_app(app):
    from .routes import declaraciones_bp
    app.register_blueprint(declaraciones_bp)
