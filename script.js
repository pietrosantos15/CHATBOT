const uploadButton = document.getElementById('upload-button');
const imageInput = document.getElementById('image-input');

document.addEventListener('DOMContentLoaded', () => {
    let socket = null;
    const chatBox = document.getElementById('chat-box');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const connectionStatus = document.getElementById('connection-status');
    const iniciarBtn = document.getElementById('iniciarBtn');
    const encerrarBtn = document.getElementById('encerrarBtn');
    const uploadButton = document.getElementById('upload-button');
    const imageInput = document.getElementById('image-input');
    let userSessionId = null;

    // Função para adicionar mensagens no chat
    function addMessageToChat(sender, text, type = 'normal') {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message');

        let senderName = '';
        if (sender.toLowerCase() === 'user') {
            messageElement.classList.add('user-message');
            senderName = 'Você';
        } else if (sender.toLowerCase() === 'bot') {
            messageElement.classList.add('bot-message');
            senderName = 'Bot';
        } else {
            messageElement.classList.add('status-message');
        }

        if (type === 'error') {
            messageElement.classList.add('error-text');
            senderName = 'Erro';
        } else if (type === 'status') {
            messageElement.classList.add('status-text');
            senderName = 'Status';
        }

        const senderSpan = document.createElement('strong');
        senderSpan.textContent = `${senderName}: `;
        messageElement.appendChild(senderSpan);
        
        const textSpan = document.createElement('span');

        // *** NOVA LÓGICA AQUI ***
        // Se a mensagem for do bot, troque as quebras de linha por tags <br>
        if (sender.toLowerCase() === 'bot') {
            // Usamos .innerHTML para que o navegador interprete a tag <br>
            textSpan.innerHTML = text.replace(/\n/g, '<br>');
        } else {
            // Para outras mensagens, usamos .textContent por segurança e simplicidade
            textSpan.textContent = text;
        }

        messageElement.appendChild(textSpan);
        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // Função para habilitar/desabilitar o chat
    function setChatEnabled(enabled) {
        messageInput.disabled = !enabled;
        sendButton.disabled = !enabled;
    }

    // Inicialmente desativa o chat
    setChatEnabled(false);
    connectionStatus.textContent = 'Desconectado';
    connectionStatus.className = 'status-offline';
    addMessageToChat('Status', 'Clique em "Iniciar conversa" para começar.', 'status');

    // Função para conectar ao servidor
    function iniciarConversa() {
        if (socket && socket.connected) return;
        socket = io('http://localhost:5000');
        socket.on('connect', () => {
            console.log('Conectado ao servidor Socket.IO! SID:', socket.id);
            connectionStatus.textContent = 'Conectado';
            connectionStatus.className = 'status-online';
            addMessageToChat('Status', 'Conectado ao servidor de chat.', 'status');
            setChatEnabled(true);
        });
        socket.on('disconnect', () => {
            console.log('Desconectado do servidor Socket.IO.');
            connectionStatus.textContent = 'Desconectado';
            connectionStatus.className = 'status-offline';
            addMessageToChat('Status', 'Você foi desconectado.', 'status');
            setChatEnabled(false);
        });
        socket.on('status_conexao', (data) => {
            if (data.session_id) {
                userSessionId = data.session_id;
            }
        });
        socket.on('nova_mensagem', (data) => {
            addMessageToChat(data.remetente, data.texto);
        });
        socket.on('erro', (data) => {
            addMessageToChat('Erro', data.erro, 'error');
        });
    }

    // Função para encerrar a conversa
    function encerrarConversa() {
        if (socket && socket.connected) {
            socket.disconnect();
            setChatEnabled(false);
            addMessageToChat('Status', 'Conversa encerrada pelo usuário.', 'status');
        }
    }

    // Enviar mensagem para o servidor
    function sendMessageToServer() {
        const messageText = messageInput.value.trim();
        if (messageText === '') return;
        if (socket && socket.connected) {
            addMessageToChat('user', messageText);
            socket.emit('enviar_mensagem', { mensagem: messageText });
            messageInput.value = '';
            messageInput.focus();
        } else {
            addMessageToChat('Erro', 'Não conectado ao servidor.', 'error');
        }
    }

    // Eventos dos botões
    iniciarBtn.addEventListener('click', iniciarConversa);
    encerrarBtn.addEventListener('click', encerrarConversa);
    sendButton.addEventListener('click', sendMessageToServer);
    messageInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessageToServer();
        }
    });
});



document.addEventListener('DOMContentLoaded', () => {
    const chatIcon = document.getElementById('chatbot-popup-icon');
    const chatContainer = document.getElementById('chatbot-container');

    // Verifica se o ícone foi encontrado no HTML
    if (chatIcon) {
        console.log('Ícone do chatbot encontrado.');

        chatIcon.addEventListener('click', () => {
            // Alterna a classe para mostrar ou esconder o chat
            if (chatContainer) {
                chatContainer.classList.toggle('chatbot-container-hidden');
                chatContainer.classList.toggle('chatbot-container-visible');
            }
            
            // Opcional: esconde o ícone quando o chat está aberto
            if (chatContainer.classList.contains('chatbot-container-visible')) {
                chatIcon.style.display = 'none';
            }
        });
    } else {
        console.error('Erro: Ícone do chatbot não encontrado. Verifique o ID "chatbot-popup-icon" no seu HTML.');
    }

    // Lógica para o botão de fechar, caso você tenha um
    const closeButton = document.getElementById('close-chat-button');
    if (closeButton) {
        closeButton.addEventListener('click', () => {
            if (chatContainer) {
                chatContainer.classList.remove('chatbot-container-visible');
                chatContainer.classList.add('chatbot-container-hidden');
            }
            if (chatIcon) {
                chatIcon.style.display = 'block';
            }
        });
    }
});