from flask import Blueprint, render_template, redirect
from flask_login import current_user
bp=Blueprint('main',__name__)
@bp.get('/')
def index(): return redirect('/admin/') if current_user.is_authenticated else render_template('main/index.html')
