from flask import Flask, request, session
from flask_socketio import SocketIO, emit
from google import genai
from google.genai import types
from dotenv import load_dotenv
from uuid import uuid4
import os
import re
import eventlet

# ---------------- KEY MANAGER ----------------
import ast

class KeyManager:
    """
    Gerencia um pool de chaves de API, permitindo a troca para a próxima
    chave disponível em caso de falha ou uso excessivo.
    """
    def __init__(self, key_env_var="GEMINI_API_KEYS"):
        load_dotenv()
        self.keys = self._load_keys(key_env_var)
        self.current_key_index = 0
        if not self.keys:
            raise ValueError("Nenhuma chave de API encontrada na variável de ambiente.")

    def _load_keys(self, key_env_var):
        keys_str = os.getenv(key_env_var)
        if keys_str:
            try:
                return ast.literal_eval(keys_str)
            except (ValueError, SyntaxError) as e:
                print(f"Erro ao ler as chaves do .env: {e}")
                return []
        return []

    def get_current_key(self):
        return self.keys[self.current_key_index]

    def switch_key(self):
        if len(self.keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.keys)
            print(f"🔑 Chave de API trocada. Agora usando índice {self.current_key_index}")
        else:
            print("⚠️ Apenas uma chave disponível, não há outra para trocar.")

    def get_all_keys(self):
        return self.keys
# -------------------------------------------------

load_dotenv()

instrucoes = """Você é o OrtoFix, um assistente virtual amigável, especialista em ortografia da Língua Portuguesa, e foi criado para ajudar alunos do ensino fundamental e médio. Sua principal função é tirar dúvidas de forma clara, objetiva e educativa.

Sua persona deve ser a do mascote OrtoFix: paciente, encorajador e divertido.

Quando um aluno fizer uma pergunta, siga estas regras:
1. Responda de forma direta, sem divagar.
2. Forneça exemplos simples e práticos para ilustrar a regra ortográfica.
3. Use uma linguagem acessível e motivadora.
4. Se a pergunta for sobre uma regra gramatical, comece com um resumo da regra antes de dar o exemplo.
5. Se a pergunta for sobre uma palavra específica, dê a ortografia correta e uma breve explicação.
6. Seja breve, as respostas não devem ser longas

Se o aluno fizer uma pergunta sobre assuntos que não sejam de ortografia, responda de forma educada que sua especialidade é a ortografia da Língua Portuguesa e que você não tem conhecimento sobre o assunto. Só fale olá no começo da conversa, depois que o aluno estiver falando com você nao precisa ficar falando olá toda hora que começar uma nova frase. DE FORMA ALGUMA coloque ASTERISCOS nas respostas, volte apenas o texto. A RESPOSTA NAO PODE TER ASTERISCOS, TIRE TODOS OS ASTERISCOS POSSIVEIS
"""

# -------- Inicializa KeyManager e client --------
key_manager = KeyManager()
client = genai.Client(api_key=key_manager.get_current_key())
# ------------------------------------------------

app = Flask(__name__)
app.secret_key = "chave"
socketio = SocketIO(app, cors_allowed_origins="*")

active_chats = {}

# ---------------- FUNÇÃO PARA LIMPAR MARKDOWN ----------------
def limpar_formatacao(texto: str) -> str:
    texto = re.sub(r"[*_#`]", "", texto)
    return texto.strip()

# ---------------- CHAT ----------------
def get_user_chat():
    if 'session_id' not in session:
        session['session_id'] = str(uuid4())
        print(f"Nova sessão Flask criada: {session['session_id']}")

    session_id = session['session_id']

    if session_id not in active_chats:
        print(f"Criando novo chat Gemini para session_id: {session_id}")
        chat_session = client.chats.create(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(system_instruction=instrucoes)
        )
        active_chats[session_id] = chat_session
        print(f"Novo chat Gemini criado e armazenado para {session_id}")

    return active_chats[session_id]

# ---------------- SOCKETS ----------------
@socketio.on('connect')
def handle_connect():
    print(f"Cliente conectado: {request.sid}")
    try:
        get_user_chat()
        user_session_id = session.get('session_id', 'N/A')
        emit('status_conexao', {'data': 'Conectado com sucesso!', 'session_id': user_session_id})
    except Exception as e:
        app.logger.error(f"Erro durante o evento connect para {request.sid}: {e}", exc_info=True)
        emit('erro', {'erro': 'Falha ao inicializar a sessão de chat no servidor.'})

@socketio.on('enviar_mensagem')
def handle_enviar_mensagem(data):
    global client
    try:
        mensagem_usuario = data.get("mensagem")
        if not mensagem_usuario:
            emit('erro', {"erro": "Mensagem não pode ser vazia."})
            return

        try:
            user_chat = get_user_chat()
            resposta_gemini = user_chat.send_message(mensagem_usuario)

            resposta_texto = (
                resposta_gemini.text
                if hasattr(resposta_gemini, 'text')
                else resposta_gemini.candidates[0].content.parts[0].text
            )

            resposta_texto = limpar_formatacao(resposta_texto)

            emit('nova_mensagem', {
                "remetente": "bot",
                "texto": resposta_texto,
                "session_id": session.get('session_id')
            })

        except Exception as e:
            # Se for erro de quota/limite (ex.: 429 Too Many Requests)
            if "429" in str(e) or "quota" in str(e).lower():
                key_manager.switch_key()
                client = genai.Client(api_key=key_manager.get_current_key())
                emit('erro', {"erro": "Chave trocada automaticamente, tente novamente."})
            else:
                emit('erro', {"erro": f"Ocorreu um erro no servidor: {str(e)}"})

    except Exception as e:
        app.logger.error(f"Erro em handle_enviar_mensagem: {e}", exc_info=True)
        emit('erro', {"erro": f"Ocorreu um erro inesperado: {str(e)}"})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Cliente desconectado: {request.sid}, session_id: {session.get('session_id', 'N/A')}")

if __name__ == "__main__":
    socketio.run(app, debug=True)
