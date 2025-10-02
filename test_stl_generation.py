# test_final.py
import os
import sys
from processamento_api import gerar_stl_simplificado

def test_stl_generation_final():
    """Teste final da geração do STL"""
    print("🧪 TESTE FINAL DA GERAÇÃO STL")
    print("=" * 50)
    
    # Dimensões de teste
    dimensoes_teste = {
        "Largura Pulso": 6.5,
        "Largura Palma": 8.2, 
        "Comprimento Mao": 18.5,
        "Tamanho Ortese": "M"
    }
    
    # Caminho do modelo base
    modelo_base_path = "C:/Users/sergi/OneDrive/Área de Trabalho/OrtoFlow_starter/backend/models/modelo_base.stl"
    
    if not os.path.exists(modelo_base_path):
        print(f"❌ Modelo base não encontrado em: {modelo_base_path}")
        return False
    
    # Caminho de saída
    output_path = "C:/Users/sergi/OneDrive/Área de Trabalho/OrtoFlow_starter/backend/models/test_final.stl"
    
    print(f"📁 Modelo base: {modelo_base_path}")
    print(f"📁 Saída: {output_path}")
    print(f"📏 Dimensões: {dimensoes_teste}")
    
    # Testar geração
    success = gerar_stl_simplificado(dimensoes_teste, "Right", output_path, modelo_base_path)
    
    if success and os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        print(f"✅ Teste bem-sucedido! Arquivo: {output_path} ({file_size} bytes)")
        
        # Verificar o conteúdo
        try:
            from stl import mesh
            test_mesh = mesh.Mesh.from_file(output_path)
            print(f"✅ STL válido: {len(test_mesh.vectors)} triângulos")
            
            # Limpar
            os.remove(output_path)
            return True
        except Exception as e:
            print(f"❌ STL inválido: {e}")
            return False
    else:
        print("❌ Teste falhou")
        return False

if __name__ == "__main__":
    test_stl_generation_final()