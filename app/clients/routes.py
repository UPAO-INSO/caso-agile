from . import bp
from flask import render_template, request, redirect, url_for, flash
from app.clients.model.clients import Cliente
from .. import db


@bp.route('/')
def list_clients():
    clients = Cliente.query.all()
    # blueprint template_folder points to app/clients/templates/
    return render_template('list.html', clients=clients)


@bp.route('/<int:cliente_id>')
def detail(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    return render_template('detail.html', cliente=cliente)
