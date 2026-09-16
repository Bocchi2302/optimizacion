# app.py
from flask import Flask, render_template
from blueprints.grafico_bp import grafico_bp

app = Flask(__name__)

# Registrar el Blueprint del Método Gráfico
# Todo lo que esté en grafico_bp tendrá el prefijo /metodo_grafico
app.register_blueprint(grafico_bp, url_prefix='/metodo_grafico')

# Ruta raíz: No usar 
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)

