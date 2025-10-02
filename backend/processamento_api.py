# processamento_imagem_ortese_simplificado.py
# -*- coding: utf-8 -*-

import cv2 as cv
import numpy as np
import mediapipe as mp
from stl import mesh
import os
import math
import base64
import shutil
import time

# Configurações globais
DEBUG = True
TAMANHO_QUADRADO_CM = 6.0
UPLOAD_FOLDER = '/tmp'

# Configurações para detecção do quadrado azul
LOWER_BLUE = np.array([90, 80, 50])
UPPER_BLUE = np.array([130, 255, 255])

# Multiplicadores fixos para as medidas
MULTIPLICADOR_PULSO = 0.9
MULTIPLICADOR_PALMA = 1.45

# Inicializar MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

def imagem_para_base64(imagem):
    """Converte imagem OpenCV para base64."""
    try:
        if imagem is None or imagem.size == 0:
            return None
            
        # Redimensionar imagem se for muito grande
        altura, largura = imagem.shape[:2]
        max_dim = 1000
        if altura > max_dim or largura > max_dim:
            fator = min(max_dim/altura, max_dim/largura)
            nova_altura = int(altura * fator)
            nova_largura = int(largura * fator)
            imagem = cv.resize(imagem, (nova_largura, nova_altura), interpolation=cv.INTER_AREA)
        
        _, buffer = cv.imencode(".jpg", imagem, [cv.IMWRITE_JPEG_QUALITY, 90])
        
        if buffer is None:
            return None
            
        imagem_base64 = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/jpeg;base64,{imagem_base64}"
    except Exception as e:
        print(f"Erro convertendo imagem para base64: {e}")
        return None

def detectar_quadrado_azul(imagem, debug=False):
    """Detecta o quadrado azul na imagem."""
    try:
        imagem_hsv = cv.cvtColor(imagem, cv.COLOR_BGR2HSV)
        mascara = cv.inRange(imagem_hsv, LOWER_BLUE, UPPER_BLUE)
        
        kernel = np.ones((15, 15), np.uint8)
        mascara = cv.morphologyEx(mascara, cv.MORPH_CLOSE, kernel, iterations=2)
        mascara = cv.morphologyEx(mascara, cv.MORPH_OPEN, kernel, iterations=1)
        
        contornos, _ = cv.findContours(mascara, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        
        if not contornos:
            return None, None, None
        
        contornos = sorted(contornos, key=cv.contourArea, reverse=True)
        
        for contorno in contornos:
            area = cv.contourArea(contorno)
            if area < 2000:
                continue
                
            perimetro = cv.arcLength(contorno, True)
            aprox = cv.approxPolyDP(contorno, 0.02 * perimetro, True)
            
            if len(aprox) == 4:
                x, y, w, h = cv.boundingRect(aprox)
                razao_aspecto = float(w) / h
                
                if 0.7 <= razao_aspecto <= 1.3:
                    return contorno, (x, y, w, h), mascara
        
        return None, None, None
        
    except Exception as e:
        print(f"Erro na detecção do quadrado: {e}")
        return None, None, None

def calcular_dimensoes_simplificado(landmarks, escala_px_cm, imagem_shape):
    """Calcula dimensões usando multiplicadores fixos."""
    try:
        altura, largura = imagem_shape[:2]
        
        # Converter landmarks para pixels
        p5 = (int(landmarks[5][0] * largura), int(landmarks[5][1] * altura))
        p17 = (int(landmarks[17][0] * largura), int(landmarks[17][1] * altura))
        p0 = (int(landmarks[0][0] * largura), int(landmarks[0][1] * altura))
        p12 = (int(landmarks[12][0] * largura), int(landmarks[12][1] * altura))
        
        # Distância base entre pontos 5 e 17
        distancia_base_px = math.hypot(p17[0] - p5[0], p17[1] - p5[1])
        
        # Aplicar multiplicadores
        largura_pulso_px = distancia_base_px * MULTIPLICADOR_PULSO
        largura_palma_px = distancia_base_px * MULTIPLICADOR_PALMA
        comprimento_px = math.hypot(p12[0] - p0[0], p12[1] - p0[1])
        
        # Converter para cm
        largura_pulso_cm = largura_pulso_px / escala_px_cm
        largura_palma_cm = largura_palma_px / escala_px_cm
        comprimento_cm = comprimento_px / escala_px_cm
        
        # Determinar tamanho da órtese
        if largura_pulso_cm <= 7.0:
            tamanho_ortese = "P"
        elif largura_pulso_cm <= 9.0:
            tamanho_ortese = "M"
        else:
            tamanho_ortese = "G"
        
        return {
            "Largura Pulso": round(largura_pulso_cm, 2),
            "Largura Palma": round(largura_palma_cm, 2),
            "Comprimento Mao": round(comprimento_cm, 2),
            "Tamanho Ortese": tamanho_ortese,
            "escala_px_cm": round(escala_px_cm, 2),
            "distancia_base_px": round(distancia_base_px, 2)
        }
        
    except Exception as e:
        print(f"Erro no cálculo simplificado: {e}")
        return None

def desenhar_medidas_simplificado(imagem, landmarks, dimensoes, contorno_quadrado=None):
    """Desenha as medidas na imagem de forma simplificada."""
    img_com_medidas = imagem.copy()
    altura, largura = imagem.shape[:2]
    
    # Desenhar contorno preto no quadrado de referência
    if contorno_quadrado is not None:
        cv.drawContours(img_com_medidas, [contorno_quadrado], 0, (0, 0, 0), 3)  # Preto
    
    # Converter landmarks para pixels
    p5 = (int(landmarks[5][0] * largura), int(landmarks[5][1] * altura))
    p17 = (int(landmarks[17][0] * largura), int(landmarks[17][1] * altura))
    p0 = (int(landmarks[0][0] * largura), int(landmarks[0][1] * altura))
    p12 = (int(landmarks[12][0] * largura), int(landmarks[12][1] * altura))
    
    # Calcular pontos para as linhas usando os multiplicadores
    distancia_base_px = dimensoes.get('distancia_base_px', math.hypot(p17[0]-p5[0], p17[1]-p5[1]))
    
    # Linha da palma (pontos 5-17)
    cv.line(img_com_medidas, p5, p17, (255, 0, 0), 3)
    cv.putText(img_com_medidas, f"Palma: {dimensoes['Largura Palma']:.2f}cm",
              ((p5[0] + p17[0]) // 2 - 60, (p5[1] + p17[1]) // 2 - 15),
              cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    # Linha do pulso (calculada a partir do ponto 0)
    # Usar a mesma direção da linha 5-17 mas com comprimento reduzido
    dx = p17[0] - p5[0]
    dy = p17[1] - p5[1]
    comprimento_base = math.hypot(dx, dy)
    
    if comprimento_base > 0:
        # Calcular ponto final para a linha do pulso
        fator_pulso = MULTIPLICADOR_PULSO / MULTIPLICADOR_PALMA
        ponto_pulso_fim = (
            int(p0[0] + dx * fator_pulso),
            int(p0[1] + dy * fator_pulso)
        )
        
        cv.line(img_com_medidas, p0, ponto_pulso_fim, (0, 165, 255), 3)
        cv.putText(img_com_medidas, f"Pulso: {dimensoes['Largura Pulso']:.2f}cm",
                  ((p0[0] + ponto_pulso_fim[0]) // 2 - 60, 
                   (p0[1] + ponto_pulso_fim[1]) // 2 + 20),
                  cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
    
    # Linha do comprimento (ponto 0-12)
    cv.line(img_com_medidas, p0, p12, (0, 255, 0), 3)
    cv.putText(img_com_medidas, f"Comp: {dimensoes['Comprimento Mao']:.2f}cm",
              ((p0[0] + p12[0]) // 2 + 10, (p0[1] + p12[1]) // 2),
              cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Informações adicionais
    y_offset = 30
    cv.putText(img_com_medidas, f"Tamanho: {dimensoes['Tamanho Ortese']}", 
               (10, y_offset), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv.putText(img_com_medidas, f"Escala: {dimensoes['escala_px_cm']:.2f} px/cm", 
               (10, y_offset + 30), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    cv.putText(img_com_medidas, f"Multiplicadores: P={MULTIPLICADOR_PULSO}, M={MULTIPLICADOR_PALMA}", 
               (10, y_offset + 60), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    
    return img_com_medidas

def gerar_stl_simplificado(dimensoes, handedness, output_path, modelo_base_path):
    """Gera STL usando a lógica do perímetro."""
    try:
        if not os.path.exists(modelo_base_path):
            print(f"Modelo base não encontrado: {modelo_base_path}")
            return False
        
        # Carregar modelo base
        ortese_base = mesh.Mesh.from_file(modelo_base_path)
        
        # Obter largura do pulso
        largura_pulso_cm = dimensoes.get("Largura Pulso", 0.0)
        if largura_pulso_cm == 0.0:
            return False
        
        # Calcular fator de escala baseado no perímetro
        perimetro_paciente = 2.2 * largura_pulso_cm
        perimetro_template = 10.0
        fator_escala = perimetro_paciente / perimetro_template
        
        print(f"📏 Escalonamento STL:")
        print(f"   Pulso: {largura_pulso_cm:.2f}cm")
        print(f"   Perímetro: {perimetro_paciente:.2f}cm")
        print(f"   Fator: {fator_escala:.3f}")
        
        # Aplicar escala
        ortese_escalada = ortese_base.copy()
        ortese_escalada.vectors[:, :, 0] *= fator_escala  # X
        ortese_escalada.vectors[:, :, 1] *= fator_escala  # Y
        # Manter Z (altura) original
        
        # Espelhar para mão esquerda
        if handedness == "Left":
            ortese_escalada.vectors[:, :, 0] *= -1.0
        
        # Salvar
        ortese_escalada.save(output_path)
        print(f"✅ STL salvo: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Erro gerando STL: {e}")
        return False

def pipeline_processamento_simplificado(caminho_imagem, caminho_stl_saida=None, modo_manual=False):
    """Pipeline simplificado sem contorno complexo."""
    try:
        print("🔄 Iniciando pipeline simplificado...")
        
        # Carregar imagem
        imagem = cv.imread(caminho_imagem)
        if imagem is None:
            return None, None, None, None, None
        
        print(f"📷 Imagem carregada: {imagem.shape}")
        
        # 1. Detectar quadrado azul
        print("🔍 Detectando quadrado azul...")
        contorno_quadrado, dimensoes_quadrado, _ = detectar_quadrado_azul(imagem)
        
        escala_px_cm = 67.92  # Fallback
        if contorno_quadrado is not None:
            x, y, w, h = dimensoes_quadrado
            escala_px_cm = (w + h) / (2 * TAMANHO_QUADRADO_CM)
            print(f"✅ Quadrado: {w}x{h} px, Escala: {escala_px_cm:.2f} px/cm")
        else:
            print("⚠️ Quadrado não detectado, usando escala padrão")
        
        # 2. Detectar landmarks
        print("🖐️ Detectando landmarks...")
        with mp_hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.5) as hands:
            imagem_rgb = cv.cvtColor(imagem, cv.COLOR_BGR2RGB)
            resultados = hands.process(imagem_rgb)
            
            if not resultados.multi_hand_landmarks:
                return None, None, None, None, None
            
            hand_landmarks = resultados.multi_hand_landmarks[0]
            landmarks = [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
            
            handedness = "Right"
            if resultados.multi_handedness:
                for classification in resultados.multi_handedness[0].classification:
                    handedness = classification.label
                    break
        
        # 3. Calcular dimensões
        print("📏 Calculando dimensões...")
        dimensoes = calcular_dimensoes_simplificado(landmarks, escala_px_cm, imagem.shape)
        if dimensoes is None:
            return None, None, None, None, None
        
        # 4. Desenhar resultados
        print("🎨 Desenhando medidas...")
        imagem_resultado = desenhar_medidas_simplificado(imagem, landmarks, dimensoes, contorno_quadrado)
        
        # 5. Gerar STL se solicitado
        stl_gerado = None
        if caminho_stl_saida:
            print("🖨️ Gerando STL...")
            # Usar modelo base (ajuste o caminho conforme necessário)
            modelo_base_path = "OrtoFlow_starter\models\modelo_base.stl"  # Altere para o caminho correto
            if gerar_stl_simplificado(dimensoes, handedness, caminho_stl_saida, modelo_base_path):
                stl_gerado = caminho_stl_saida
                print(f"✅ STL gerado: {stl_gerado}")
            else:
                print("❌ Falha ao gerar STL")
        
        print("✅ Pipeline simplificado concluído!")
        return stl_gerado, imagem_resultado, None, dimensoes, handedness
        
    except Exception as e:
        print(f"💥 Erro no pipeline: {e}")
        return None, None, None, None, None

def processar_imagem_ortese_api(imagem_bytes, modo_manual=False, modelo_base_stl_path=None):
    """Função principal para a API."""
    try:
        print("🔍 Processando imagem para API...")
        
        # Converter bytes para imagem
        nparr = np.frombuffer(imagem_bytes, np.uint8)
        imagem = cv.imdecode(nparr, cv.IMREAD_COLOR)
        
        if imagem is None:
            return {"erro": "Não foi possível carregar a imagem"}
        
        # Salvar temporariamente
        temp_img_path = "temp_processamento.jpg"
        cv.imwrite(temp_img_path, imagem)
        
        # Gerar nome único para o STL
        temp_stl_path = f"ortese_gerada_{int(time.time())}.stl"
        
        # Processar
        stl_path, imagem_processada, _, dimensoes, handedness = pipeline_processamento_simplificado(
            temp_img_path, temp_stl_path, modo_manual
        )
        
        # Limpar arquivo temporário
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
        
        if dimensoes is None:
            return {"erro": "Não foi possível processar a imagem"}
        
        # Converter imagem para base64
        imagem_base64 = imagem_para_base64(imagem_processada)
        if imagem_base64 is None:
            return {"erro": "Erro ao processar imagem para exibição"}
        
        # Preparar URL para download do STL
        stl_url = None
        if stl_path and os.path.exists(stl_path):
            # Mover para pasta de uploads
            stl_filename = f"ortese_{int(time.time())}.stl"
            stl_final_path = os.path.join(UPLOAD_FOLDER, stl_filename)
            shutil.copy2(stl_path, stl_final_path)
            stl_url = f"/api/download-stl/{stl_filename}"
            
            # Limpar arquivo temporário do STL
            if os.path.exists(stl_path):
                os.remove(stl_path)
        
        return {
            "sucesso": True,
            "dimensoes": dimensoes,
            "handedness": handedness,
            "imagem_processada": imagem_base64,
            "stl_url": stl_url,
            "tipo_processamento": "simplificado"
        }
        
    except Exception as e:
        print(f"❌ Erro no processamento: {e}")
        return {"erro": f"Erro no processamento: {str(e)}"}