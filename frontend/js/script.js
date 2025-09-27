// frontend/js/script.js - COM TRATAMENTO CORS MELHORADO
const IS_PRODUCTION = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
const API_BASE = IS_PRODUCTION 
    ? 'https://ortoflow-backend.onrender.com/api' 
    : 'http://localhost:5000/api';

console.log('🌐 Configuração:', {
    ambiente: IS_PRODUCTION ? 'PRODUÇÃO' : 'DESENVOLVIMENTO',
    api: API_BASE,
    frontend: window.location.origin
});

// Configuração global do fetch
const fetchConfig = {
    mode: 'cors',
    credentials: 'omit',
    headers: {
        'Content-Type': 'application/json',
    }
};

let pacienteAtual = null;
let dadosPaciente = {};

// ... resto do código permanece igual, mas atualize as chamadas fetch:

// EXEMPLO: Na função cadastrarPaciente, substitua:
const response = await fetch(`${API_BASE}/cadastrar-paciente`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({ nome, idade, email })
});

// POR:
const response = await fetch(`${API_BASE}/cadastrar-paciente`, {
    ...fetchConfig,
    method: 'POST',
    body: JSON.stringify({ nome, idade, email })
});