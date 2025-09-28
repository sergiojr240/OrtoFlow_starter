// frontend/js/script.js - VERSÃO CORRIGIDA (SEM ERRO DE SYNTAX)
const IS_PRODUCTION = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
const API_BASE = IS_PRODUCTION 
    ? 'https://ortoflow-backend.onrender.com/api' 
    : 'http://localhost:5000/api';

console.log('Configuração carregada:', { ambiente: IS_PRODUCTION ? 'PRODUÇÃO' : 'DESENVOLVIMENTO', api: API_BASE });

let pacienteAtual = null;
let dadosPaciente = {};

// Inicialização quando o DOM carregar
document.addEventListener('DOMContentLoaded', function() {
    console.log('Sistema inicializado');
    inicializarEventos();
    // Removido o await daqui - testarConexaoAPI será chamada quando necessário
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
        console.log('📤 Enviando dados para API...');
        
        const response = await fetch(`${API_BASE}/cadastrar-paciente`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            mode: 'cors',
            body: JSON.stringify({ nome, idade, email })
        });

        console.log('📥 Resposta recebida:', response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Erro HTTP:', response.status, errorText);
            throw new Error(`Erro do servidor: ${response.status} - ${errorText}`);
        }

        const resultado = await response.json();
        console.log('✅ Dados recebidos:', resultado);

        if (resultado.sucesso) {
            // ... resto do código de sucesso permanece igual
            pacienteAtual = resultado.paciente_id;
            dadosPaciente = { nome, idade, email };

            document.getElementById('paciente-id').textContent = pacienteAtual;
            document.getElementById('upload-paciente-id').value = pacienteAtual;
            document.getElementById('paciente-atual-id').textContent = pacienteAtual;
            document.getElementById('paciente-atual-nome').textContent = nome;

            // QR Code
            if (resultado.qr_code) {
                document.getElementById('qrcode-container').innerHTML = 
                    `<img src="${resultado.qr_code}" alt="QR Code" style="max-width: 200px;">`;
            }

            // Folha padrão
            if (resultado.folha_padrao_url) {
                const linkFolha = document.getElementById('link-folha-padrao');
                linkFolha.href = `${API_BASE}${resultado.folha_padrao_url.replace('/api', '')}`;
            }

            document.getElementById('resultado-cadastro').classList.remove('hidden');
            botao.textContent = 'Cadastro Concluído!';

        } else {
            throw new Error(resultado.erro || 'Erro desconhecido no cadastro');
        }

    } catch (error) {
        console.error('💥 Erro completo:', error);
        alert('Erro no cadastro: ' + error.message);
        botao.textContent = textoOriginal;
        botao.disabled = false;
    }
}

// ===== PROCESSAMENTO DE IMAGEM COM BARRA DE PROGRESSO =====
async function processarImagem() {
    const arquivoInput = document.getElementById('imagem');
    const modoManual = document.getElementById('modo-manual').checked;

    if (!arquivoInput.files[0]) {
        alert('Por favor, selecione uma imagem primeiro');
        return;
    }

    const botao = document.querySelector('#form-upload button[type="submit"]');
    const textoOriginal = botao.textContent;
    
    // 🔥 ADICIONAR ELEMENTOS DE PROGRESSO
    let progressContainer = document.getElementById('progress-container');
    if (!progressContainer) {
        progressContainer = document.createElement('div');
        progressContainer.id = 'progress-container';
        progressContainer.className = 'progress-container';
        progressContainer.innerHTML = `
            <div class="progress-bar" id="progress-bar">0%</div>
            <div class="progress-text" id="progress-text">Iniciando processamento...</div>
            <div class="loading-container" id="loading-container">
                <div class="loading-spinner"></div>
                <p>Analisando imagem e detectando pontos da mão...</p>
            </div>
        `;
        document.querySelector('#form-upload').appendChild(progressContainer);
    }

    // Mostrar elementos de progresso
    progressContainer.style.display = 'block';
    document.getElementById('loading-container').style.display = 'block';
    document.getElementById('resultado-processamento').classList.add('hidden');
    
    botao.textContent = 'Processando...';
    botao.disabled = true;
    document.body.classList.add('processing');

    try {
        // 🔥 SIMULAR PROGRESSO
        await simularProgresso();
        
        const formData = new FormData();
        formData.append('imagem', arquivoInput.files[0]);
        formData.append('paciente_id', pacienteAtual || '');
        formData.append('modo_manual', modoManual.toString());

        atualizarProgresso(60, 'Enviando imagem para análise...');

        const response = await fetch(`${API_BASE}/processar-imagem`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        atualizarProgresso(80, 'Processando medidas...');

        const resultado = await response.json();
        
        atualizarProgresso(100, 'Processamento concluído!');

        // Pequeno delay para mostrar 100%
        await new Promise(resolve => setTimeout(resolve, 500));

        // Exibir resultados
        exibirResultadosProcessamento(resultado);

        botao.textContent = 'Processamento Concluído!';

    } catch (error) {
        console.error('Erro no processamento:', error);
        alert('Erro no processamento: ' + error.message);
        botao.textContent = textoOriginal;
    } finally {
        botao.disabled = false;
        document.body.classList.remove('processing');
        
        // Esconder barra de progresso após 2 segundos
        setTimeout(() => {
            const progressContainer = document.getElementById('progress-container');
            if (progressContainer) {
                progressContainer.style.display = 'none';
            }
        }, 2000);
    }
}

// 🔥 FUNÇÃO PARA SIMULAR PROGRESSO
function simularProgresso() {
    return new Promise(resolve => {
        let progress = 0;
        const interval = setInterval(() => {
            progress += 2;
            if (progress <= 50) {
                atualizarProgresso(progress, 'Preparando análise...');
            } else {
                clearInterval(interval);
                resolve();
            }
        }, 50);
    });
}

// 🔥 ATUALIZAR BARRA DE PROGRESSO
function atualizarProgresso(percent, texto) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    
    if (progressBar) {
        progressBar.style.width = percent + '%';
        progressBar.textContent = percent + '%';
    }
    
    if (progressText) {
        progressText.textContent = texto;
    }
}

// 🔥 EXIBIR RESULTADOS DO PROCESSAMENTO
function exibirResultadosProcessamento(resultado) {
    // Imagem processada
    const imagemProcessada = document.getElementById('imagem-processada');
    if (resultado.imagem_processada) {
        imagemProcessada.src = resultado.imagem_processada;
        imagemProcessada.style.display = 'block';
    } else {
        // Imagem placeholder quando não há imagem processada
        imagemProcessada.src = 'data:image/svg+xml;base64,PHN2Zy width="400" height="300" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#f0f0f0"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="Arial" font-size="16" fill="#666">Imagem processada não disponível</text></svg>';
        imagemProcessada.style.display = 'block';
    }

    // Dimensões
    if (resultado.dimensoes) {
        const dimensoesDiv = document.getElementById('dimensoes');
        dimensoesDiv.innerHTML = '';
        for (const [chave, valor] of Object.entries(resultado.dimensoes)) {
            dimensoesDiv.innerHTML += `<div><strong>${chave}:</strong> ${valor}</div>`;
        }
    }

    // Mão detectada
    if (resultado.handedness) {
        document.getElementById('dimensoes').innerHTML += 
            `<div><strong>Mão Detectada:</strong> ${resultado.handedness}</div>`;
    }

    // Tipo de processamento (para debug)
    if (resultado.tipo_processamento) {
        document.getElementById('dimensoes').innerHTML += 
            `<div style="font-size: 12px; color: #666; margin-top: 10px;"><em>Tipo: ${resultado.tipo_processamento}</em></div>`;
    }

    // Configurar download do STL
    if (resultado.stl_url) {
        document.getElementById('link-download-stl').href = 
            `${API_BASE}${resultado.stl_url.replace('/api', '')}`;
    }

    document.getElementById('resultado-processamento').classList.remove('hidden');
}

// ===== FUNÇÕES DE NAVEGAÇÃO =====
function avancarParaUpload() {
    console.log('Avançando para upload...');
    document.getElementById('etapa-cadastro').classList.remove('ativa');
    document.getElementById('etapa-upload').classList.add('ativa');
}

function gerarOrtese() {
    console.log('Gerando órtese...');
    document.getElementById('etapa-upload').classList.remove('ativa');
    document.getElementById('etapa-download').classList.add('ativa');
}

function reiniciarProcesso() {
    console.log('Reiniciando processo...');
    location.reload();
}

function verificarCadastro() {
    alert('Funcionalidade de verificação em desenvolvimento');
}

// ===== TESTE DE CONEXÃO =====
async function testarConexaoAPI() {
    try {
        console.log('Testando conexão com API...');
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            const data = await response.json();
            console.log('Conexão com API: OK', data);
            return true;
        } else {
            console.warn('API respondeu com erro:', response.status);
            return false;
        }
    } catch (error) {
        console.error('Erro na conexão com API:', error);
        return false;
    }
}

// Testar conexão quando necessário (não no carregamento automático)
function testarConexaoManual() {
    testarConexaoAPI().then(sucesso => {
        if (sucesso) {
            alert('Conexão com a API está funcionando!');
        } else {
            alert('Erro na conexão com a API. Verifique o console.');
        }
    });
}

// Adicionar botão de teste manual (opcional)
document.addEventListener('DOMContentLoaded', function() {
    // Adicionar botão de teste de conexão
    const testeBtn = document.createElement('button');
    testeBtn.textContent = 'Testar Conexão API';
    testeBtn.style.cssText = 'position: fixed; top: 10px; right: 10px; background: #007bff; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; z-index: 1000; font-size: 12px;';
    testeBtn.onclick = testarConexaoManual;
    document.body.appendChild(testeBtn);
});