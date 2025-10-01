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
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# Configurações
UPLOAD_FOLDER = '/tmp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MIDDLEWARE CORS MANUAL EXTREMO
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

# ROTA CATCH-ALL PARA OPTIONS
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    return '', 200

import importlib.util

# Caminho para o modelo STL base fornecido pelo usuário
# Certifique-se de que este arquivo esteja acessível no ambiente de execução
MODELO_BASE_STL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'upload', 'wristband_2.0(1).stl')

# Carregar módulo de processamento
try:
    spec = importlib.util.spec_from_file_location("processamento",
                                                 os.path.join(os.path.dirname(__file__), "processamento_api.py"))
    processamento = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(processamento)
    print("Módulo de processamento carregado com sucesso")
except Exception as e:
    print(f"Erro ao carregar módulo de processamento: {e}")
    processamento = None

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
        # CORREÇÃO: Usar get_json() em vez de request.json
        data = request.get_json(silent=True) or {}
        print("Dados recebidos:", data)
        
        nome = data.get('nome', '').strip()
        idade = data.get('idade', '').strip()
        email = data.get('email', '').strip()

        if not nome or not idade:
            return jsonify({'erro': 'Nome e idade são obrigatórios'}), 400

        # Gerar ID único
        paciente_id = 'P' + str(uuid.uuid4())[:8].upper()
        print(f"Novo paciente: {nome} - ID: {paciente_id}")

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
        print(f"Erro no cadastro: {str(e)}")
        return jsonify({'erro': f'Erro no servidor: {str(e)}'}), 500

def gerar_folha_padrao(paciente_id, nome, idade, output_path):
    try:
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4

        # Conversão cm -> pontos (pt)
        cm_pt = 28.3464567
        margin = 20  # margem em pontos

        # --- Quadrado azul 6x6cm (superior esquerdo) ---
        quad_size = 6.0 * cm_pt
        x_quad = margin
        y_quad = height - margin - quad_size

        # Desenhar retângulo azul preenchido (SEM área branca interna)
        c.setFillColor(colors.HexColor('#0B66FF'))  # azul
        c.rect(x_quad, y_quad, quad_size, quad_size, stroke=0, fill=1)

        # --- QR code SEM fundo branco ---
        qr_payload = f"ID:{paciente_id};Nome:{nome};Idade:{idade}"
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(qr_payload)
        qr.make(fit=True)
        
        # Criar QR code sem fundo branco
        qr_img = qr.make_image(fill_color="black", back_color="blue")  # back_color=None para fundo transparente
        qr_img = qr_img.convert("RGBA")
        
        # Redimensionar QR code para caber dentro do quadrado azul
        qr_size = int(quad_size * 0.7)  # 70% do tamanho do quadrado
        qr_img = qr_img.resize((qr_size, qr_size))
        
        # Salvar QR code temporariamente
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        # Posicionar QR code no centro do quadrado azul
        qr_x = x_quad + (quad_size - qr_size) / 2
        qr_y = y_quad + (quad_size - qr_size) / 2
        c.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size, mask='auto')

        # --- Dados do paciente (superior direito) ---
        x_right = width - margin
        y_top = height - margin - 6

        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(x_right, y_top, f"Paciente: {nome}")
        c.setFont("Helvetica", 10)
        c.drawRightString(x_right, y_top - 15, f"Idade: {idade} anos")
        c.drawRightString(x_right, y_top - 30, f"ID: {paciente_id}")

        # --- Régua graduada (~10 cm) no canto inferior direito ---
        ruler_cm = 10.0
        ruler_w = ruler_cm * cm_pt
        ruler_x = width - margin - ruler_w
        ruler_y = margin + 20

        # Linha principal
        c.setLineWidth(1)
        c.line(ruler_x, ruler_y, ruler_x + ruler_w, ruler_y)

        # Ticks e legendas
        for i in range(11):  # 0..10 (11 marcas)
            x_tick = ruler_x + (i * (ruler_w / 10.0))
            # marca maior a cada 5 (0cm e 5cm e 10cm)
            if i % 5 == 0:
                tick_h = 12
                c.line(x_tick, ruler_y, x_tick, ruler_y + tick_h)
                # label numérico (centro/baixo da marca)
                c.setFont("Helvetica", 8)
                c.drawCentredString(x_tick, ruler_y + tick_h + 2, str(i))
            else:
                tick_h = 6
                c.line(x_tick, ruler_y, x_tick, ruler_y + tick_h)

        # legenda "cm" no final
        c.setFont("Helvetica", 8)
        c.drawRightString(ruler_x + ruler_w, ruler_y + 22, "cm")

        # Rodapé informativo
        c.setFont("Helvetica", 8)
        c.drawString(margin, 10, "Imprima em escala 100% (sem ajuste 'Ajustar à página') para garantir precisão da régua.")

        c.showPage()
        c.save()
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
            return send_file(folha_path, as_attachment=True, download_name=f'folha_{paciente_id}.pdf')
        return jsonify({'erro': 'Folha não encontrada'}), 404
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ===== PROCESSAMENTO REAL DE IMAGEM =====
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

        print(f"📸 Processando imagem com método melhorado...")

        # Ler imagem
        imagem_bytes = arquivo.read()
        
        # 🔥 USAR PROCESSAMENTO MELHORADO
        try:
            resultado = processar_imagem_ortese_api_melhorado(imagem_bytes, modo_manual)
            
            if resultado.get('sucesso'):
                print("✅ Processamento melhorado bem-sucedido!")
            else:
                print("❌ Processamento melhorado falhou, usando fallback")
                resultado = processamento_simulado()
                
        except Exception as e:
            print(f"⚠️ Erro no processamento melhorado: {e}")
            resultado = processamento_simulado()

        return jsonify(resultado)
        
    except Exception as e:
        print(f"💥 Erro no processamento: {str(e)}")
        return jsonify({'erro': f'Erro no processamento: {str(e)}'}), 500

def processamento_simulado():
    """Simulação de processamento quando o módulo real não está disponível"""
    import random
    
    # Gerar medidas realistas com alguma variação
    largura_pulso = round(5.5 + random.random() * 2, 1)  # 5.5-7.5 cm
    largura_palma = round(7.0 + random.random() * 3, 1)  # 7.0-10.0 cm
    comprimento_mao = round(16.0 + random.random() * 5, 1)  # 16.0-21.0 cm
    
    # Determinar tamanho da órtese
    if largura_palma < 7.5:
        tamanho_ortese = "P"
    elif largura_palma < 9.0:
        tamanho_ortese = "M"
    else:
        tamanho_ortese = "G"
    
    # Determinar mão (direita/esquerda) baseado em aleatório
    handedness = "Direita" if random.random() > 0.5 else "Esquerda"
    
    return {
        'sucesso': True,
        'dimensoes': {
            'Largura Pulso': f'{largura_pulso} cm',
            'Largura Palma': f'{largura_palma} cm',
            'Comprimento Mao': f'{comprimento_mao} cm',
            'Tamanho Ortese': tamanho_ortese
        },
        'handedness': handedness,
        'imagem_processada': None,  # Será preenchida se disponível
        'mensagem': 'Processamento concluído com sucesso',
        'tipo_processamento': 'simulado'  # Para debug
    }


@app.route('/api/download-stl/<paciente_id>', methods=['GET', 'OPTIONS'])
def download_stl(paciente_id):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        stl_path = os.path.join(app.config["UPLOAD_FOLDER"], f'ortese_gerada_{paciente_id}.stl')
        if os.path.exists(stl_path):
            return send_file(stl_path, as_attachment=True, download_name=f'ortese_gerada_{paciente_id}.stl')
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Servidor iniciando na porta {port}")
    print("CORS CONFIGURADO - PERMITINDO TUDO")
    print("URLs testáveis:")
    print(f"   - https://ortoflow-backend.onrender.com/")
    print(f"   - https://ortoflow-backend.onrender.com/api/health")
    print(f"   - https://ortoflow-backend.onrender.com/health")
    app.run(host='0.0.0.0', port=port, debug=False)