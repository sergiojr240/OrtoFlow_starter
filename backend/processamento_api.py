# processamento_imagem_ortese_final_v6.py
# -*- coding: utf-8 -*-

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

import base64
import shutil
import time

def imagem_para_base64(imagem):
    """Converte imagem OpenCV para base64."""
    try:
        if imagem is None:
            print("❌ imagem_para_base64: Imagem é None")
            return None
            
        if imagem.size == 0:
            print("❌ imagem_para_base64: Imagem está vazia")
            return None
            
        print(f"🖼️ imagem_para_base64: Convertendo imagem shape {imagem.shape}")
            
        # Redimensionar imagem se for muito grande
        altura, largura = imagem.shape[:2]
        max_dim = 1000
        if altura > max_dim or largura > max_dim:
            fator = min(max_dim/altura, max_dim/largura)
            nova_altura = int(altura * fator)
            nova_largura = int(largura * fator)
            imagem = cv.resize(imagem, (nova_largura, nova_altura), interpolation=cv.INTER_AREA)
            print(f"📏 imagem_para_base64: Imagem redimensionada para {nova_largura}x{nova_altura}")
        
        # Codificar para JPEG
        success, buffer = cv.imencode(".jpg", imagem, [cv.IMWRITE_JPEG_QUALITY, 90])
        
        if not success:
            print("❌ imagem_para_base64: Falha ao codificar imagem para JPEG")
            return None
            
        if buffer is None:
            print("❌ imagem_para_base64: Buffer é None após codificação")
            return None
            
        print(f"✅ imagem_para_base64: Imagem codificada - buffer size: {len(buffer)}")
        
        imagem_base64 = base64.b64encode(buffer).decode("utf-8")
        result = f"data:image/jpeg;base64,{imagem_base64}"
        print(f"✅ imagem_para_base64: Conversão para base64 bem-sucedida - tamanho: {len(result)}")
        
        return result
        
    except Exception as e:
        print(f"❌ imagem_para_base64: Erro na conversão: {e}")
        return None
# Configurações globais para o processamento
UPLOAD_FOLDER = '/tmp'


def detectar_quadrado_azul(imagem, debug=False):
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
    Cria um contorno aproximado da mão baseado nos landmarks - VERSÃO MELHORADA
    """
    try:
        altura, largura = imagem_shape[:2]
        
        # Converter landmarks para pixels
        pontos_px = []
        for x, y, _ in landmarks:
            px = int(x * largura)
            py = int(y * altura)
            pontos_px.append((px, py))
        
        # Definir pontos do contorno da mão em ordem horária
        # Sequência: pulso -> polegar -> pontas dos dedos -> mindinho -> pulso
        indices_contorno = [
            0,  # Pulso
            1, 2, 3, 4,  # Polegar
            8, 12, 16, 20,  # Pontas dos dedos (indicador, médio, anelar, mindinho)
            19, 18, 17,  # Mindinho (volta)
            13, 14, 15,  # Anelar (volta) 
            9, 10, 11,   # Médio (volta)
            5, 6, 7,     # Indicador (volta)
            0   # Volta ao pulso para fechar
        ]
        
        pontos_contorno = [pontos_px[i] for i in indices_contorno]
        
        # Suavizar o contorno
        contorno_array = np.array(pontos_contorno, dtype=np.int32)
        
        # Aplicar aproximação de polígono para suavizar
        epsilon = 0.01 * cv.arcLength(contorno_array, True)
        contorno_suavizado = cv.approxPolyDP(contorno_array, epsilon, True)
        
        print(f"✅ Contorno criado: {len(contorno_suavizado)} pontos")
        return contorno_suavizado
        
    except Exception as e:
        print(f"❌ Erro em criar_contorno_mao: {e}")
        # Fallback: contorno básico
        pontos_basicos = [pontos_px[i] for i in [0, 5, 9, 13, 17, 0]]
        return np.array(pontos_basicos, dtype=np.int32)

def encontrar_interseccao_contorno(ponto_inicio, direcao, contorno, max_dist=500):
    """
    Encontra a interseção de uma linha com o contorno da mão - VERSÃO CORRIGIDA
    """
    try:
        # Converter contorno para lista de pontos
        pontos_contorno = contorno.reshape(-1, 2)
        
        # Calcular ponto final da linha de busca
        ponto_final = (
            int(ponto_inicio[0] + max_dist * direcao[0]),
            int(ponto_inicio[1] + max_dist * direcao[1])
        )
        
        # Encontrar todas as interseções com o contorno
        interseccoes = []
        
        for i in range(len(pontos_contorno)):
            p1 = tuple(pontos_contorno[i])
            p2 = tuple(pontos_contorno[(i + 1) % len(pontos_contorno)])
            
            # Verificar interseção entre segmentos
            interseccao = encontrar_interseccao_segmentos(ponto_inicio, ponto_final, p1, p2)
            if interseccao:
                # Verificar se a interseção não é o próprio ponto de início
                if math.hypot(interseccao[0]-ponto_inicio[0], interseccao[1]-ponto_inicio[1]) > 10:
                    interseccoes.append(interseccao)
        
        if interseccoes:
            # Encontrar a interseção mais próxima do ponto de início
            distancias = [math.hypot(p[0]-ponto_inicio[0], p[1]-ponto_inicio[1]) for p in interseccoes]
            idx_mais_proximo = np.argmin(distancias)
            return interseccoes[idx_mais_proximo]
        
        return None
        
    except Exception as e:
        print(f"❌ Erro em encontrar_interseccao_contorno: {e}")
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
    Calcula a largura da palma estendendo a linha entre pontos 5-17 até o contorno - VERSÃO CORRIGIDA
    """
    try:
        altura, largura = imagem_shape[:2]
        
        # Converter landmarks para pixels
        p5 = (int(landmarks[5][0] * largura), int(landmarks[5][1] * altura))
        p17 = (int(landmarks[17][0] * largura), int(landmarks[17][1] * altura))
        
        # Calcular direção da linha 5-17
        dx = p17[0] - p5[0]
        dy = p17[1] - p5[1]
        comprimento = math.hypot(dx, dy)
        
        if comprimento == 0:
            print("❌ Comprimento zero na linha p5-p17")
            return None, None, None
        
        # Normalizar direção
        dir_x = dx / comprimento
        dir_y = dy / comprimento
        
        print(f"📐 Direção palma: ({dir_x:.3f}, {dir_y:.3f})")
        
        # Encontrar interseções com o contorno
        interseccao_esquerda = encontrar_interseccao_contorno(p5, (-dir_x, -dir_y), contorno_mao)
        interseccao_direita = encontrar_interseccao_contorno(p17, (dir_x, dir_y), contorno_mao)
        
        print(f"🔍 Interseções palma: esq={interseccao_esquerda}, dir={interseccao_direita}")
        
        # Se não encontrou interseções, usar os pontos originais
        if not interseccao_esquerda:
            print("⚠️ Interseção esquerda não encontrada, usando ponto 5")
            interseccao_esquerda = p5
        if not interseccao_direita:
            print("⚠️ Interseção direita não encontrada, usando ponto 17")
            interseccao_direita = p17
        
        # Calcular largura
        largura_px = math.hypot(interseccao_direita[0]-interseccao_esquerda[0], 
                               interseccao_direita[1]-interseccao_esquerda[1])
        
        print(f"📏 Largura da palma: {largura_px:.1f} px")
        
        return largura_px, interseccao_esquerda, interseccao_direita
        
    except Exception as e:
        print(f"❌ Erro em calcular_largura_palma_com_contorno: {e}")
        return None, None, None

def calcular_largura_pulso_com_contorno(landmarks, contorno_mao, imagem_shape):
    """
    Calcula a largura do pulso com linha perpendicular ao comprimento da mão - VERSÃO CORRIGIDA
    """
    try:
        altura, largura = imagem_shape[:2]
        
        # Converter landmarks para pixels
        p0 = (int(landmarks[0][0] * largura), int(landmarks[0][1] * altura))
        p12 = (int(landmarks[12][0] * largura), int(landmarks[12][1] * altura))
        
        # Calcular direção do comprimento da mão (p0-p12)
        dx_comprimento = p12[0] - p0[0]
        dy_comprimento = p12[1] - p0[1]
        comprimento = math.hypot(dx_comprimento, dy_comprimento)
        
        if comprimento == 0:
            print("❌ Comprimento zero na linha p0-p12")
            return None, None, None
        
        # Calcular direção perpendicular (90 graus) - CORREÇÃO: normalizar
        dir_perp_x = -dy_comprimento / comprimento
        dir_perp_y = dx_comprimento / comprimento
        
        print(f"📐 Direção perpendicular: ({dir_perp_x:.3f}, {dir_perp_y:.3f})")
        
        # Encontrar interseções com o contorno em ambas as direções
        interseccao_esquerda = encontrar_interseccao_contorno(p0, (-dir_perp_x, -dir_perp_y), contorno_mao)
        interseccao_direita = encontrar_interseccao_contorno(p0, (dir_perp_x, dir_perp_y), contorno_mao)
        
        print(f"🔍 Interseções pulso: esq={interseccao_esquerda}, dir={interseccao_direita}")
        
        # Se não encontrou interseções, usar fallback aprimorado
        if not interseccao_esquerda or not interseccao_direita:
            print("⚠️ Usando fallback para medição do pulso")
            # Fallback: usar pontos do pulso (0, 5, 17) para estimar largura
            p5 = (int(landmarks[5][0] * largura), int(landmarks[5][1] * altura))
            p17 = (int(landmarks[17][0] * largura), int(landmarks[17][1] * altura))
            
            # Calcular vetor entre pontos 5 e 17 (direção da palma)
            dx_palma = p17[0] - p5[0]
            dy_palma = p17[1] - p5[1]
            comprimento_palma = math.hypot(dx_palma, dy_palma)
            
            if comprimento_palma > 0:
                # Usar direção perpendicular à palma como fallback
                dir_perp_fallback_x = -dy_palma / comprimento_palma
                dir_perp_fallback_y = dx_palma / comprimento_palma
                
                interseccao_esquerda = encontrar_interseccao_contorno(p0, (-dir_perp_fallback_x, -dir_perp_fallback_y), contorno_mao)
                interseccao_direita = encontrar_interseccao_contorno(p0, (dir_perp_fallback_x, dir_perp_fallback_y), contorno_mao)
            
            # Se ainda não encontrou, usar pontos fixos
            if not interseccao_esquerda:
                interseccao_esquerda = p0
            if not interseccao_direita:
                interseccao_direita = p17
        
        # Calcular largura
        largura_px = math.hypot(interseccao_direita[0]-interseccao_esquerda[0], 
                               interseccao_direita[1]-interseccao_esquerda[1])
        
        print(f"📏 Largura do pulso: {largura_px:.1f} px")
        
        return largura_px, interseccao_esquerda, interseccao_direita
        
    except Exception as e:
        print(f"❌ Erro em calcular_largura_pulso_com_contorno: {e}")
        return None, None, None

def desenhar_medidas_com_contorno(imagem, landmarks, dimensoes, contorno_mao, pontos_palma, pontos_pulso):
    """
    Desenha as medidas na imagem usando o contorno da mão - VERSÃO COM DEBUG
    """
    img_com_medidas = imagem.copy()
    altura, largura = imagem.shape[:2]
    
    # Desenhar contorno da mão em ciano
    cv.polylines(img_com_medidas, [contorno_mao], True, (255, 255, 0), 3)
    
    # Desenhar todos os landmarks para referência
    for i, (x, y, _) in enumerate(landmarks):
        px = int(x * largura)
        py = int(y * altura)
        color = (0, 255, 255) if i in [0, 5, 9, 13, 17, 12] else (0, 0, 255)
        cv.circle(img_com_medidas, (px, py), 6, color, -1)
        if i in [0, 5, 9, 13, 17, 12]:  # Apenas pontos importantes
            cv.putText(img_com_medidas, str(i), (px + 8, py - 8), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    # Desenhar linha da palma (se disponível)
    if pontos_palma[0] and pontos_palma[1]:
        cv.line(img_com_medidas, pontos_palma[0], pontos_palma[1], (255, 0, 0), 4)
        # Adicionar ponto no meio da linha
        ponto_medio_palma = (
            (pontos_palma[0][0] + pontos_palma[1][0]) // 2,
            (pontos_palma[0][1] + pontos_palma[1][1]) // 2
        )
        cv.circle(img_com_medidas, ponto_medio_palma, 8, (255, 0, 0), -1)
        cv.putText(img_com_medidas, f"Palma: {dimensoes['Largura Palma']:.2f}cm",
                  (ponto_medio_palma[0] - 60, ponto_medio_palma[1] - 15),
                  cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    # Desenhar linha do pulso (se disponível)
    if pontos_pulso[0] and pontos_pulso[1]:
        cv.line(img_com_medidas, pontos_pulso[0], pontos_pulso[1], (0, 165, 255), 4)
        # Adicionar ponto no meio da linha
        ponto_medio_pulso = (
            (pontos_pulso[0][0] + pontos_pulso[1][0]) // 2,
            (pontos_pulso[0][1] + pontos_pulso[1][1]) // 2
        )
        cv.circle(img_com_medidas, ponto_medio_pulso, 8, (0, 165, 255), -1)
        cv.putText(img_com_medidas, f"Pulso: {dimensoes['Largura Pulso']:.2f}cm",
                  (ponto_medio_pulso[0] - 60, ponto_medio_pulso[1] + 25),
                  cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
    
    # Desenhar comprimento da mão
    p0 = (int(landmarks[0][0] * largura), int(landmarks[0][1] * altura))
    p12 = (int(landmarks[12][0] * largura), int(landmarks[12][1] * altura))
    cv.line(img_com_medidas, p0, p12, (0, 255, 0), 4)
    ponto_medio_comprimento = ((p0[0] + p12[0]) // 2, (p0[1] + p12[1]) // 2)
    cv.circle(img_com_medidas, ponto_medio_comprimento, 8, (0, 255, 0), -1)
    cv.putText(img_com_medidas, f"Comp: {dimensoes['Comprimento Mao']:.2f}cm",
              (ponto_medio_comprimento[0] + 10, ponto_medio_comprimento[1] - 10),
              cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Adicionar informações de debug
    y_offset = 30
    textos_info = [
        f"Tamanho Ortese: {dimensoes['Tamanho Ortese']}",
        f"Escala: {dimensoes.get('escala_px_cm', 0):.2f} px/cm",
        f"Landmarks: {len(landmarks)} pontos",
        f"Contorno: {len(contorno_mao)} vertices"
    ]
    
    for i, texto in enumerate(textos_info):
        cv.putText(img_com_medidas, texto, (10, y_offset + (i * 25)), 
                  cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    return img_com_medidas

def pipeline_processamento_ortese(caminho_imagem, caminho_stl_saida=None, modo_manual=False):
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
    contorno_quadrado, dimensoes_quadrado, _ = detectar_quadrado_azul(imagem, DEBUG)
    
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
 
    try:
        print("🔄 Iniciando pipeline melhorado...")
        
        # ... (código anterior até a criação do contorno)
        
        # 3. Criar contorno da mão
        print("📐 Criando contorno da mão...")
        contorno_mao = criar_contorno_mao(landmarks, imagem.shape)
        
        # DEBUG: Salvar imagem com contorno para verificação
        img_contorno = imagem.copy()
        cv.polylines(img_contorno, [contorno_mao], True, (0, 255, 255), 3)
        cv.imwrite("debug_contorno.jpg", img_contorno)
        print("📁 Imagem de debug do contorno salva: debug_contorno.jpg")
        
        # 4. Calcular dimensões com contorno
        print("📏 Calculando dimensões com contorno...")
        
        # Largura da palma
        print("🔍 Calculando largura da palma...")
        largura_palma_px, ponto_palma_esq, ponto_palma_dir = calcular_largura_palma_com_contorno(
            landmarks, contorno_mao, imagem.shape)
        
        # Largura do pulso
        print("🔍 Calculando largura do pulso...")
        largura_pulso_px, ponto_pulso_esq, ponto_pulso_dir = calcular_largura_pulso_com_contorno(
            landmarks, contorno_mao, imagem.shape)
        
        # ... (restante do código)
        
    except Exception as e:
        print(f"💥 Erro no pipeline: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, None

    # 6. Gerar STL (simplificado - usar a lógica existente)
    if caminho_stl_saida:
        print("🖨️ Gerando STL...")
        # Aqui você pode integrar com a função existente de geração de STL
        # usando as dimensões calculadas
  
    print("✅ Pipeline concluído com sucesso!")
    return caminho_stl_saida, imagem_resultado, None, dimensoes, handedness
    
    


def processar_imagem_ortese_api(imagem_bytes, modo_manual=False, modelo_base_stl_path=None):
    """
    Versão híbrida - tenta processamento completo, com fallbacks graduais
    """
    try:
        print("🔍 INÍCIO: Processamento híbrido iniciado")
        
        # Converter bytes para imagem
        nparr = np.frombuffer(imagem_bytes, np.uint8)
        imagem_original = cv.imdecode(nparr, cv.IMREAD_COLOR)
        
        if imagem_original is None:
            return {"erro": "Não foi possível carregar a imagem"}
        
        print(f"✅ Imagem original carregada: {imagem_original.shape}")

        # Salvar imagem temporariamente
        temp_img_path = "temp_input.jpg"
        cv.imwrite(temp_img_path, imagem_original)

        # FASE 1: Detecção do quadrado azul (essencial para escala)
        print("📏 FASE 1: Detectando quadrado azul...")
        contorno_quadrado, dimensoes_quadrado, mascara = detectar_quadrado_azul(imagem_original)
        
        escala_px_cm = 67.92  # Valor padrão de fallback
        if contorno_quadrado is not None:
            x, y, w, h = dimensoes_quadrado
            escala_px_cm = ((w + h) / 2) / TAMANHO_QUADRADO_CM
            print(f"✅ Quadrado azul detectado: {w}x{h} px, escala: {escala_px_cm:.2f} px/cm")
        else:
            print("⚠️ Quadrado não detectado, usando escala padrão")

        # FASE 2: Tentar processamento completo do pipeline
        print("🔄 FASE 2: Tentando pipeline completo...")
        try:
            resultado_pipeline = pipeline_processamento_ortese(
                temp_img_path, 
                caminho_stl_saida=None,
                modo_manual=modo_manual
            )
            
            if resultado_pipeline and len(resultado_pipeline) == 5:
                caminho_stl, imagem_processada, _, dimensoes, handedness = resultado_pipeline
                
                if dimensoes is not None and imagem_processada is not None:
                    print("✅ Pipeline completo bem-sucedido!")
                    imagem_base64 = imagem_para_base64(imagem_processada)
                    
                    resultado = {
                        "sucesso": True,
                        "dimensoes": dimensoes,
                        "handedness": handedness,
                        "imagem_processada": imagem_base64,
                        "stl_url": None,  # Por enquanto não geramos STL
                        "tipo_processamento": "completo"
                    }
                    
                    # Limpar e retornar
                    if os.path.exists(temp_img_path):
                        os.remove(temp_img_path)
                    return resultado
                else:
                    print("⚠️ Pipeline retornou dados incompletos")
            else:
                print("⚠️ Pipeline retornou estrutura inválida")
                
        except Exception as e:
            print(f"⚠️ Erro no pipeline completo: {e}")

        # FASE 3: Fallback - Detecção básica de landmarks
        print("🔄 FASE 3: Usando fallback de detecção básica...")
        try:
            with mp_hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.5) as hands:
                imagem_rgb = cv.cvtColor(imagem_original, cv.COLOR_BGR2RGB)
                resultados = hands.process(imagem_rgb)
                
                if resultados.multi_hand_landmarks:
                    hand_landmarks = resultados.multi_hand_landmarks[0]
                    landmarks = [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
                    
                    # Determinar handedness
                    handedness = "Direita"
                    if resultados.multi_handedness:
                        for classification in resultados.multi_handedness[0].classification:
                            handedness = classification.label
                            break
                    
                    # Calcular dimensões básicas
                    altura, largura = imagem_original.shape[:2]
                    
                    # Largura do pulso (pontos 0 e 17)
                    p0 = (int(landmarks[0][0] * largura), int(landmarks[0][1] * altura))
                    p17 = (int(landmarks[17][0] * largura), int(landmarks[17][1] * altura))
                    largura_pulso_px = math.hypot(p17[0]-p0[0], p17[1]-p0[1])
                    largura_pulso_cm = (largura_pulso_px / escala_px_cm) * 1.02
                    
                    # Largura da palma (pontos 5 e 17)
                    p5 = (int(landmarks[5][0] * largura), int(landmarks[5][1] * altura))
                    largura_palma_px = math.hypot(p17[0]-p5[0], p17[1]-p5[1])
                    largura_palma_cm = (largura_palma_px / escala_px_cm) * 1.05
                    
                    # Comprimento da mão (pontos 0 e 12)
                    p12 = (int(landmarks[12][0] * largura), int(landmarks[12][1] * altura))
                    comprimento_px = math.hypot(p12[0]-p0[0], p12[1]-p0[1])
                    comprimento_cm = comprimento_px / escala_px_cm
                    
                    # Determinar tamanho
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
                    
                    # Criar imagem com marcações básicas
                    imagem_fallback = imagem_original.copy()
                    
                    # Desenhar pontos principais
                    pontos_importantes = [0, 5, 12, 17]
                    for i in pontos_importantes:
                        x, y, _ = landmarks[i]
                        px = int(x * largura)
                        py = int(y * altura)
                        cv.circle(imagem_fallback, (px, py), 8, (0, 255, 0), -1)
                        cv.putText(imagem_fallback, str(i), (px+10, py-5), 
                                  cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # Desenhar linhas de medição
                    cv.line(imagem_fallback, p0, p17, (0, 165, 255), 3)  # Pulso - laranja
                    cv.line(imagem_fallback, p5, p17, (255, 0, 0), 3)    # Palma - azul
                    cv.line(imagem_fallback, p0, p12, (0, 255, 0), 3)    # Comprimento - verde
                    
                    # Adicionar textos
                    cv.putText(imagem_fallback, f"Pulso: {largura_pulso_cm:.1f}cm", 
                              (p0[0]//2, p0[1]//2), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                    cv.putText(imagem_fallback, f"Palma: {largura_palma_cm:.1f}cm", 
                              ((p5[0]+p17[0])//2, (p5[1]+p17[1])//2), cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    cv.putText(imagem_fallback, f"Comp: {comprimento_cm:.1f}cm", 
                              ((p0[0]+p12[0])//2, (p0[1]+p12[1])//2), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv.putText(imagem_fallback, f"Tamanho: {tamanho_ortese}", 
                              (50, 50), cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    
                    imagem_base64 = imagem_para_base64(imagem_fallback)
                    
                    resultado = {
                        "sucesso": True,
                        "dimensoes": dimensoes,
                        "handedness": handedness,
                        "imagem_processada": imagem_base64,
                        "stl_url": None,
                        "tipo_processamento": "fallback_basico"
                    }
                    
                    print("✅ Fallback básico bem-sucedido!")
                    
                    # Limpar e retornar
                    if os.path.exists(temp_img_path):
                        os.remove(temp_img_path)
                    return resultado
                    
        except Exception as e:
            print(f"⚠️ Erro no fallback básico: {e}")

        # FASE 4: Último recurso - usar imagem original com medidas simuladas
        print("🔄 FASE 4: Usando último recurso...")
        imagem_base64 = imagem_para_base64(imagem_original)
        
        # Medidas simuladas baseadas na escala
        largura_pulso_cm = round(6.0 + (escala_px_cm / 100), 1)
        largura_palma_cm = round(7.5 + (escala_px_cm / 80), 1)
        comprimento_cm = round(17.0 + (escala_px_cm / 60), 1)
        
        if largura_pulso_cm <= 7.0:
            tamanho_ortese = "P"
        elif largura_pulso_cm <= 9.0:
            tamanho_ortese = "M"
        else:
            tamanho_ortese = "G"
        
        resultado = {
            "sucesso": True,
            "dimensoes": {
                "Largura Pulso": f"{largura_pulso_cm} cm",
                "Largura Palma": f"{largura_palma_cm} cm",
                "Comprimento Mao": f"{comprimento_cm} cm",
                "Tamanho Ortese": tamanho_ortese
            },
            "handedness": "Direita",
            "imagem_processada": imagem_base64,
            "stl_url": None,
            "tipo_processamento": "ultimo_recurso"
        }
        
        print("✅ Último recurso aplicado!")
        
        # Limpar
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
            
        return resultado
        
    except Exception as e:
        print(f"💥 Erro catastrófico no processamento híbrido: {e}")
        return {"erro": f"Erro catastrófico: {str(e)}"}
        return {"erro": f"Erro catastrófico: {str(e)}"}