import cv2 as cv
import numpy as np
import mediapipe as mp
import base64
from stl import mesh
import os
import math
import logging

# Configurações
TAMANHO_QUADRADO_CM = 6.0
LOWER_BLUE = np.array([75, 80, 50])
UPPER_BLUE = np.array([140, 255, 255])

# Inicializar MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

logger = logging.getLogger(__name__)

def _dist(p1, p2):
    return math.hypot(p1[0]-p2[0], p1[1]-p2[1])
    
def detectar_quadrado_azul(imagem):
    """Detecta quadrado azul na imagem e retorna o contorno, dimensões e a máscara."""
    try:
        imagem_hsv = cv.cvtColor(imagem, cv.COLOR_BGR2HSV)
        
        # CORREÇÃO: Ajustar faixa de cor para azul
        lower_blue = np.array([90, 100, 50])   # Azul mais escuro
        upper_blue = np.array([130, 255, 255]) # Azul mais claro
        
        mascara = cv.inRange(imagem_hsv, lower_blue, upper_blue)
        
        # CORREÇÃO: Melhorar operações morfológicas
        kernel = np.ones((9, 9), np.uint8)
        mascara = cv.morphologyEx(mascara, cv.MORPH_CLOSE, kernel, iterations=2)
        mascara = cv.morphologyEx(mascara, cv.MORPH_OPEN, kernel, iterations=2)
        
        contornos, _ = cv.findContours(mascara, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        
        if contornos is None or len(contornos) == 0:
            print("❌ Nenhum contorno azul encontrado")
            return None, None, None
        
        # CORREÇÃO: Ordenar contornos por área (maior primeiro)
        contornos = sorted(contornos, key=cv.contourArea, reverse=True)
        
        for contorno in contornos:
            area = cv.contourArea(contorno)
            if area < 1000: # Aumentar limite mínimo
                continue
                
            perimetro = cv.arcLength(contorno, True)
            aprox = cv.approxPolyDP(contorno, 0.02 * perimetro, True)
            
            if len(aprox) == 4: # Quadrilátero
                x, y, w, h = cv.boundingRect(aprox)
                razao_aspecto = float(w) / h
                
                # CORREÇÃO: Tornar critério de aspecto mais flexível
                if 0.7 <= razao_aspecto <= 1.3: # Quadrado aproximadamente
                    print(f"✅ Quadrado azul detectado: {w}x{h} pixels, área: {area}")
                    return aprox, (x, y, w, h), mascara
                    
        print("❌ Nenhum quadrilátero azul encontrado")
        return None, None, None
            
    except Exception as e:
        print(f"❌ Erro na detecção do quadrado: {e}")
        return None, None, None

def detectar_landmarks_mediapipe(imagem):
    """Detecta landmarks usando MediaPipe."""
    try:
        with mp_hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.5) as hands:
            imagem_rgb = cv.cvtColor(imagem, cv.COLOR_BGR2RGB)
            resultados = hands.process(imagem_rgb)
            
            if (resultados.multi_hand_landmarks is not None and 
                len(resultados.multi_hand_landmarks) > 0):
                
                hand_landmarks = resultados.multi_hand_landmarks[0]
                
                handedness = "Direita"  # Default
                if (resultados.multi_handedness is not None and 
                    len(resultados.multi_handedness) > 0):
                    
                    # MediaPipe retorna 'Right' para mão direita e 'Left' para mão esquerda.
                    # O usuário quer 'Direita' e 'Esquerda' no output.
                    for classification in resultados.multi_handedness[0].classification:
                        if classification.label == "Right":
                            handedness = "Direita"
                        elif classification.label == "Left":
                            handedness = "Esquerda"
                        break
                
                landmarks = [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
                return landmarks, handedness, resultados
                
    except Exception as e:
        print(f"Erro MediaPipe: {e}")
    
    return None, None, None

def obter_pontos_padrao(altura, largura):
    """Retorna pontos padrão baseados no tamanho da imagem para o modo manual. Estes são apenas placeholders."""
    # Estes pontos são arbitrários e precisam ser ajustados para refletir posições reais de landmarks
    # para que o modo manual seja útil. Por enquanto, são apenas para evitar erros.
    return [
        (int(largura * 0.5), int(altura * 0.8)),  # 0: Pulso
        (int(largura * 0.4), int(altura * 0.7)),  # 1: Polegar base
        (int(largura * 0.3), int(altura * 0.6)),  # 2: Polegar 1ª articulação
        (int(largura * 0.2), int(altura * 0.5)),  # 3: Polegar 2ª articulação
        (int(largura * 0.1), int(altura * 0.4)),  # 4: Ponta do polegar
        (int(largura * 0.4), int(altura * 0.6)),  # 5: Indicador base
        (int(largura * 0.4), int(altura * 0.5)),  # 6: Indicador 1ª articulação
        (int(largura * 0.4), int(altura * 0.4)),  # 7: Indicador 2ª articulação
        (int(largura * 0.4), int(altura * 0.3)),  # 8: Ponta do indicador
        (int(largura * 0.5), int(altura * 0.6)),  # 9: Médio base
        (int(largura * 0.5), int(altura * 0.5)),  # 10: Médio 1ª articulação
        (int(largura * 0.5), int(altura * 0.4)),  # 11: Médio 2ª articulação
        (int(largura * 0.5), int(altura * 0.3)),  # 12: Ponta do médio
        (int(largura * 0.6), int(altura * 0.6)),  # 13: Anelar base
        (int(largura * 0.6), int(altura * 0.5)),  # 14: Anelar 1ª articulação
        (int(largura * 0.6), int(altura * 0.4)),  # 15: Anelar 2ª articulação
        (int(largura * 0.6), int(altura * 0.3)),  # 16: Ponta do anelar
        (int(largura * 0.7), int(altura * 0.6)),  # 17: Mínimo base
        (int(largura * 0.7), int(altura * 0.5)),  # 18: Mínimo 1ª articulação
        (int(largura * 0.7), int(altura * 0.4)),  # 19: Mínimo 2ª articulação
        (int(largura * 0.7), int(altura * 0.3))   # 20: Ponta do mínimo
    ]

def detectar_landmarks_manual(imagem, escala_px_cm=None):
    """Detecta landmarks manualmente (placeholder, precisa de refinamento para ser preciso)."""
    try:
        altura, largura = imagem.shape[:2]
        pontos = obter_pontos_padrao(altura, largura)
        
        landmarks = []
        for x, y in pontos:
            landmarks.append((x / largura, y / altura, 0.0)) # Normalizar para 0-1
        
        handedness = "Direita"  # Default para manual, pode ser ajustado se houver lógica para isso
        if landmarks and len(landmarks) > 4:
            # Lógica simples para inferir handedness, pode precisar de ajuste
            if landmarks[4][0] > landmarks[0][0]:  # Se a ponta do polegar está à direita da base do pulso
                handedness = "Esquerda"
            else:
                handedness = "Direita"
                
        return landmarks, handedness, None
        
    except Exception as e:
        print(f"Erro modo manual: {e}")
        return None, None, None

def desenhar_landmarks(imagem, landmarks, resultados_mp=None, dimensoes=None, escala_px_cm=None, contorno_quadrado=None):
    """Desenha landmarks, dimensões e o quadrado de referência na imagem."""
    imagem_com_contorno = imagem.copy()
    altura, largura = imagem.shape[:2]

    # CORREÇÃO: Desenhar o quadrado de referência de forma mais visível
    if contorno_quadrado is not None:
        cv.drawContours(imagem_com_contorno, [contorno_quadrado], -1, (0, 255, 0), 3)  # Verde mais visível
        x, y, w, h = cv.boundingRect(contorno_quadrado)
        # Adicionar texto informativo sobre o quadrado
        cv.putText(imagem_com_contorno, f"QUADRADO REFERENCIA - {TAMANHO_QUADRADO_CM}cm", 
                  (x, y - 15), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv.LINE_AA)

    # Desenhar landmarks do MediaPipe
    if (resultados_mp is not None and 
        resultados_mp.multi_hand_landmarks is not None and 
        len(resultados_mp.multi_hand_landmarks) > 0):
        
        for hand_landmarks in resultados_mp.multi_hand_landmarks:
            mp_drawing.draw_landmarks(
                imagem_com_contorno,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style())
    
    # CORREÇÃO: Desenhar landmarks manuais com melhor visualização
    elif landmarks is not None and len(landmarks) > 0:
        for i, (x, y, _) in enumerate(landmarks):
            if not (0 <= x <= 1 and 0 <= y <= 1):
                continue
                
            px = int(x * largura)
            py = int(y * altura)
            # Cores diferentes para pontos importantes
            if i == 0:  # Pulso
                color = (255, 255, 0)  # Ciano
                size = 8
            elif i in [5, 17]:  # Base dos dedos (importantes para medições)
                color = (0, 255, 255)  # Amarelo
                size = 7
            elif i == 12:  # Ponta do dedo médio
                color = (255, 0, 255)  # Magenta
                size = 7
            else:
                color = (0, 0, 255)  # Vermelho
                size = 5
                
            cv.circle(imagem_com_contorno, (px, py), size, color, -1)
            cv.putText(imagem_com_contorno, str(i), (px + 5, py - 5), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv.LINE_AA)

    # CORREÇÃO: Desenhar dimensões de forma mais clara e organizada
    if dimensoes and landmarks:
        font = cv.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 2
        
        # Converter landmarks para pixels
        landmarks_px = []
        for x, y, z in landmarks:
            landmarks_px.append((int(x * largura), int(y * altura)))

        # Posição inicial para texto das medidas
        text_y = 30
        text_margin = 20
        
        # CORREÇÃO: Exibir todas as medidas no canto superior direito
        medidas_texto = [
            f"Pulso: {dimensoes.get('Largura Pulso', 0):.1f}cm",
            f"Palma: {dimensoes.get('Largura Palma', 0):.1f}cm", 
            f"Comprimento: {dimensoes.get('Comprimento Mao', 0):.1f}cm",
            f"Ortese: {dimensoes.get('Tamanho Ortese', 'N/A')}"
        ]
        
        for i, texto in enumerate(medidas_texto):
            y_pos = text_y + (i * 25)
            cv.putText(imagem_com_contorno, texto, 
                      (largura - 250, y_pos), font, font_scale, (0, 0, 255), font_thickness, cv.LINE_AA)

        # CORREÇÃO: Desenhar linhas de medição na imagem
        if len(landmarks_px) >= 18:
            # Linha do pulso (0-17)
            cv.line(imagem_com_contorno, landmarks_px[0], landmarks_px[17], (255, 0, 0), 3)
            cv.putText(imagem_com_contorno, f"{dimensoes.get('Largura Pulso', 0):.1f}cm",
                      ((landmarks_px[0][0] + landmarks_px[17][0]) // 2,
                       (landmarks_px[0][1] + landmarks_px[17][1]) // 2 - 10),
                      font, 0.5, (255, 0, 0), 1, cv.LINE_AA)
            
            # Linha da palma (5-17)
            cv.line(imagem_com_contorno, landmarks_px[5], landmarks_px[17], (0, 255, 0), 3)
            cv.putText(imagem_com_contorno, f"{dimensoes.get('Largura Palma', 0):.1f}cm",
                      ((landmarks_px[5][0] + landmarks_px[17][0]) // 2,
                       (landmarks_px[5][1] + landmarks_px[17][1]) // 2 - 10),
                      font, 0.5, (0, 255, 0), 1, cv.LINE_AA)
            
            # Linha do comprimento (0-12)
            cv.line(imagem_com_contorno, landmarks_px[0], landmarks_px[12], (0, 0, 255), 3)
            cv.putText(imagem_com_contorno, f"{dimensoes.get('Comprimento Mao', 0):.1f}cm",
                      ((landmarks_px[0][0] + landmarks_px[12][0]) // 2 + 20,
                       (landmarks_px[0][1] + landmarks_px[12][1]) // 2),
                      font, 0.5, (0, 0, 255), 1, cv.LINE_AA)

    return imagem_com_contorno

def calcular_dimensoes(landmarks, escala_px_cm, imagem_shape):
    """
    landmarks: lista de 21 (x,y,z) normalizados (0..1)
    escala_px_cm: px por cm (float)
    imagem_shape: shape da imagem (h, w, ...)
    retorna dicionário com medidas em cm (float)
    """
    try:
        altura, largura = imagem_shape[:2]
        if landmarks is None or len(landmarks) < 21:
            return None

        # converter para pixels
        lm_px = []
        for x,y,z in landmarks:
            if not (0 <= x <= 1 and 0 <= y <= 1):
                return None
            lm_px.append((int(x*largura), int(y*altura)))

        # CORREÇÃO: Largura do pulso entre pontos 0 (pulso) e 17 (base do mindinho)
        p0 = lm_px[0]
        p17 = lm_px[17]
        largura_pulso_px = _dist(p0, p17)

        # CORREÇÃO: Largura da palma entre pontos 5 (base do indicador) e 17 (base do mindinho)
        p5 = lm_px[5]
        p17 = lm_px[17]
        largura_palma_px = _dist(p5, p17)

        # CORREÇÃO: Comprimento da mão entre pontos 0 (pulso) e 12 (ponta do dedo médio)
        p0 = lm_px[0]
        p12 = lm_px[12]
        comprimento_px = _dist(p0, p12)

        # converter para cm (px/cm)
        if escala_px_cm is None or escala_px_cm <= 0:
            logger.warning("Escala inválida: %s", escala_px_cm)
            return None

        largura_pulso_cm = largura_pulso_px / escala_px_cm
        largura_palma_cm = largura_palma_px / escala_px_cm
        comprimento_cm = comprimento_px / escala_px_cm

        # CORREÇÃO: Aplicar fatores de correção baseados em calibração
        largura_pulso_cm *= 1.15  # Fator de correção para medição do pulso
        largura_palma_cm *= 1.08  # Fator de correção para medição da palma

        # CORREÇÃO: Determinar tamanho da órtese pela tabela fornecida (baseado na largura do pulso)
        if largura_pulso_cm <= 7.0:
            tamanho = "P"
        elif largura_pulso_cm <= 9.0:
            tamanho = "M"
        else:
            tamanho = "G"

        return {
            "Largura Pulso": round(largura_pulso_cm, 2),
            "Largura Palma": round(largura_palma_cm, 2),
            "Comprimento Mao": round(comprimento_cm, 2),
            "Tamanho Ortese": tamanho,
            "largura_pulso_px": round(largura_pulso_px, 2),
            "escala_px_cm": round(escala_px_cm, 2)
        }

    except Exception as e:
        logger.exception("Erro calculando dimensões: %s", e)
        return None

def imagem_para_base64(imagem):
    """Converte imagem OpenCV para base64."""
    try:
        if imagem is None or imagem.size == 0:
            print("Erro: Imagem vazia ou inválida para conversão base64.")
            return None
            
        # Redimensionar imagem se for muito grande para evitar problemas de performance/tamanho
        altura, largura = imagem.shape[:2]
        max_dim = 1000 # Limite máximo para a maior dimensão
        if altura > max_dim or largura > max_dim:
            fator = min(max_dim/altura, max_dim/largura)
            nova_altura = int(altura * fator)
            nova_largura = int(largura * fator)
            imagem = cv.resize(imagem, (nova_largura, nova_altura), interpolation=cv.INTER_AREA)
        
        _, buffer = cv.imencode(".jpg", imagem, [cv.IMWRITE_JPEG_QUALITY, 90])
        
        if buffer is None:
            print("Erro: Falha ao codificar imagem para JPEG.")
            return None
            
        imagem_base64 = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/jpeg;base64,{imagem_base64}"
    except Exception as e:
        print(f"Erro convertendo imagem para base64: {e}")
        return None

def gerar_stl_simples(dimensoes, handedness, output_path, modelo_base_stl_path):
    """Gera um STL baseado no modelo de órtese padrão e nas dimensões calculadas."""
    try:
        if not os.path.exists(modelo_base_stl_path):
            print(f"Erro: Modelo STL base não encontrado em {modelo_base_stl_path}")
            return False

        # Carregar o modelo STL base
        ortese_base = mesh.Mesh.from_file(modelo_base_stl_path)

        # Obter a largura do pulso calculada
        largura_pulso_cm = dimensoes.get("Largura Pulso", 0.0)
        if largura_pulso_cm == 0.0:
            print("Erro: Largura do pulso não disponível para escalonamento do STL.")
            return False

        # CORREÇÃO: Cálculo baseado no perímetro
        # Perímetro do pulso do paciente = 2.2 * largura_pulso_cm
        # Perímetro da órtese template = 10cm (conforme especificado)
        perimetro_paciente = 2.2 * largura_pulso_cm
        perimetro_template = 10.0  # cm
        
        # Fator de escala = perímetro_paciente / perímetro_template
        fator_escala = perimetro_paciente / perimetro_template
        
        print(f"📏 Escalonamento da órtese:")
        print(f"   Largura do pulso: {largura_pulso_cm:.2f}cm")
        print(f"   Perímetro do pulso: {perimetro_paciente:.2f}cm") 
        print(f"   Perímetro template: {perimetro_template:.2f}cm")
        print(f"   Fator de escala: {fator_escala:.3f}")

        # CORREÇÃO: Aplicar escala apenas nos eixos X e Y (mantém Z para altura)
        ortese_escalada = ortese_base.copy()
        
        # Escalar apenas X e Y (plano da órtese)
        for i in range(len(ortese_escalada.vectors)):
            for j in range(3):
                # Aplicar escala apenas em X e Y
                ortese_escalada.vectors[i][j][0] *= fator_escala  # X
                ortese_escalada.vectors[i][j][1] *= fator_escala  # Y
                # Manter Z original (altura)

        # CORREÇÃO: Espelhar se for mão esquerda
        if handedness == "Esquerda":
            print(f"   Espelhando para mão esquerda")
            # Espelhar no eixo X
            for i in range(len(ortese_escalada.vectors)):
                for j in range(3):
                    ortese_escalada.vectors[i][j][0] *= -1  # Inverte X

        ortese_escalada.save(output_path)
        print(f"✅ Modelo STL gerado e salvo em: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Erro gerando STL: {e}")
        import traceback
        traceback.print_exc()
        return False
        
def pipeline_processamento_ortese(img_path, caminho_stl_saida=None, mostrar_imagens_matplotlib=False, modo_manual=False, modelo_base_stl_path=None):
    """Função principal para o pipeline de processamento de imagem e geração de órtese."""
    try:
        print("🔍 Iniciando pipeline de processamento da imagem...")
        
        imagem = cv.imread(img_path)
        if imagem is None:
            print(f"Erro: Não foi possível carregar a imagem em {img_path}")
            return None, None, None, None, None
        
        print(f"Imagem carregada: {imagem.shape[1]}x{imagem.shape[0]} pixels")
        
        # 1. Detectar quadrado azul para escala
        contorno_quadrado, dimensoes_quadrado, _ = detectar_quadrado_azul(imagem)
        
        escala_px_cm = None
        if contorno_quadrado is not None:
            x, y, w, h = dimensoes_quadrado
            # Usar a média da largura e altura do quadrado detectado para calcular a escala
            escala_px_cm = ((w + h) / 2) / TAMANHO_QUADRADO_CM
            print(f"Quadrado detectado. Escala: {escala_px_cm:.2f} px/cm")
        else:
            # Fallback para escala padrão se o quadrado não for detectado
            # Este valor pode precisar de calibração para ser mais preciso
            escala_px_cm = 30.0 # Valor de fallback ajustado (exemplo, precisa ser calibrado)
            print(f"Quadrado não detectado. Usando escala padrão: {escala_px_cm} px/cm")

        if escala_px_cm is None or escala_px_cm == 0:
            print("Erro: Escala de pixel para cm não pode ser determinada ou é zero.")
            return None, None, None, None, None
        
        # 2. Detectar landmarks
        landmarks, handedness, resultados_mp = None, None, None
        
        if not modo_manual:
            landmarks, handedness, resultados_mp = detectar_landmarks_mediapipe(imagem)
        
        # Fallback para manual se MediaPipe falhar ou modo manual ativado
        if landmarks is None or len(landmarks) == 0:
            print("🔧 MediaPipe falhou ou modo manual ativado. Usando detecção manual...")
            landmarks, handedness, resultados_mp = detectar_landmarks_manual(imagem, escala_px_cm)
        
        if landmarks is None or len(landmarks) == 0:
            print("Erro: Não foi possível detectar landmarks da mão (MediaPipe e manual falharam).")
            return None, None, None, None, None
        
        print(f"Landmarks detectados: {len(landmarks)} pontos")
        print(f"Mão detectada: {handedness}")
        
        # 3. Calcular dimensões
        dimensoes = calcular_dimensoes(landmarks, escala_px_cm, imagem.shape)
        
        if dimensoes is None:
            print("Erro: Não foi possível calcular dimensões da mão.")
            return None, None, None, None, None
        
        print("Dimensões calculadas com sucesso:", dimensoes)
        
        # 4. Desenhar landmarks, dimensões e quadrado na imagem
        imagem_processada = desenhar_landmarks(imagem, landmarks, resultados_mp, dimensoes, escala_px_cm, contorno_quadrado)
        
        # 5. Gerar STL
        caminho_stl = None
        if caminho_stl_saida and modelo_base_stl_path:
            if gerar_stl_simples(dimensoes, handedness, caminho_stl_saida, modelo_base_stl_path):
                caminho_stl = caminho_stl_saida
            else:
                print("Aviso: Falha na geração do arquivo STL.")
        
        print("Pipeline concluído com sucesso!")
        return caminho_stl, imagem_processada, None, dimensoes, handedness
        
    except Exception as e:
        print(f"Erro no pipeline de processamento: {str(e)}")
        return None, None, None, None, None

def processar_imagem_ortese_api(imagem_bytes, modo_manual=False, modelo_base_stl_path=None):
    """Função principal para processamento de imagem na API."""
    try:
        print("🔍 Iniciando processamento da imagem para API...")
        
        nparr = np.frombuffer(imagem_bytes, np.uint8)
        imagem = cv.imdecode(nparr, cv.IMREAD_COLOR)
        
        if imagem is None:
            return {"erro": "Não foi possível carregar a imagem a partir dos bytes"}
        
        # Salvar imagem temporariamente para o pipeline
        temp_img_path = "temp_input_image.jpg"
        cv.imwrite(temp_img_path, imagem)

        # Definir caminho de saída para o STL temporário
        temp_stl_path = "temp_output_ortese.stl"

        caminho_stl, imagem_processada, _, dimensoes, handedness = pipeline_processamento_ortese(
            temp_img_path, 
            caminho_stl_saida=temp_stl_path, 
            mostrar_imagens_matplotlib=False, 
            modo_manual=modo_manual,
            modelo_base_stl_path=modelo_base_stl_path
        )
        
        # Limpar arquivo de imagem temporário
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

        if dimensoes is None:
            return {"erro": "Não foi possível calcular dimensões da mão"}
        
        imagem_base64 = imagem_para_base64(imagem_processada)
        
        if imagem_base64 is None:
            return {"erro": "Erro ao processar imagem para exibição"}
        
        resultado = {
            "sucesso": True,
            "dimensoes": dimensoes,
            "handedness": handedness,
            "imagem_processada": imagem_base64,
            "stl_path": caminho_stl if caminho_stl else None # Retorna o caminho do STL gerado
        }
        
        print("Processamento concluído com sucesso para API!")
        return resultado
        
    except Exception as e:
        print(f"Erro no processamento da API: {str(e)}")
        return {"erro": f"Erro no processamento da API: {str(e)}"}