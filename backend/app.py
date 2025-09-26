import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import qrcode
from io import BytesIO

app = Flask(__name__)

# Configuração CORS para produção
CORS(app)

# Configurações para Render
UPLOAD_FOLDER = '/tmp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

try:
    from processamento_api import processar_imagem_ortese_api, gerar_stl_simples
    print("✅ Módulo de processamento carregado")
except ImportError as e:
    print(f"❌ Erro ao importar módulo: {e}")
    
    def processar_imagem_ortese_api(*args, **kwargs):
        return {"erro": "Módulo de processamento não carregado"}
    def gerar_stl_simples(*args, **kwargs):
        return False

@app.route('/')
def home():
    return jsonify({
        "message": "API de Geração de Órteses - Online",
        "status": "online",
        "version": "1.0"
    })

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})

# ... (adicionar aqui todas as suas rotas existentes)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)