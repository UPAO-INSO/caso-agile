from . import bp
from flask import render_template
from app.prestamos.model.prestamos import Prestamo


@bp.route('/')
def list_prestamos():
    items = Prestamo.query.all()
    return render_template('list.html', prestamos=items)


@bp.route('/<int:prestamo_id>')
def detail(prestamo_id):
    item = Prestamo.query.get_or_404(prestamo_id)
    return render_template('detail.html', prestamo=item)
