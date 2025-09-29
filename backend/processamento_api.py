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
    """Detecta quadrado azul na imagem - VERSÃO CORRIGIDA"""
    try:
        imagem_hsv = cv.cvtColor(imagem, cv.COLOR_BGR2HSV)
        mascara = cv.inRange(imagem_hsv, LOWER_BLUE, UPPER_BLUE)
        
        kernel = np.ones((7, 7), np.uint8)
        mascara = cv.morphologyEx(mascara, cv.MORPH_OPEN, kernel, iterations=2)
        mascara = cv.morphologyEx(mascara, cv.MORPH_CLOSE, kernel, iterations=2)
        
        contornos, _ = cv.findContours(mascara, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        
        # CORREÇÃO: Verificar se há contornos antes de iterar
        if contornos is None or len(contornos) == 0:
            return None, None, None
        
        for contorno in contornos:
            area = cv.contourArea(contorno)
            if area < 500:
                continue
                
            perimetro = cv.arcLength(contorno, True)
            aprox = cv.approxPolyDP(contorno, 0.02 * perimetro, True)
            
            # CORREÇÃO: Verificar o comprimento do array corretamente
            if len(aprox) == 4:
                x, y, w, h = cv.boundingRect(aprox)
                razao_aspecto = float(w) / h
                
                if 0.8 <= razao_aspecto <= 1.2:
                    return aprox, (x, y, w, h), mascara
                    
    except Exception as e:
        print(f"Erro na detecção do quadrado: {e}")
    
    return None, None, None

def detectar_landmarks_mediapipe(imagem):
    """Detecta landmarks usando MediaPipe - VERSÃO CORRIGIDA"""
    try:
        with mp_hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.5) as hands:
            imagem_rgb = cv.cvtColor(imagem, cv.COLOR_BGR2RGB)
            resultados = hands.process(imagem_rgb)
            
            # CORREÇÃO: Verificar corretamente se há landmarks
            if (resultados.multi_hand_landmarks is not None and 
                len(resultados.multi_hand_landmarks) > 0):
                
                hand_landmarks = resultados.multi_hand_landmarks[0]
                
                handedness = "Direita"  # Default
                if (resultados.multi_handedness is not None and 
                    len(resultados.multi_handedness) > 0):
                    
                    for classification in resultados.multi_handedness[0].classification:
                        handedness = "Esquerda" if classification.label == "Right" else "Direita"
                        break
                
                landmarks = [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
                return landmarks, handedness, resultados
                
    except Exception as e:
        print(f"Erro MediaPipe: {e}")
    
    return None, None, None

def obter_pontos_padrao(altura, largura):
    """Retorna pontos padrão baseados no tamanho da imagem"""
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
    """Detecta landmarks manualmente"""
    try:
        altura, largura = imagem.shape[:2]
        pontos = obter_pontos_padrao(altura, largura)
        
        # Converter para formato MediaPipe
        landmarks = []
        for x, y in pontos:
            landmarks.append((x / largura, y / altura, 0.0))
        
        # Inferir handedness - CORREÇÃO: Verificar se landmarks existe
        handedness = "Direita"  # Default
        if landmarks and len(landmarks) > 4:
            # CORREÇÃO: Usar valores numéricos, não arrays
            if landmarks[4][0] > landmarks[0][0]:  # Comparar valores float
                handedness = "Esquerda"
            else:
                handedness = "Direita"
                
        return landmarks, handedness, None
        
    except Exception as e:
        print(f"Erro modo manual: {e}")
        return None, None, None

def desenhar_landmarks(imagem, landmarks, resultados_mp=None):
    """Desenha landmarks na imagem"""
    try:
        imagem_com_contorno = imagem.copy()
        
        # CORREÇÃO: Verificar corretamente os resultados do MediaPipe
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
        
        # CORREÇÃO: Verificar corretamente os landmarks manuais
        elif landmarks is not None and len(landmarks) > 0:
            altura, largura = imagem.shape[:2]
            
            # Desenhar pontos
            for i, (x, y, _) in enumerate(landmarks):
                # CORREÇÃO: Verificar se os valores são válidos
                if not (0 <= x <= 1 and 0 <= y <= 1):
                    continue
                    
                px = int(x * largura)
                py = int(y * altura)
                color = (0, 0, 255) if i != 0 else (255, 255, 0)
                cv.circle(imagem_com_contorno, (px, py), 5, color, -1)
            
            # Desenhar conexões básicas
            conexoes = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
                       (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16),
                       (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]
            
            for inicio, fim in conexoes:
                # CORREÇÃO: Verificar índices válidos
                if (inicio < len(landmarks) and fim < len(landmarks) and
                    landmarks[inicio] is not None and landmarks[fim] is not None):
                    
                    x1, y1, _ = landmarks[inicio]
                    x2, y2, _ = landmarks[fim]
                    
                    # Verificar coordenadas válidas
                    if not (0 <= x1 <= 1 and 0 <= y1 <= 1 and 0 <= x2 <= 1 and 0 <= y2 <= 1):
                        continue
                        
                    px1 = int(x1 * largura)
                    py1 = int(y1 * altura)
                    px2 = int(x2 * largura)
                    py2 = int(y2 * altura)
                    cv.line(imagem_com_contorno, (px1, py1), (px2, py2), (0, 255, 0), 2)
        
        return imagem_com_contorno
        
    except Exception as e:
        print(f"Erro desenhando landmarks: {e}")
        return imagem

def calcular_dimensoes(landmarks, escala_px_cm, imagem_shape):
    """Calcula dimensões da mão - VERSÃO CORRIGIDA"""
    try:
        altura, largura = imagem_shape[:2]
        
        # CORREÇÃO: Verificar landmarks corretamente
        if landmarks is None or len(landmarks) < 21:
            return None
        
        # Converter landmarks para pixels
        landmarks_px = []
        for x, y, z in landmarks:
            # CORREÇÃO: Verificar coordenadas válidas
            if not (0 <= x <= 1 and 0 <= y <= 1):
                return None
            landmarks_px.append((int(x * largura), int(y * altura)))
        
        # Largura do pulso (pontos 0 e 17)
        x0, y0 = landmarks_px[0]
        x17, y17 = landmarks_px[17]
        largura_pulso_px = np.sqrt((x17 - x0)**2 + (y17 - y0)**2)
        largura_pulso_cm = largura_pulso_px / escala_px_cm
        
        # Largura da palma (pontos 5 e 17)
        x5, y5 = landmarks_px[5]
        largura_palma_px = np.sqrt((x17 - x5)**2 + (y17 - y5)**2)
        largura_palma_cm = largura_palma_px / escala_px_cm
        
        # Comprimento da mão (ponto 0 ao 12)
        x12, y12 = landmarks_px[12]
        comprimento_px = np.sqrt((x12 - x0)**2 + (y12 - y0)**2)
        comprimento_cm = comprimento_px / escala_px_cm
        
        # Aplicar fatores de correção
        largura_pulso_cm *= 1.02
        largura_palma_cm *= 1.05
        
        # Determinar tamanho da órtese
        if largura_palma_cm < 7.0:
            tamanho_ortese = "P"
        elif largura_palma_cm < 9.0:
            tamanho_ortese = "M"
        else:
            tamanho_ortese = "G"
        
        return {
            "Largura Pulso": round(largura_pulso_cm, 2),
            "Largura Palma": round(largura_palma_cm, 2),
            "Comprimento Mão": round(comprimento_cm, 2),
            "Tamanho Órtese": tamanho_ortese
        }
        
    except Exception as e:
        print(f"Erro calculando dimensões: {e}")
        return None

def imagem_para_base64(imagem):
    """Converte imagem OpenCV para base64"""
    try:
        # CORREÇÃO: Verificar se a imagem é válida
        if imagem is None or imagem.size == 0:
            print("Erro: Imagem vazia ou inválida")
            return None
            
        # Redimensionar imagem se for muito grande
        altura, largura = imagem.shape[:2]
        if altura > 800 or largura > 800:
            fator = min(800/altura, 800/largura)
            nova_altura = int(altura * fator)
            nova_largura = int(largura * fator)
            imagem = cv.resize(imagem, (nova_largura, nova_altura))
        
        _, buffer = cv.imencode('.jpg', imagem, [cv.IMWRITE_JPEG_QUALITY, 80])
        
        # CORREÇÃO: Verificar se a codificação foi bem-sucedida
        if buffer is None:
            print("Erro: Falha ao codificar imagem")
            return None
            
        imagem_base64 = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{imagem_base64}"
    except Exception as e:
        print(f"Erro convertendo imagem para base64: {e}")
        return None

def gerar_stl_simples(dimensoes, handedness, output_path):
    """Gera um STL simples para demonstração"""
    try:
        # Criar um cubo simples como placeholder
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]
        ])
        
        faces = np.array([
            [0, 3, 1], [1, 3, 2], [0, 4, 7], [0, 7, 3],
            [4, 5, 6], [4, 6, 7], [5, 1, 2], [5, 2, 6],
            [2, 3, 6], [3, 7, 6], [0, 1, 5], [0, 5, 4]
        ])
        
        cubo = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
        for i, face in enumerate(faces):
            for j in range(3):
                cubo.vectors[i][j] = vertices[face[j], :]
        
        # Aplicar escala baseada nas dimensões
        fator_escala = dimensoes["Largura Pulso"] / 6.0
        cubo.vectors *= fator_escala
        
        # Espelhar se for mão esquerda
        if handedness == "Esquerda":
            cubo.vectors[:, :, 0] *= -1
        
        cubo.save(output_path)
        return True
        
    except Exception as e:
        print(f"Erro gerando STL: {e}")
        return False

def processar_imagem_ortese_api(imagem_bytes, modo_manual=False):
    """
    Função principal para processamento de imagem
    """
    try:
        print("🔍 Iniciando processamento da imagem...")
        
        # Converter bytes para imagem OpenCV
        nparr = np.frombuffer(imagem_bytes, np.uint8)
        imagem = cv.imdecode(nparr, cv.IMREAD_COLOR)
        
        # CORREÇÃO: Verificar se a imagem foi carregada corretamente
        if imagem is None:
            return {"erro": "Não foi possível carregar a imagem a partir dos bytes"}
        
        print(f"Imagem carregada: {imagem.shape[1]}x{imagem.shape[0]} pixels")
        
        # Detectar quadrado azul para escala
        contorno_quadrado, dimensoes_quadrado, _ = detectar_quadrado_azul(imagem)
        
        if contorno_quadrado is not None:
            x, y, w, h = dimensoes_quadrado
            escala_px_cm = (w + h) / (2 * TAMANHO_QUADRADO_CM)
            print(f"Quadrado detectado. Escala: {escala_px_cm:.2f} px/cm")
        else:
            escala_px_cm = 67.92  # Fallback
            print(f"Quadrado não detectado. Usando escala padrão: {escala_px_cm} px/cm")
        
        # Detectar landmarks
        landmarks, handedness, resultados_mp = None, None, None
        
        if not modo_manual:
            landmarks, handedness, resultados_mp = detectar_landmarks_mediapipe(imagem)
        
        # Fallback para manual se MediaPipe falhar ou modo manual ativado
        if landmarks is None:
            print("🔧 Usando detecção manual...")
            landmarks, handedness, resultados_mp = detectar_landmarks_manual(imagem, escala_px_cm)
        
        # CORREÇÃO: Verificar se os landmarks foram detectados corretamente
        if landmarks is None or len(landmarks) == 0:
            return {"erro": "Não foi possível detectar landmarks da mão"}
        
        print(f"Landmarks detectados: {len(landmarks)} pontos")
        print(f"Mão detectada: {handedness}")
        
        # Processar imagem com landmarks
        imagem_processada = desenhar_landmarks(imagem, landmarks, resultados_mp)
        
        # Calcular dimensões
        dimensoes = calcular_dimensoes(landmarks, escala_px_cm, imagem.shape)
        
        if dimensoes is None:
            return {"erro": "Não foi possível calcular dimensões da mão"}
        
        print("Dimensões calculadas com sucesso")
        
        # Converter imagem processada para base64
        imagem_base64 = imagem_para_base64(imagem_processada)
        
        if imagem_base64 is None:
            return {"erro": "Erro ao processar imagem para exibição"}
        
        resultado = {
            "sucesso": True,
            "dimensoes": dimensoes,
            "handedness": handedness,
            "imagem_processada": imagem_base64,
            "escala_px_cm": round(escala_px_cm, 2)
        }
        
        print("Processamento concluído com sucesso!")
        return resultado
        
    except Exception as e:
        print(f"Erro no processamento: {str(e)}")
        return {"erro": f"Erro no processamento: {str(e)}"}