# app.py
from flask import Flask, render_template
from blueprints.grafico_bp import grafico_bp
from blueprints.gran_m_bp import gran_m_bp

app = Flask(__name__)

# Registrar el Blueprint del Método Gráfico
# Todo lo que esté en grafico_bp tendrá el prefijo /metodo_grafico
app.register_blueprint(grafico_bp, url_prefix='/metodo_grafico')

# Registrar el Blueprint del Método de la Gran M
app.register_blueprint(gran_m_bp, url_prefix='/metodo_gran_m')

# Ruta raíz: No usar 
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)

