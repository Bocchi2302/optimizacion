# blueprints/manual_bp.py
from flask import Blueprint, render_template

manual_bp = Blueprint('manual_bp', __name__)


@manual_bp.route('/es')
def manual_es():
    return render_template('manual/manual_es.html')


@manual_bp.route('/en')
def manual_en():
    return render_template('manual/manual_en.html')
