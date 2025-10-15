from flask import render_template, Blueprint
from app.declaraciones.model.declaraciones import DeclaracionJurada


declaraciones_bp = Blueprint('declaraciones', __name__, url_prefix='/api/v1/declaraciones')


@declaraciones_bp.route('/')
def list_declaraciones():
    items = DeclaracionJurada.query.all()
    return render_template('list.html', declaraciones=items)


@declaraciones_bp.route('/<int:declaracion_id>')
def detail(declaracion_id):
    item = DeclaracionJurada.query.get_or_404(declaracion_id)
    return render_template('detail.html', declaracion=item)
