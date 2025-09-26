// frontend/js/script.js - VERSÃO CORRIGIDA
console.log('🔧 Script carregado!');

// Configuração dinâmica para produção/desenvolvimento
const IS_PRODUCTION = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
const API_BASE = IS_PRODUCTION 
    ? 'https://ortoflow-backend.onrender.com/api' 
    : 'http://localhost:5000/api';

console.log('🌐 Ambiente:', IS_PRODUCTION ? 'PRODUÇÃO' : 'DESENVOLVIMENTO');
console.log('🔗 API Base:', API_BASE);

// Estado global
let pacienteAtual = null;

// Aguardar o DOM carregar completamente
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 DOM carregado, inicializando...');
    inicializarEventos();
});

function inicializarEventos() {
    // Formulário de cadastro
    const formCadastro = document.getElementById('form-cadastro');
    if (formCadastro) {
        formCadastro.addEventListener('submit', function(e) {
            e.preventDefault(); // IMPEDIR RECARREGAMENTO DA PÁGINA
            console.log('📝 Formulário de cadastro submetido');
            cadastrarPaciente();
        });
    } else {
        console.error('❌ Formulário de cadastro não encontrado');
    }

    // Formulário de upload
    const formUpload = document.getElementById('form-upload');
    if (formUpload) {
        formUpload.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('📸 Formulário de upload submetido');
            processarImagem();
        });
    }

    // Verificar cadastro existente
    const btnVerificar = document.querySelector('button[onclick*="verificarCadastro"]');
    if (btnVerificar) {
        btnVerificar.addEventListener('click', verificarCadastro);
    }
}

async function cadastrarPaciente() {
    const nome = document.getElementById('nome').value;
    const idade = document.getElementById('idade').value;
    const email = document.getElementById('email').value;

    if (!nome || !idade) {
        alert('❌ Por favor, preencha nome e idade');
        return;
    }

    console.log('👤 Cadastrando paciente:', { nome, idade, email });

    try {
        // Simular cadastro (substituir por API real depois)
        pacienteAtual = 'P' + Math.random().toString(36).substr(2, 8).toUpperCase();
        
        // Atualizar interface
        document.getElementById('paciente-id').textContent = pacienteAtual;
        document.getElementById('upload-paciente-id').value = pacienteAtual;
        
        // Mostrar QR Code simulado
        exibirQRCode(pacienteAtual);
        
        // Mostrar seção de resultados
        document.getElementById('resultado-cadastro').classList.remove('hidden');
        
        console.log('✅ Paciente cadastrado:', pacienteAtual);
        
    } catch (error) {
        console.error('❌ Erro no cadastro:', error);
        alert('Erro no cadastro: ' + error.message);
    }
}

function exibirQRCode(pacienteId) {
    const container = document.getElementById('qrcode-container');
    if (container) {
        container.innerHTML = `
            <div style="border: 2px solid #333; padding: 15px; display: inline-block; background: white;">
                <div style="font-family: monospace; font-size: 24px; letter-spacing: 4px;">
                    ██████████
                    ██      ██
                    ██  ██  ██
                    ██      ██
                    ██████████
                </div>
                <div style="margin-top: 10px; font-weight: bold;">ID: ${pacienteId}</div>
            </div>
        `;
    }
}

function avancarParaUpload() {
    console.log('➡️ Avançando para upload...');
    document.getElementById('etapa-cadastro').classList.remove('ativa');
    document.getElementById('etapa-upload').classList.add('ativa');
}

function verificarCadastro() {
    const pacienteId = document.getElementById('paciente-id-existente').value;
    console.log('🔍 Verificando cadastro:', pacienteId);
    alert('Funcionalidade de verificação será implementada em breve!');
}

async function processarImagem() {
    const arquivoInput = document.getElementById('imagem');
    if (!arquivoInput.files[0]) {
        alert('📸 Por favor, selecione uma imagem!');
        return;
    }

    console.log('🔄 Processando imagem...');
    
    // Simular processamento
    setTimeout(() => {
        const dimensoesExemplo = {
            "Largura Pulso": "6.5 cm",
            "Largura Palma": "8.2 cm", 
            "Comprimento Mão": "18.7 cm",
            "Tamanho Órtese": "M"
        };

        // Atualizar interface
        const dimensoesDiv = document.getElementById('dimensoes');
        if (dimensoesDiv) {
            dimensoesDiv.innerHTML = '';
            for (const [chave, valor] of Object.entries(dimensoesExemplo)) {
                dimensoesDiv.innerHTML += `<div><strong>${chave}:</strong> ${valor}</div>`;
            }
        }

        document.getElementById('resultado-processamento').classList.remove('hidden');
        console.log('✅ Processamento simulado concluído');
    }, 2000);
}

function gerarOrtese() {
    console.log('🖨️ Gerando órtese...');
    document.getElementById('etapa-upload').classList.remove('ativa');
    document.getElementById('etapa-download').classList.add('ativa');
}

function reiniciarProcesso() {
    console.log('🔄 Reiniciando processo...');
    location.reload();
}

// Preview de imagem
document.getElementById('imagem')?.addEventListener('change', function(e) {
    const arquivo = e.target.files[0];
    if (arquivo) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = document.getElementById('imagem-processada');
            if (img) {
                img.src = e.target.result;
                img.style.display = 'block';
            }
        };
        reader.readAsDataURL(arquivo);
    }
});

// Testar conexão com API
async function testarConexaoAPI() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Conexão com API OK:', data);
        } else {
            console.warn('⚠️ API respondeu com erro:', response.status);
        }
    } catch (error) {
        console.error('❌ Erro na conexão com API:', error);
    }
}

// Testar ao carregar
testarConexaoAPI();