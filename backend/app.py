import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import qrcode
from io import BytesIO
import base64

app = Flask(__name__)

# 🔥🔥🔥 CORS NUCLEAR - PERMITE TUDO
CORS(app, resources={r"/*": {"origins": "*"}})

# Configurações
UPLOAD_FOLDER = '/tmp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 🔥🔥🔥 MIDDLEWARE CORS MANUAL EXTREMO
@app.before_request
def before_request():
    if request.method == 'OPTIONS':
        return '', 200

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', '*')
    response.headers.add('Access-Control-Allow-Methods', '*')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# 🔥🔥🔥 ROTA CATCH-ALL PARA OPTIONS
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    return '', 200

try:
    from processamento_api import processar_imagem_ortese_api, gerar_stl_simples
    print("✅ Módulo de processamento carregado")
except ImportError as e:
    print(f"❌ Erro ao importar módulo: {e}")
    
    def processar_imagem_ortese_api(*args, **kwargs):
        return {"erro": "Módulo de processamento não carregado"}
    def gerar_stl_simples(*args, **kwargs):
        return False

# ===== ROTAS PRINCIPAIS =====
@app.route('/')
def home():
    return jsonify({
        "message": "API de Geração de Órteses Online", 
        "status": "online",
        "version": "2.0",
        "cors": "enabled"
    })

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health():
    return jsonify({
        "status": "healthy", 
        "cors": "working",
        "timestamp": "2024-01-01"
    })

@app.route('/health', methods=['GET', 'OPTIONS'])
def health_alt():
    return jsonify({"status": "healthy", "route": "alternativa"})

# ===== CADASTRO DE PACIENTE =====
@app.route('/api/cadastrar-paciente', methods=['POST', 'OPTIONS'])
def cadastrar_paciente():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # 🔥 CORREÇÃO: Usar get_json() em vez de request.json
        data = request.get_json(silent=True) or {}
        print("📥 Dados recebidos:", data)
        
        nome = data.get('nome', '').strip()
        idade = data.get('idade', '').strip()
        email = data.get('email', '').strip()

        if not nome or not idade:
            return jsonify({'erro': 'Nome e idade são obrigatórios'}), 400

        # Gerar ID único
        paciente_id = 'P' + str(uuid.uuid4())[:8].upper()
        print(f"👤 Novo paciente: {nome} - ID: {paciente_id}")

        # Gerar QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(paciente_id)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode('utf-8')

        # Gerar folha padrão
        folha_path = os.path.join(app.config['UPLOAD_FOLDER'], f'folha_{paciente_id}.pdf')
        if gerar_folha_padrao(paciente_id, nome, idade, folha_path):
            return jsonify({
                'sucesso': True,
                'paciente_id': paciente_id,
                'qr_code': f'data:image/png;base64,{qr_base64}',
                'folha_padrao_url': f'/api/baixar-folha/{paciente_id}',
                'mensagem': 'Paciente cadastrado com sucesso'
            })
        else:
            return jsonify({'erro': 'Erro ao gerar folha padrão'}), 500

    except Exception as e:
        print(f"💥 Erro no cadastro: {str(e)}")
        return jsonify({'erro': f'Erro no servidor: {str(e)}'}), 500

def gerar_folha_padrao(paciente_id, nome, idade, output_path):
    try:
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4
        
        # Cabeçalho
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 100, "Sistema de Geração de Órteses Personalizadas")
        
        # Informações do paciente
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 140, f"Paciente: {nome}")
        c.drawString(100, height - 160, f"Idade: {idade} anos")
        c.drawString(100, height - 180, f"ID: {paciente_id}")
        
        c.save()
        print(f"📄 Folha gerada: {output_path}")
        return True
        
    except Exception as e:
        print(f"Erro gerando folha: {e}")
        return False

@app.route('/api/baixar-folha/<paciente_id>', methods=['GET', 'OPTIONS'])
def baixar_folha(paciente_id):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        folha_path = os.path.join(app.config['UPLOAD_FOLDER'], f'folha_{paciente_id}.pdf')
        if os.path.exists(folha_path):
            return send_file(folha_path, as_attachment=True, download_name=f'folha_referencia_{paciente_id}.pdf')
        return jsonify({'erro': 'Folha não encontrada'}), 404
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ===== PROCESSAMENTO DE IMAGEM (SIMULAÇÃO) =====
@app.route('/api/processar-imagem', methods=['POST', 'OPTIONS'])
def processar_imagem():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        if 'imagem' not in request.files:
            return jsonify({'erro': 'Nenhuma imagem enviada'}), 400
        
        arquivo = request.files['imagem']
        paciente_id = request.form.get('paciente_id', '')
        modo_manual = request.form.get('modo_manual', 'false').lower() == 'true'

        if arquivo.filename == '':
            return jsonify({'erro': 'Nome de arquivo vazio'}), 400

        print(f"📸 Processando imagem para paciente: {paciente_id}")

        # Simular processamento
        resultado = {
            'sucesso': True,
            'dimensoes': {
                'Largura Pulso': '6.5 cm',
                'Largura Palma': '8.2 cm',
                'Comprimento Mao': '18.7 cm',
                'Tamanho Ortese': 'M'
            },
            'handedness': 'Direita',
            'imagem_processada': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
            'mensagem': 'Processamento simulado - funcionalidade real em desenvolvimento'
        }

        return jsonify(resultado)
        
    except Exception as e:
        print(f"💥 Erro no processamento: {str(e)}")
        return jsonify({'erro': f'Erro no processamento: {str(e)}'}), 500

@app.route('/api/download-stl/<paciente_id>', methods=['GET', 'OPTIONS'])
def download_stl(paciente_id):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # Simular arquivo STL
        stl_path = os.path.join(app.config['UPLOAD_FOLDER'], f'ortese_{paciente_id}.stl')
        
        # Criar arquivo STL vazio para teste
        with open(stl_path, 'w') as f:
            f.write(f"# STL simulado para paciente {paciente_id}")
            
        return send_file(stl_path, as_attachment=True, download_name=f'ortese_{paciente_id}.stl')
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Servidor iniciando na porta {port}")
    print("🔧 CORS CONFIGURADO - PERMITINDO TUDO")
    print("🌐 URLs testáveis:")
    print(f"   - https://ortese-backend.onrender.com/")
    print(f"   - https://ortese-backend.onrender.com/api/health")
    print(f"   - https://ortese-backend.onrender.com/health")
    app.run(host='0.0.0.0', port=port, debug=False)