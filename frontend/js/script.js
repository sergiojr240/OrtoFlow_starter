// frontend/js/script.js - VERSÃO COMPLETA E PROFISSIONAL
const IS_PRODUCTION = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
const API_BASE = IS_PRODUCTION 
    ? 'https://ortese-backend.onrender.com/api' 
    : 'http://localhost:5000/api';

let pacienteAtual = null;
let dadosPaciente = {};

document.addEventListener('DOMContentLoaded', function() {
    console.log('Sistema inicializado');
    inicializarEventos();
    testarConexaoAPI();
});

function inicializarEventos() {
    // Formulário de cadastro
    const formCadastro = document.getElementById('form-cadastro');
    if (formCadastro) {
        formCadastro.addEventListener('submit', function(e) {
            e.preventDefault();
            cadastrarPaciente();
        });
    }

    // Formulário de upload
    const formUpload = document.getElementById('form-upload');
    if (formUpload) {
        formUpload.addEventListener('submit', function(e) {
            e.preventDefault();
            processarImagem();
        });
    }

    // Preview de imagem
    const inputImagem = document.getElementById('imagem');
    if (inputImagem) {
        inputImagem.addEventListener('change', function(e) {
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
    }
}

// ===== CADASTRO DE PACIENTE =====
async function cadastrarPaciente() {
    const nome = document.getElementById('nome').value.trim();
    const idade = document.getElementById('idade').value.trim();
    const email = document.getElementById('email').value.trim();

    if (!nome || !idade) {
        alert('Por favor, preencha nome e idade');
        return;
    }

    const botao = document.querySelector('#form-cadastro button[type="submit"]');
    const textoOriginal = botao.textContent;
    botao.textContent = 'Cadastrando...';
    botao.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/cadastrar-paciente`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ nome, idade, email })
        });

        const resultado = await response.json();

        if (resultado.sucesso) {
            pacienteAtual = resultado.paciente_id;
            dadosPaciente = { nome, idade, email };

            // Atualizar interface
            document.getElementById('paciente-id').textContent = pacienteAtual;
            document.getElementById('upload-paciente-id').value = pacienteAtual;
            document.getElementById('paciente-atual-id').textContent = pacienteAtual;
            document.getElementById('paciente-atual-nome').textContent = nome;

            // QR Code real
            if (resultado.qr_code) {
                document.getElementById('qrcode-container').innerHTML = 
                    `<img src="${resultado.qr_code}" alt="QR Code" style="max-width: 200px;">`;
            }

            // Link para folha padrão
            if (resultado.folha_padrao_url) {
                document.getElementById('link-folha-padrao').href = 
                    `${API_BASE}${resultado.folha_padrao_url.replace('/api', '')}`;
            }

            document.getElementById('resultado-cadastro').classList.remove('hidden');
            botao.textContent = 'Cadastro Concluído!';

        } else {
            throw new Error(resultado.erro || 'Erro no cadastro');
        }

    } catch (error) {
        console.error('Erro no cadastro:', error);
        alert('Erro no cadastro: ' + error.message);
        botao.textContent = textoOriginal;
        botao.disabled = false;
    }
}

// ===== PROCESSAMENTO DE IMAGEM =====
async function processarImagem() {
    const arquivoInput = document.getElementById('imagem');
    const modoManual = document.getElementById('modo-manual').checked;

    if (!arquivoInput.files[0]) {
        alert('Por favor, selecione uma imagem primeiro');
        return;
    }

    const botao = document.querySelector('#form-upload button[type="submit"]');
    const textoOriginal = botao.textContent;
    botao.textContent = 'Processando...';
    botao.disabled = true;

    try {
        const formData = new FormData();
        formData.append('imagem', arquivoInput.files[0]);
        formData.append('paciente_id', pacienteAtual || '');
        formData.append('modo_manual', modoManual.toString());

        const response = await fetch(`${API_BASE}/processar-imagem`, {
            method: 'POST',
            body: formData
        });

        const resultado = await response.json();

        if (!response.ok) {
            throw new Error(resultado.erro || `Erro: ${response.status}`);
        }

        // Exibir resultados
        if (resultado.imagem_processada) {
            document.getElementById('imagem-processada').src = resultado.imagem_processada;
        }

        if (resultado.dimensoes) {
            const dimensoesDiv = document.getElementById('dimensoes');
            dimensoesDiv.innerHTML = '';
            for (const [chave, valor] of Object.entries(resultado.dimensoes)) {
                dimensoesDiv.innerHTML += `<div><strong>${chave}:</strong> ${valor}</div>`;
            }
        }

        if (resultado.handedness) {
            document.getElementById('dimensoes').innerHTML += 
                `<div><strong>Mão Detectada:</strong> ${resultado.handedness}</div>`;
        }

        // Configurar download do STL se disponível
        if (resultado.stl_url) {
            document.getElementById('link-download-stl').href = 
                `${API_BASE}${resultado.stl_url.replace('/api', '')}`;
        }

        document.getElementById('resultado-processamento').classList.remove('hidden');
        botao.textContent = 'Processamento Concluído!';

    } catch (error) {
        console.error('Erro no processamento:', error);
        alert('Erro no processamento: ' + error.message);
        botao.textContent = textoOriginal;
    } finally {
        botao.disabled = false;
    }
}

// ===== FUNÇÕES DE NAVEGAÇÃO =====
function avancarParaUpload() {
    document.getElementById('etapa-cadastro').classList.remove('ativa');
    document.getElementById('etapa-upload').classList.add('ativa');
}

function gerarOrtese() {
    document.getElementById('etapa-upload').classList.remove('ativa');
    document.getElementById('etapa-download').classList.add('ativa');
}

function reiniciarProcesso() {
    location.reload();
}

function verificarCadastro() {
    alert('Funcionalidade de verificação em desenvolvimento');
}

// ===== UTILITÁRIOS =====
async function testarConexaoAPI() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            console.log('Conexão com API: OK');
        } else {
            console.warn('API respondeu com erro:', response.status);
        }
    } catch (error) {
        console.error('Erro na conexão com API:', error);
    }
}