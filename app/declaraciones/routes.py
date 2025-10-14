from . import bp
from flask import render_template
from app.declaraciones.model.declaraciones import DeclaracionJurada


@bp.route('/')
def list_declaraciones():
    items = DeclaracionJurada.query.all()
    return render_template('list.html', declaraciones=items)


@bp.route('/<int:declaracion_id>')
def detail(declaracion_id):
    item = DeclaracionJurada.query.get_or_404(declaracion_id)
    return render_template('detail.html', declaracion=item)
