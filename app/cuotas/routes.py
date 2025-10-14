from . import bp
from flask import render_template
from app.cuotas.model.cuotas import Cuota


@bp.route('/')
def list_cuotas():
    items = Cuota.query.all()
    # blueprint's template_folder points to app/cuotas/templates/
    return render_template('list.html', cuotas=items)


@bp.route('/<int:cuota_id>')
def detail(cuota_id):
    item = Cuota.query.get_or_404(cuota_id)
    return render_template('detail.html', cuota=item)
