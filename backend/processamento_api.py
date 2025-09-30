import cv2 as cv
import numpy as np
import mediapipe as mp
import base64
from stl import mesh
import os

# Configurações
TAMANHO_QUADRADO_CM = 6.0
LOWER_BLUE = np.array([75, 80, 50])
UPPER_BLUE = np.array([140, 255, 255])

# Inicializar MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

def detectar_quadrado_azul(imagem):
    """Detecta quadrado azul na imagem e retorna o contorno, dimensões e a máscara."""
    try:
        imagem_hsv = cv.cvtColor(imagem, cv.COLOR_BGR2HSV)
        mascara = cv.inRange(imagem_hsv, LOWER_BLUE, UPPER_BLUE)
        
        kernel = np.ones((7, 7), np.uint8)
        mascara = cv.morphologyEx(mascara, cv.MORPH_OPEN, kernel, iterations=2)
        mascara = cv.morphologyEx(mascara, cv.MORPH_CLOSE, kernel, iterations=2)
        
        contornos, _ = cv.findContours(mascara, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        
        if contornos is None or len(contornos) == 0:
            return None, None, None
        
        for contorno in contornos:
            area = cv.contourArea(contorno)
            if area < 500: # Ignorar contornos muito pequenos
                continue
                
            perimetro = cv.arcLength(contorno, True)
            aprox = cv.approxPolyDP(contorno, 0.02 * perimetro, True)
            
            if len(aprox) == 4: # Procurar por formas com 4 vértices (quadriláteros)
                x, y, w, h = cv.boundingRect(aprox)
                razao_aspecto = float(w) / h
                
                if 0.8 <= razao_aspecto <= 1.2: # Verificar se é aproximadamente um quadrado
                    return aprox, (x, y, w, h), mascara
                    
    except Exception as e:
        print(f"Erro na detecção do quadrado: {e}")
    
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

    # Desenhar o quadrado de referência se detectado
    if contorno_quadrado is not None:
        cv.drawContours(imagem_com_contorno, [contorno_quadrado], -1, (0, 255, 255), 3) # Amarelo
        x, y, w, h = cv.boundingRect(contorno_quadrado)
        cv.putText(imagem_com_contorno, f"Ref: {TAMANHO_QUADRADO_CM}cm", (x, y - 10), 
                   cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv.LINE_AA)

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
    
    # Desenhar landmarks manuais (se MediaPipe não for usado ou falhar)
    elif landmarks is not None and len(landmarks) > 0:
        for i, (x, y, _) in enumerate(landmarks):
            if not (0 <= x <= 1 and 0 <= y <= 1):
                continue
                
            px = int(x * largura)
            py = int(y * altura)
            color = (0, 0, 255) if i != 0 else (255, 255, 0) # Vermelho para outros, Azul para o primeiro
            cv.circle(imagem_com_contorno, (px, py), 5, color, -1)
        
        # Desenhar conexões básicas para landmarks manuais
        conexoes = [
            (0, 1), (1, 2), (2, 3), (3, 4), # Polegar
            (0, 5), (5, 6), (6, 7), (7, 8), # Indicador
            (9, 10), (10, 11), (11, 12), # Médio
            (13, 14), (14, 15), (15, 16), # Anelar
            (17, 18), (18, 19), (19, 20), # Mínimo
            (5, 9), (9, 13), (13, 17), (0, 17) # Palma e pulso
        ]
        
        for inicio, fim in conexoes:
            if (inicio < len(landmarks) and fim < len(landmarks) and
                landmarks[inicio] is not None and landmarks[fim] is not None):
                
                x1, y1, _ = landmarks[inicio]
                x2, y2, _ = landmarks[fim]
                
                if not (0 <= x1 <= 1 and 0 <= y1 <= 1 and 0 <= x2 <= 1 and 0 <= y2 <= 1):
                    continue
                    
                px1 = int(x1 * largura)
                py1 = int(y1 * altura)
                px2 = int(x2 * largura)
                py2 = int(y2 * altura)
                cv.line(imagem_com_contorno, (px1, py1), (px2, py2), (0, 255, 0), 2)

    # Desenhar dimensões na imagem
    if dimensoes and escala_px_cm:
        font = cv.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        font_thickness = 2
        color = (255, 0, 0) # Azul

        # Converter landmarks para pixels para posicionamento do texto
        landmarks_px = []
        for x, y, z in landmarks:
            landmarks_px.append((int(x * largura), int(y * altura)))

        # Largura do Pulso
        if "Largura Pulso" in dimensoes and len(landmarks_px) > 17:
            p0 = landmarks_px[0]
            p17 = landmarks_px[17]
            mid_x, mid_y = (p0[0] + p17[0]) // 2, (p0[1] + p17[1]) // 2
            cv.putText(imagem_com_contorno, f"Pulso: {dimensoes['Largura Pulso']:.2f}cm", 
                       (mid_x - 50, mid_y - 20), font, font_scale, color, font_thickness, cv.LINE_AA)
            cv.line(imagem_com_contorno, p0, p17, color, 2)

        # Largura da Palma (entre 5 e 17, ou 5 e 9, ou 9 e 13, etc. - vamos usar 5 e 17 como no cálculo)
        if "Largura Palma" in dimensoes and len(landmarks_px) > 17 and len(landmarks_px) > 5:
            p5 = landmarks_px[5]
            p17 = landmarks_px[17]
            mid_x, mid_y = (p5[0] + p17[0]) // 2, (p5[1] + p17[1]) // 2
            cv.putText(imagem_com_contorno, f"Palma: {dimensoes['Largura Palma']:.2f}cm", 
                       (mid_x - 50, mid_y + 20), font, font_scale, color, font_thickness, cv.LINE_AA)
            cv.line(imagem_com_contorno, p5, p17, color, 2)

        # Comprimento da Mão (entre 0 e 12)
        if "Comprimento Mão" in dimensoes and len(landmarks_px) > 12:
            p0 = landmarks_px[0]
            p12 = landmarks_px[12]
            mid_x, mid_y = (p0[0] + p12[0]) // 2, (p0[1] + p12[1]) // 2
            cv.putText(imagem_com_contorno, f"Comp. Mão: {dimensoes['Comprimento Mão']:.2f}cm", 
                       (mid_x + 20, mid_y), font, font_scale, color, font_thickness, cv.LINE_AA)
            cv.line(imagem_com_contorno, p0, p12, color, 2)

    return imagem_com_contorno

def calcular_dimensoes(landmarks, escala_px_cm, imagem_shape):
    """Calcula dimensões da mão com base nos landmarks e escala."""
    try:
        altura, largura = imagem_shape[:2]
        
        if landmarks is None or len(landmarks) < 21:
            print("Erro: Landmarks insuficientes para calcular dimensões.")
            return None
        
        # Converter landmarks normalizados (0-1) para coordenadas de pixel
        landmarks_px = []
        for lm in landmarks:
            # Certificar-se de que lm é uma tupla/lista com pelo menos 2 elementos (x, y)
            if len(lm) < 2:
                print(f"Erro: Landmark com formato inválido: {lm}")
                return None
            x_px = int(lm[0] * largura)
            y_px = int(lm[1] * altura)
            landmarks_px.append((x_px, y_px))
        
        # Medições baseadas nos landmarks do MediaPipe (indices)
        # Pulso: ponto 0 (base do pulso) e ponto 17 (base do dedo mínimo)
        # A largura do pulso é geralmente medida entre os ossos ulna e rádio, 
        # mas para uma foto 2D, a distância entre o ponto 0 e 17 do MediaPipe é uma boa aproximação.
        p0 = np.array(landmarks_px[mp_hands.HandLandmark.WRIST.value])
        p17 = np.array(landmarks_px[mp_hands.HandLandmark.PINKY_MCP.value]) # Base do dedo mínimo
        largura_pulso_px = np.linalg.norm(p0 - p17)
        largura_pulso_cm = largura_pulso_px / escala_px_cm
        
        # Largura da Palma: entre a base do indicador (ponto 5) e a base do mínimo (ponto 17)
        p5 = np.array(landmarks_px[mp_hands.HandLandmark.INDEX_FINGER_MCP.value]) # Base do dedo indicador
        largura_palma_px = np.linalg.norm(p5 - p17)
        largura_palma_cm = largura_palma_px / escala_px_cm
        
        # Comprimento da Mão: do pulso (ponto 0) até a ponta do dedo médio (ponto 12)
        p12 = np.array(landmarks_px[mp_hands.HandLandmark.MIDDLE_FINGER_TIP.value]) # Ponta do dedo médio
        comprimento_mao_px = np.linalg.norm(p0 - p12)
        comprimento_mao_cm = comprimento_mao_px / escala_px_cm
        
        # Fatores de correção (ajustar conforme a necessidade para maior precisão)
        largura_pulso_cm *= 1.05 # Ajuste experimental
        largura_palma_cm *= 1.05 # Ajuste experimental
        comprimento_mao_cm *= 1.05 # Ajuste experimental
        
        # Determinar tamanho da órtese com base na largura do pulso (conforme tabela do usuário)
        tamanho_ortese = "Desconhecido"
        if 5.0 <= largura_pulso_cm <= 7.0:
            tamanho_ortese = "P"
        elif 7.1 <= largura_pulso_cm <= 9.0:
            tamanho_ortese = "M"
        elif 9.1 <= largura_pulso_cm <= 11.0:
            tamanho_ortese = "G"
        elif largura_pulso_cm < 5.0:
            tamanho_ortese = "PP"
        elif largura_pulso_cm > 11.0:
            tamanho_ortese = "GG"

        return {
            "Largura Pulso": round(largura_pulso_cm, 2),
            "Largura Palma": round(largura_palma_cm, 2),
            "Comprimento Mão": round(comprimento_mao_cm, 2),
            "Tamanho Órtese": tamanho_ortese
        }
        
    except Exception as e:
        print(f"Erro calculando dimensões: {e}")
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

        # O centro do modelo 3D é 2.2x a medida do pulso encontrada.
        # Isso implica que a órtese base tem uma largura de pulso de referência.
        # Precisamos encontrar a largura do pulso do modelo base para calcular o fator de escala.
        # Para simplificar, vamos assumir que o modelo base tem uma largura de pulso de 7cm (tamanho M de referência).
        # Este valor pode precisar ser ajustado com base nas dimensões reais do modelo wristband_2.0(1).stl.
        largura_pulso_base_cm = 7.0 # Assumindo uma largura de pulso de 7cm para o modelo base
        
        # Calcular o fator de escala para a largura do pulso
        # O fator de escala deve ser aplicado de forma que a largura do pulso do modelo escalado
        # seja 2.2 * largura_pulso_cm.
        # Se o modelo base tem largura_pulso_base_cm, e queremos que o resultado seja target_width,
        # então fator_escala = target_width / largura_pulso_base_cm
        target_width_cm = 2.2 * largura_pulso_cm
        fator_escala = target_width_cm / largura_pulso_base_cm

        # Aplicar o fator de escala ao modelo
        # A escala deve ser aplicada uniformemente em X, Y e Z para manter a proporção, 
        # a menos que haja uma necessidade específica de escalonamento não uniforme.
        # Para órteses, geralmente queremos manter a proporção geral, mas ajustar o tamanho.
        ortese_escalada = ortese_base.copy()
        ortese_escalada.vectors *= fator_escala

        # Espelhar se for mão esquerda (se o modelo base for para a mão direita)
        # Isso depende de como o modelo base foi criado. Se ele é simétrico ou se é específico para uma mão.
        # Para um wristband, pode não ser necessário espelhar, mas se for uma órtese mais complexa, sim.
        # Por enquanto, manter a lógica de espelhamento se o modelo base for assimétrico e para a mão direita.
        if handedness == "Esquerda":
            # Espelhar ao longo do eixo Y (ou X, dependendo da orientação do modelo)
            # Isso pode precisar de ajuste fino dependendo da orientação do modelo STL.
            ortese_escalada.vectors[:, :, 1] *= -1 # Espelha a coordenada Y
            # Pode ser necessário ajustar a posição após o espelhamento para centralizar
            # ortese_escalada.x += ortese_escalada.x.max() - ortese_escalada.x.min()

        ortese_escalada.save(output_path)
        print(f"Modelo STL gerado e salvo em: {output_path}")
        return True
        
    except Exception as e:
        print(f"Erro gerando STL: {e}")
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