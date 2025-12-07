from flask import render_template
from app.models import DeclaracionJurada
from app.routes import declaraciones_bp


@declaraciones_bp.route('/')
def list_declaraciones():
    items = DeclaracionJurada.query.all()
    return render_template('list.html', declaraciones=items)


@declaraciones_bp.route('/<int:declaracion_id>')
def detail(declaracion_id):
    item = DeclaracionJurada.query.get_or_404(declaracion_id)
    return render_template('detail.html', declaracion=item)
