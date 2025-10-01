import cv2 as cv
import numpy as np
import mediapipe as mp
from stl import mesh
import os
import math

# Configurações globais
DEBUG = True
TAMANHO_QUADRADO_CM = 6.0

# Configurações para detecção do quadrado azul (ajustadas para QR code sem fundo)
LOWER_BLUE = np.array([90, 80, 50])   # Azul mais escuro
UPPER_BLUE = np.array([130, 255, 255]) # Azul mais claro

# Inicializar MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

def detectar_quadrado_azul_melhorado(imagem, debug=False):
    """
    Detecção melhorada do quadrado azul que ignora o QR code
    """
    try:
        imagem_hsv = cv.cvtColor(imagem, cv.COLOR_BGR2HSV)
        
        # Criar máscara para azul
        mascara = cv.inRange(imagem_hsv, LOWER_BLUE, UPPER_BLUE)
        
        # Operações morfológicas mais agressivas para fechar buracos do QR code
        kernel_grande = np.ones((15, 15), np.uint8)
        kernel_pequeno = np.ones((5, 5), np.uint8)
        
        # Fechamento para preencher o QR code
        mascara = cv.morphologyEx(mascara, cv.MORPH_CLOSE, kernel_grande, iterations=3)
        mascara = cv.morphologyEx(mascara, cv.MORPH_OPEN, kernel_pequeno, iterations=2)
        
        # Encontrar contornos
        contornos, _ = cv.findContours(mascara, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        
        if not contornos:
            if debug:
                print("❌ Nenhum contorno azul encontrado")
                cv.imwrite("debug_mascara_azul.jpg", mascara)
            return None, None, None
        
        # Ordenar por área (maior primeiro)
        contornos = sorted(contornos, key=cv.contourArea, reverse=True)
        
        for contorno in contornos:
            area = cv.contourArea(contorno)
            if area < 2000:  # Aumentar limite mínimo
                continue
                
            perimetro = cv.arcLength(contorno, True)
            aprox = cv.approxPolyDP(contorno, 0.02 * perimetro, True)
            
            if len(aprox) == 4:  # Quadrilátero
                x, y, w, h = cv.boundingRect(aprox)
                razao_aspecto = float(w) / h
                
                # Critério mais flexível para quadrado
                if 0.7 <= razao_aspecto <= 1.3:
                    if debug:
                        print(f"✅ Quadrado azul detectado: {w}x{h} px, área: {area}")
                        img_debug = imagem.copy()
                        cv.drawContours(img_debug, [contorno], 0, (0, 255, 0), 3)
                        cv.rectangle(img_debug, (x, y), (x + w, y + h), (255, 0, 0), 2)
                        cv.imwrite("debug_quadrado_detectado.jpg", img_debug)
                    
                    return contorno, (x, y, w, h), mascara
        
        if debug:
            print("❌ Nenhum quadrilátero azul encontrado")
            cv.imwrite("debug_mascara_final.jpg", mascara)
            
        return None, None, None
        
    except Exception as e:
        print(f"❌ Erro na detecção do quadrado: {e}")
        return None, None, None

def criar_contorno_mao(landmarks, imagem_shape):
    """
    Cria um contorno aproximado da mão baseado nos landmarks
    """
    altura, largura = imagem_shape[:2]
    
    # Converter landmarks para pixels
    pontos_px = []
    for x, y, _ in landmarks:
        px = int(x * largura)
        py = int(y * altura)
        pontos_px.append((px, py))
    
    # Definir pontos do contorno da mão (ordem específica para criar polígono fechado)
    indices_contorno = [0, 1, 2, 3, 4, 8, 12, 16, 20, 19, 18, 17, 13, 9, 5, 0]
    pontos_contorno = [pontos_px[i] for i in indices_contorno]
    
    return np.array(pontos_contorno, dtype=np.int32)

def encontrar_interseccao_contorno(ponto_inicio, direcao, contorno, max_dist=300):
    """
    Encontra a interseção de uma linha com o contorno da mão
    """
    # Converter contorno para lista de pontos
    pontos_contorno = contorno.reshape(-1, 2)
    
    # Calcular linha de busca
    linha_x = int(ponto_inicio[0] + max_dist * direcao[0])
    linha_y = int(ponto_inicio[1] + max_dist * direcao[1])
    ponto_final = (linha_x, linha_y)
    
    # Encontrar interseções
    interseccoes = []
    
    for i in range(len(pontos_contorno)):
        p1 = pontos_contorno[i]
        p2 = pontos_contorno[(i + 1) % len(pontos_contorno)]
        
        # Verificar interseção entre segmentos
        interseccao = encontrar_interseccao_segmentos(ponto_inicio, ponto_final, p1, p2)
        if interseccao:
            interseccoes.append(interseccao)
    
    if interseccoes:
        # Encontrar a interseção mais próxima
        distancias = [math.hypot(p[0]-ponto_inicio[0], p[1]-ponto_inicio[1]) for p in interseccoes]
        return interseccoes[np.argmin(distancias)]
    
    return None

def encontrar_interseccao_segmentos(p1, p2, p3, p4):
    """
    Encontra a interseção entre dois segmentos de linha
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-10:
        return None
    
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
    
    if 0 <= t <= 1 and 0 <= u <= 1:
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        return (int(x), int(y))
    
    return None

def calcular_largura_palma_com_contorno(landmarks, contorno_mao, imagem_shape):
    """
    Calcula a largura da palma estendendo a linha entre pontos 5-17 até o contorno
    """
    altura, largura = imagem_shape[:2]
    
    # Converter landmarks para pixels
    p5 = (int(landmarks[5][0] * largura), int(landmarks[5][1] * altura))
    p17 = (int(landmarks[17][0] * largura), int(landmarks[17][1] * altura))
    
    # Calcular direção da linha 5-17
    dx = p17[0] - p5[0]
    dy = p17[1] - p5[1]
    comprimento = math.hypot(dx, dy)
    
    if comprimento == 0:
        return None, None, None
    
    # Normalizar direção
    dir_x = dx / comprimento
    dir_y = dy / comprimento
    
    # Encontrar interseções com o contorno
    interseccao_esquerda = encontrar_interseccao_contorno(p5, (-dir_x, -dir_y), contorno_mao)
    interseccao_direita = encontrar_interseccao_contorno(p17, (dir_x, dir_y), contorno_mao)
    
    # Se não encontrou interseções, usar os pontos originais
    if not interseccao_esquerda:
        interseccao_esquerda = p5
    if not interseccao_direita:
        interseccao_direita = p17
    
    # Calcular largura
    largura_px = math.hypot(interseccao_direita[0]-interseccao_esquerda[0], 
                           interseccao_direita[1]-interseccao_esquerda[1])
    
    return largura_px, interseccao_esquerda, interseccao_direita

def calcular_largura_pulso_com_contorno(landmarks, contorno_mao, imagem_shape):
    """
    Calcula a largura do pulso com linha perpendicular ao comprimento da mão
    """
    altura, largura = imagem_shape[:2]
    
    # Converter landmarks para pixels
    p0 = (int(landmarks[0][0] * largura), int(landmarks[0][1] * altura))
    p12 = (int(landmarks[12][0] * largura), int(landmarks[12][1] * altura))
    
    # Calcular direção do comprimento da mão (p0-p12)
    dx_comprimento = p12[0] - p0[0]
    dy_comprimento = p12[1] - p0[1]
    comprimento = math.hypot(dx_comprimento, dy_comprimento)
    
    if comprimento == 0:
        return None, None, None
    
    # Calcular direção perpendicular (90 graus)
    dir_perp_x = -dy_comprimento / comprimento
    dir_perp_y = dx_comprimento / comprimento
    
    # Encontrar interseções com o contorno
    interseccao_esquerda = encontrar_interseccao_contorno(p0, (-dir_perp_x, -dir_perp_y), contorno_mao)
    interseccao_direita = encontrar_interseccao_contorno(p0, (dir_perp_x, dir_perp_y), contorno_mao)
    
    # Se não encontrou interseções, usar fallback
    if not interseccao_esquerda or not interseccao_direita:
        # Fallback: usar pontos 0 e 17 como referência
        p17 = (int(landmarks[17][0] * largura), int(landmarks[17][1] * altura))
        largura_px = math.hypot(p17[0]-p0[0], p17[1]-p0[1])
        return largura_px, p0, p17
    
    # Calcular largura
    largura_px = math.hypot(interseccao_direita[0]-interseccao_esquerda[0], 
                           interseccao_direita[1]-interseccao_esquerda[1])
    
    return largura_px, interseccao_esquerda, interseccao_direita

def desenhar_medidas_com_contorno(imagem, landmarks, dimensoes, contorno_mao, pontos_palma, pontos_pulso):
    """
    Desenha as medidas na imagem usando o contorno da mão
    """
    img_com_medidas = imagem.copy()
    altura, largura = imagem.shape[:2]
    
    # Desenhar contorno da mão
    cv.polylines(img_com_medidas, [contorno_mao], True, (255, 255, 0), 2)  # Ciano
    
    # Desenhar linha da palma
    if pontos_palma[0] and pontos_palma[1]:
        cv.line(img_com_medidas, pontos_palma[0], pontos_palma[1], (255, 0, 0), 3)  # Azul
        cv.putText(img_com_medidas, f"Palma: {dimensoes['Largura Palma']:.2f}cm",
                  ((pontos_palma[0][0] + pontos_palma[1][0]) // 2 - 50,
                   (pontos_palma[0][1] + pontos_palma[1][1]) // 2 - 10),
                  cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
    
    # Desenhar linha do pulso
    if pontos_pulso[0] and pontos_pulso[1]:
        cv.line(img_com_medidas, pontos_pulso[0], pontos_pulso[1], (0, 165, 255), 3)  # Laranja
        cv.putText(img_com_medidas, f"Pulso: {dimensoes['Largura Pulso']:.2f}cm",
                  ((pontos_pulso[0][0] + pontos_pulso[1][0]) // 2 - 50,
                   (pontos_pulso[0][1] + pontos_pulso[1][1]) // 2 + 20),
                  cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
    
    # Desenhar comprimento da mão
    p0 = (int(landmarks[0][0] * largura), int(landmarks[0][1] * altura))
    p12 = (int(landmarks[12][0] * largura), int(landmarks[12][1] * altura))
    cv.line(img_com_medidas, p0, p12, (0, 255, 0), 3)  # Verde
    cv.putText(img_com_medidas, f"Comp: {dimensoes['Comprimento Mao']:.2f}cm",
              ((p0[0] + p12[0]) // 2 + 10, (p0[1] + p12[1]) // 2),
              cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    # Adicionar informações no canto
    y_offset = 30
    cv.putText(img_com_medidas, f"Tamanho Ortese: {dimensoes['Tamanho Ortese']}", 
               (10, y_offset), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv.putText(img_com_medidas, f"Escala: {dimensoes.get('escala_px_cm', 0):.2f} px/cm", 
               (10, y_offset + 30), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    
    return img_com_medidas

def pipeline_processamento_melhorado(caminho_imagem, caminho_stl_saida=None, modo_manual=False):
    """
    Pipeline melhorado com detecção de contorno da mão
    """
    print("🔄 Iniciando pipeline melhorado...")
    
    # Carregar imagem
    imagem = cv.imread(caminho_imagem)
    if imagem is None:
        print(f"❌ Erro ao carregar imagem: {caminho_imagem}")
        return None, None, None, None, None
    
    # 1. Detectar quadrado azul (versão melhorada)
    print("🔍 Detectando quadrado azul...")
    contorno_quadrado, dimensoes_quadrado, _ = detectar_quadrado_azul_melhorado(imagem, DEBUG)
    
    escala_px_cm = 0.0
    if contorno_quadrado is None:
        print("⚠️ Quadrado não detectado, usando escala padrão")
        escala_px_cm = 67.92  # Fallback
    else:
        x, y, w, h = dimensoes_quadrado
        escala_px_cm = (w + h) / (2 * TAMANHO_QUADRADO_CM)
        print(f"✅ Quadrado: {w}x{h} px, Escala: {escala_px_cm:.2f} px/cm")
    
    # 2. Detectar landmarks da mão
    print("🖐️ Detectando landmarks da mão...")
    with mp_hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.5) as hands:
        imagem_rgb = cv.cvtColor(imagem, cv.COLOR_BGR2RGB)
        resultados = hands.process(imagem_rgb)
        
        if not resultados.multi_hand_landmarks:
            print("❌ Não foi possível detectar landmarks da mão")
            return None, None, None, None, None
        
        hand_landmarks = resultados.multi_hand_landmarks[0]
        landmarks = [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
        
        # Determinar handedness
        handedness = "Right"
        if resultados.multi_handedness:
            for classification in resultados.multi_handedness[0].classification:
                handedness = classification.label
                break
    
    # 3. Criar contorno da mão
    print("📐 Criando contorno da mão...")
    contorno_mao = criar_contorno_mao(landmarks, imagem.shape)
    
    # 4. Calcular dimensões com contorno
    print("📏 Calculando dimensões com contorno...")
    
    # Largura da palma
    largura_palma_px, ponto_palma_esq, ponto_palma_dir = calcular_largura_palma_com_contorno(
        landmarks, contorno_mao, imagem.shape)
    
    # Largura do pulso
    largura_pulso_px, ponto_pulso_esq, ponto_pulso_dir = calcular_largura_pulso_com_contorno(
        landmarks, contorno_mao, imagem.shape)
    
    # Comprimento da mão
    altura, largura_img = imagem.shape[:2]
    p0 = (int(landmarks[0][0] * largura_img), int(landmarks[0][1] * altura))
    p12 = (int(landmarks[12][0] * largura_img), int(landmarks[12][1] * altura))
    comprimento_px = math.hypot(p12[0]-p0[0], p12[1]-p0[1])
    
    # Converter para cm
    largura_palma_cm = largura_palma_px / escala_px_cm if largura_palma_px else 0
    largura_pulso_cm = largura_pulso_px / escala_px_cm if largura_pulso_px else 0
    comprimento_cm = comprimento_px / escala_px_cm
    
    # Aplicar fatores de correção
    largura_palma_cm *= 1.05
    largura_pulso_cm *= 1.02
    
    # Determinar tamanho da órtese
    if largura_pulso_cm <= 7.0:
        tamanho_ortese = "P"
    elif largura_pulso_cm <= 9.0:
        tamanho_ortese = "M"
    else:
        tamanho_ortese = "G"
    
    dimensoes = {
        "Largura Pulso": round(largura_pulso_cm, 2),
        "Largura Palma": round(largura_palma_cm, 2),
        "Comprimento Mao": round(comprimento_cm, 2),
        "Tamanho Ortese": tamanho_ortese,
        "escala_px_cm": round(escala_px_cm, 2)
    }
    
    # 5. Desenhar resultados
    print("🎨 Desenhando resultados...")
    pontos_palma = (ponto_palma_esq, ponto_palma_dir)
    pontos_pulso = (ponto_pulso_esq, ponto_pulso_dir)
    
    imagem_resultado = desenhar_medidas_com_contorno(
        imagem, landmarks, dimensoes, contorno_mao, pontos_palma, pontos_pulso)
    
    # 6. Gerar STL (simplificado - usar a lógica existente)
    if caminho_stl_saida:
        print("🖨️ Gerando STL...")
        # Aqui você pode integrar com a função existente de geração de STL
        # usando as dimensões calculadas
    
    print("✅ Pipeline concluído com sucesso!")
    return caminho_stl_saida, imagem_resultado, None, dimensoes, handedness

# Função para integrar com a API existente
def processar_imagem_ortese_api_melhorado(imagem_bytes, modo_manual=False, modelo_base_stl_path=None):
    """
    Versão melhorada para a API
    """
    try:
        # Converter bytes para imagem
        nparr = np.frombuffer(imagem_bytes, np.uint8)
        imagem = cv.imdecode(nparr, cv.IMREAD_COLOR)
        
        if imagem is None:
            return {"erro": "Não foi possível carregar a imagem"}
        
        # Salvar temporariamente
        temp_img_path = "temp_input.jpg"
        cv.imwrite(temp_img_path, imagem)
        
        # Processar
        caminho_stl, imagem_processada, _, dimensoes, handedness = pipeline_processamento_melhorado(
            temp_img_path, modo_manual=modo_manual)
        
        # Limpar
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
        
        if dimensoes is None:
            return {"erro": "Não foi possível processar a imagem"}
        
        # Converter imagem para base64
        _, buffer = cv.imencode(".jpg", imagem_processada)
        imagem_base64 = base64.b64encode(buffer).decode("utf-8")
        
        return {
            "sucesso": True,
            "dimensoes": dimensoes,
            "handedness": handedness,
            "imagem_processada": f"data:image/jpeg;base64,{imagem_base64}",
            "stl_path": caminho_stl
        }
        
    except Exception as e:
        print(f"❌ Erro no processamento: {e}")
        return {"erro": f"Erro no processamento: {str(e)}"}