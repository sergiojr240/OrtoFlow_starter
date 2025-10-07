# processamento_api.py - VERSÃO COMPLETAMENTE CORRIGIDA
import cv2 as cv
import numpy as np
import mediapipe as mp
from stl import mesh
import os
import math
import base64
import shutil
import time
import copy

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

def corrigir_detecao_mao(landmarks, handedness_detectado, imagem_shape):
    try:
        altura, largura = imagem_shape[:2]
        
        # Converter landmarks para pixels
        pulso = (int(landmarks[0][0] * largura), int(landmarks[0][1] * altura))
        polegar_ponta = (int(landmarks[4][0] * largura), int(landmarks[4][1] * altura))
        mindinho_ponta = (int(landmarks[20][0] * largura), int(landmarks[20][1] * altura))
        
        # Se a ponta do polegar estiver à esquerda da ponta do mindinho na imagem,
        # é provavelmente a mão direita (e vice-versa)
        if polegar_ponta[0] < mindinho_ponta[0]:
            mao_corrigida = "Right"
        else:
            mao_corrigida = "Left"
            
        print(f"Correção de mão: Detectado='{handedness_detectado}', Corrigido='{mao_corrigida}'")
        print(f"Polegar: {polegar_ponta}, Mindinho: {mindinho_ponta}")
        
        return mao_corrigida
        
    except Exception as e:
        print(f"Erro na correção da mão: {e}")
        return handedness_detectado

def desenhar_medidas_simplificado(imagem, landmarks, dimensoes, contorno_quadrado=None):
    img_com_medidas = imagem.copy()
    altura, largura = imagem.shape[:2]
    
    if contorno_quadrado is not None:
        cv.drawContours(img_com_medidas, [contorno_quadrado], 0, (0, 0, 0), 3)  # Preto
    
    # Converter landmarks para pixels
    p5 = (int(landmarks[5][0] * largura), int(landmarks[5][1] * altura))
    p17 = (int(landmarks[17][0] * largura), int(landmarks[17][1] * altura))
    p0 = (int(landmarks[0][0] * largura), int(landmarks[0][1] * altura))
    p12 = (int(landmarks[12][0] * largura), int(landmarks[12][1] * altura))
    
    # Calcular pontos para as linhas usando os multiplicadores
    distancia_base_px = dimensoes.get('distancia_base_px', math.hypot(p17[0]-p5[0], p17[1]-p5[1]))
    
    # LINHA DA PALMA (pontos 5-17)
    cv.line(img_com_medidas, p5, p17, (255, 0, 0), 3)
    cv.putText(img_com_medidas, f"Palma: {dimensoes['Largura Palma']:.2f}cm",
              ((p5[0] + p17[0]) // 2 - 60, (p5[1] + p17[1]) // 2 - 15),
              cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    # LINHA DO COMPRIMENTO (ponto 0-12)
    cv.line(img_com_medidas, p0, p12, (0, 255, 0), 3)
    cv.putText(img_com_medidas, f"Comp: {dimensoes['Comprimento Mao']:.2f}cm",
              ((p0[0] + p12[0]) // 2 + 10, (p0[1] + p12[1]) // 2),
              cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Calcular vetor do comprimento (0->12)
    vetor_comprimento = (p12[0] - p0[0], p12[1] - p0[1])
    
    # Calcular vetor perpendicular (90 graus)
    vetor_perpendicular = (-vetor_comprimento[1], vetor_comprimento[0])
    
    # Normalizar o vetor perpendicular
    norma = math.hypot(vetor_perpendicular[0], vetor_perpendicular[1])
    if norma > 0:
        vetor_perpendicular = (vetor_perpendicular[0]/norma, vetor_perpendicular[1]/norma)
    
    # Calcular pontos da linha do pulso (centrada no ponto 0)
    largura_pulso_px = distancia_base_px * MULTIPLICADOR_PULSO
    metade_largura = largura_pulso_px / 2
    
    ponto_pulso_inicio = (
        int(p0[0] - vetor_perpendicular[0] * metade_largura),
        int(p0[1] - vetor_perpendicular[1] * metade_largura)
    )
    ponto_pulso_fim = (
        int(p0[0] + vetor_perpendicular[0] * metade_largura),
        int(p0[1] + vetor_perpendicular[1] * metade_largura)
    )
    
    cv.line(img_com_medidas, ponto_pulso_inicio, ponto_pulso_fim, (0, 165, 255), 3)
    cv.putText(img_com_medidas, f"Pulso: {dimensoes['Largura Pulso']:.2f}cm",
              ((p0[0] + ponto_pulso_inicio[0] + ponto_pulso_fim[0]) // 3, 
               (p0[1] + ponto_pulso_inicio[1] + ponto_pulso_fim[1]) // 3),
              cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
    
    # TODOS OS LANDMARKS (pontos da mão)
    for i, landmark in enumerate(landmarks):
        x = int(landmark[0] * largura)
        y = int(landmark[1] * altura)
        # Desenhar círculo em cada landmark
        cv.circle(img_com_medidas, (x, y), 4, (0, 0, 255), -1)  # Vermelho
        # Adicionar número do landmark (opcional)
        cv.putText(img_com_medidas, str(i), (x-5, y-5), 
                  cv.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
    
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
    try:
        print(f"Procurando modelo base em: {modelo_base_path}")
        
        if not os.path.exists(modelo_base_path):
            print(f"Modelo base não encontrado em: {modelo_base_path}")
            return False
        
        print(f"Modelo base encontrado no caminho original")
        
        # Carregar modelo base
        print(f"Carregando modelo STL: {modelo_base_path}")
        ortese_base = mesh.Mesh.from_file(modelo_base_path)
        print(f"Modelo carregado: {len(ortese_base.vectors)} triângulos")
        
        # Obter largura do pulso
        largura_pulso_cm = dimensoes.get("Largura Pulso", 0.0)
        if largura_pulso_cm == 0.0:
            print("Largura do pulso não encontrada nas dimensões")
            return False
        
        # Calcular fator de escala baseado no perímetro
        perimetro_paciente = 2.2 * largura_pulso_cm
        perimetro_template = 10.0
        fator_escala = perimetro_paciente / perimetro_template
        
        print(f"   Escalonamento STL:")
        print(f"   Pulso: {largura_pulso_cm:.2f}cm")
        print(f"   Perímetro: {perimetro_paciente:.2f}cm")
        print(f"   Fator: {fator_escala:.3f}")
        
        # CORREÇÃO SIMPLES: Escalonar os vetores diretamente
        ortese_escalada = mesh.Mesh(np.zeros(ortese_base.vectors.shape[0], dtype=mesh.Mesh.dtype))
        ortese_escalada.vectors = ortese_base.vectors * fator_escala
        
        # Espelhar para mão esquerda (se necessário)
        if handedness == "Left":
            print("Espelhando para mão esquerda")
            # Inverter o eixo X para espelhar
            ortese_escalada.vectors[:,:,0] *= -1.0
        
        # Garantir que o diretório de saída existe
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        # Salvar
        ortese_escalada.save(output_path)
        print(f"STL salvo: {output_path}")
        
        # Verificar se o arquivo foi realmente criado
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"Arquivo STL criado: {file_size} bytes")
            
            # Ler o arquivo salvo para verificar as dimensões
            stl_verificado = mesh.Mesh.from_file(output_path)
            if len(stl_verificado.vectors) > 0:
                min_x = stl_verificado.vectors[:,:,0].min()
                max_x = stl_verificado.vectors[:,:,0].max()
                min_y = stl_verificado.vectors[:,:,1].min()
                max_y = stl_verificado.vectors[:,:,1].max()
                min_z = stl_verificado.vectors[:,:,2].min()
                max_z = stl_verificado.vectors[:,:,2].max()
                
                print(f"Dimensões do STL gerado (verificado):")
                print(f"   X: {min_x:.2f} a {max_x:.2f} (largura: {max_x-min_x:.2f})")
                print(f"   Y: {min_y:.2f} a {max_y:.2f} (altura: {max_y-min_y:.2f})") 
                print(f"   Z: {min_z:.2f} a {max_z:.2f} (profundidade: {max_z-min_z:.2f})")
            else:
                print("Não foi possível verificar as dimensões do STL")
        else:
            print("Arquivo STL não foi criado")
            return False
        
        return True
        
    except Exception as e:
        print(f"Erro gerando STL: {e}")
        import traceback
        traceback.print_exc()
        return False

def pipeline_processamento_simplificado(caminho_imagem, caminho_stl_saida=None, modo_manual=False, modelo_base_path=None):
    try:
        print("Iniciando pipeline simplificado...")
        
        # Carregar imagem
        imagem = cv.imread(caminho_imagem)
        if imagem is None:
            print("Não foi possível carregar a imagem")
            return None, None, None, None, None
        
        print(f"Imagem carregada: {imagem.shape}")
        
        # 1. Detectar quadrado azul
        print("Detectando quadrado azul...")
        contorno_quadrado, dimensoes_quadrado, _ = detectar_quadrado_azul(imagem)
        
        escala_px_cm = 67.92  # Fallback
        if contorno_quadrado is not None:
            x, y, w, h = dimensoes_quadrado
            escala_px_cm = (w + h) / (2 * TAMANHO_QUADRADO_CM)
            print(f"Quadrado: {w}x{h} px, Escala: {escala_px_cm:.2f} px/cm")
        else:
            print("Quadrado não detectado, usando escala padrão")
        
        # 2. Detectar landmarks
        print("Detectando landmarks...")
        with mp_hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.5) as hands:
            imagem_rgb = cv.cvtColor(imagem, cv.COLOR_BGR2RGB)
            resultados = hands.process(imagem_rgb)
            
            if not resultados.multi_hand_landmarks:
                print("Nenhuma mão detectada")
                return None, None, None, None, None
            
            hand_landmarks = resultados.multi_hand_landmarks[0]
            landmarks = [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
            
            handedness_detectado = "Right"
            if resultados.multi_handedness:
                for classification in resultados.multi_handedness[0].classification:
                    handedness_detectado = classification.label
                    break
            
            print(f"{len(landmarks)} landmarks detectados - Mão detectada: {handedness_detectado}")
            
            # CORREÇÃO: Aplicar correção da detecção da mão
            handedness = corrigir_detecao_mao(landmarks, handedness_detectado, imagem.shape)
            print(f"Mão final: {handedness}")
        
        # 3. Calcular dimensões
        print("Calculando dimensões...")
        dimensoes = calcular_dimensoes_simplificado(landmarks, escala_px_cm, imagem.shape)
        if dimensoes is None:
            print("Erro no cálculo das dimensões")
            return None, None, None, None, None
        
        print(f"Dimensões calculadas:")
        for key, value in dimensoes.items():
            print(f"   {key}: {value}")
        
        # 4. Desenhar resultados
        print("Desenhando medidas e landmarks...")
        imagem_resultado = desenhar_medidas_simplificado(imagem, landmarks, dimensoes, contorno_quadrado)
        
        # 5. Gerar STL se solicitado
        stl_gerado = None
        if caminho_stl_saida and modelo_base_path:
            print("Gerando STL...")
            if gerar_stl_simplificado(dimensoes, handedness, caminho_stl_saida, modelo_base_path):
                stl_gerado = caminho_stl_saida
                print(f"STL gerado: {stl_gerado}")
            else:
                print("Falha ao gerar STL")
        else:
            print("Geração de STL não solicitada ou caminho do modelo base não fornecido")
        
        print("Pipeline simplificado concluído!")
        return stl_gerado, imagem_resultado, None, dimensoes, handedness
        
    except Exception as e:
        print(f"Erro no pipeline: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, None

def processar_imagem_ortese_api(imagem_bytes, modo_manual=False, modelo_base_stl_path=None):
    try:
        print("Processando imagem para API...")
        
        # Converter bytes para imagem
        nparr = np.frombuffer(imagem_bytes, np.uint8)
        imagem = cv.imdecode(nparr, cv.IMREAD_COLOR)
        
        if imagem is None:
            return {"erro": "Não foi possível carregar a imagem"}
        
        # Salvar temporariamente
        temp_img_path = os.path.join(UPLOAD_FOLDER, f"temp_processamento_{int(time.time())}.jpg")
        cv.imwrite(temp_img_path, imagem)
        
        # Gerar nome único para o STL
        temp_stl_path = os.path.join(UPLOAD_FOLDER, f"ortese_gerada_{int(time.time())}.stl")
        
        print(f"Processando imagem: {temp_img_path}")
        print(f"Saída STL: {temp_stl_path}")
        print(f"Modelo base: {modelo_base_stl_path}")
        
        # Processar
        stl_path, imagem_processada, _, dimensoes, handedness = pipeline_processamento_simplificado(
            temp_img_path, temp_stl_path, modo_manual, modelo_base_stl_path
        )
        
        # Limpar arquivo temporário da imagem
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
            # CORREÇÃO: Usar o mesmo arquivo, não copiar
            stl_filename = os.path.basename(stl_path)
            stl_url = f"/backend/models/{stl_filename}"
            
            print(f"STL disponível para download: {stl_url}")
            print(f"Caminho real do arquivo: {stl_path}")
            print(f"Tamanho do arquivo: {os.path.getsize(stl_path)} bytes")
        else:
            print("Nenhum STL gerado para download")
            if stl_path:
                print(f"❌ Arquivo STL não existe em: {stl_path}")
        
        return {
            "sucesso": True,
            "dimensoes": dimensoes,
            "handedness": handedness,
            "imagem_processada": imagem_base64,
            "stl_url": stl_url,
            "tipo_processamento": "simplificado"
        }
        
    except Exception as e:
        print(f"Erro no processamento: {e}")
        import traceback
        traceback.print_exc()
        return {"erro": f"Erro no processamento: {str(e)}"}