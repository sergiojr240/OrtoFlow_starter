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

        # Desenhar retângulo azul preenchido
        c.setFillColor(colors.HexColor('#0B66FF'))  # azul
        c.rect(x_quad, y_quad, quad_size, quad_size, stroke=0, fill=1)

        # Inserir uma pequena área branca interna para o QR (melhor contraste)
        #inset = 4  # pontos
        #inner_size = quad_size - 2 * inset
        #c.setFillColor(colors.white)
        #c.rect(x_quad + inset, y_quad + inset, inner_size, inner_size, stroke=0, fill=1)

        # Gerar QR code (dados básicos) e inserir no centro do quadrado
        qr_payload = f"ID:{paciente_id};Nome:{nome};Idade:{idade}"
        qr_img = qrcode.make(qr_payload).convert("RGB")
        # redimensionar o QR para caber no inner_size
        qr_px = int(inner_size)
        qr_img = qr_img.resize((qr_px, qr_px))
        qr_buf = BytesIO()
        qr_img.save(qr_buf, format='PNG')
        qr_buf.seek(0)
        c.drawImage(ImageReader(qr_buf), x_quad + inset, y_quad + inset,
                    width=inner_size, height=inner_size, mask='auto')

        # --- Dados do paciente (superior direito) ---
        x_right = width - margin
        y_top = height - margin - 6  # pequeno ajuste vertical

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
        ruler_y = margin + 20  # eleva um pouco do rodapé

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

        print(f"Processando imagem real para paciente: {paciente_id}")

        # Ler imagem
        imagem_bytes = arquivo.read()
        
        try:
            if processamento is None:
                return jsonify({"erro": "Módulo de processamento não disponível"}), 500
            
            # Chamar a função processar_imagem_ortese_api do módulo processamento_api
            resultado_processamento = processamento.processar_imagem_ortese_api(
                imagem_bytes=imagem_bytes,
                modo_manual=modo_manual,
                modelo_base_stl_path=MODELO_BASE_STL_PATH # Passar o caminho do modelo STL base
            )

            if resultado_processamento.get("erro"):
                return jsonify({"erro": resultado_processamento["erro"]}), 500

            # Salvar imagem processada (base64 decodificada)
            imagem_processada_base64 = resultado_processamento.get("imagem_processada")
            if imagem_processada_base64:
                # Remover o prefixo 'data:image/jpeg;base64,'
                header, encoded = imagem_processada_base64.split(",", 1)
                img_bytes = base64.b64decode(encoded)
                img_processada_path = os.path.join(app.config["UPLOAD_FOLDER"], f'{paciente_id}_processada.jpg')
                with open(img_processada_path, 'wb') as f:
                    f.write(img_bytes)
            else:
                img_processada_path = None

            # O caminho do STL é retornado diretamente agora
            caminho_stl = resultado_processamento.get("stl_path")
            if caminho_stl:
                # Renomear o STL gerado para o nome esperado pela rota de download
                final_stl_path = os.path.join(app.config["UPLOAD_FOLDER"], f'ortese_gerada_{paciente_id}.stl')
                os.rename(caminho_stl, final_stl_path)
                caminho_stl_url = f'/api/download-stl/{paciente_id}'
            else:
                caminho_stl_url = None

            return jsonify({
                'sucesso': True,
                'dimensoes': resultado_processamento['dimensoes'],
                'handedness': resultado_processamento['handedness'],
                'imagem_processada_url': f'/api/imagem-processada/{paciente_id}' if img_processada_path else None,
                'stl_url': caminho_stl_url
            })

        except Exception as e:
            return jsonify({'erro': f'Erro no processamento: {str(e)}'}), 500
        
    except Exception as e:
        print(f"Erro no processamento: {str(e)}")
        return jsonify({'erro': f'Erro no processamento: {str(e)}'}), 500


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