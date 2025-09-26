// Configuração dinâmica para produção/desenvolvimento
const IS_PRODUCTION = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
const API_BASE = IS_PRODUCTION 
    ? 'https://ortese-backend.onrender.com/api' 
    : 'http://localhost:5000/api';

console.log(`🌐 Ambiente: ${IS_PRODUCTION ? 'PRODUÇÃO' : 'DESENVOLVIMENTO'}`);
console.log(`🔗 API: ${API_BASE}`);

// Restante do seu código JavaScript aqui...
// (usar API_BASE em todas as chamadas fetch)