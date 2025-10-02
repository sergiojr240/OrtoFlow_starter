# test_stl_generation.py
import sys
import os

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(__file__))

from processamento_api import gerar_stl_simplificado

def test_stl_generation():
    print("🧪 Testando geração de STL...")
    
    # Dimensões de teste
    dimensoes_teste = {
        "Largura Pulso": 6.5,
        "Largura Palma": 8.2,
        "Comprimento Mao": 18.5,
        "Tamanho Ortese": "M"
    }
    
    # Caminhos de teste
    modelo_base_path = "backend/models/modelo_base.stl"
    output_path = "test_output.stl"
    
    # Testar geração
    success = gerar_stl_simplificado(dimensoes_teste, "Right", output_path, modelo_base_path)
    
    if success and os.path.exists(output_path):
        print(f"✅ Teste de STL bem-sucedido! Arquivo: {output_path}")
        # Limpar
        os.remove(output_path)
        return True
    else:
        print("❌ Teste de STL falhou")
        return False

if __name__ == "__main__":
    test_stl_generation()