# test_processing.py
import cv2
import mediapipe as mp
import sys

def test_mediapipe():
    print("🧪 Testando MediaPipe...")
    try:
        mp_hands = mp.solutions.hands
        print("✅ MediaPipe importado com sucesso")
        
        with mp_hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.5) as hands:
            print("✅ Hands detector inicializado")
            
        return True
    except Exception as e:
        print(f"❌ Erro no MediaPipe: {e}")
        return False

def test_opencv():
    print("🧪 Testando OpenCV...")
    try:
        print(f"✅ OpenCV versão: {cv2.__version__}")
        return True
    except Exception as e:
        print(f"❌ Erro no OpenCV: {e}")
        return False

if __name__ == "__main__":
    print("Iniciando testes...")
    opencv_ok = test_opencv()
    mediapipe_ok = test_mediapipe()
    
    if opencv_ok and mediapipe_ok:
        print("🎉 Todos os testes passaram!")
    else:
        print("❌ Alguns testes falharam")
        sys.exit(1)