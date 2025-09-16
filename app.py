from flask import Flask, request, session
from flask_socketio import SocketIO, emit #Permite comunicação em tempo real (WebSocket).
from google import genai
from google.genai import types
from dotenv import load_dotenv
from uuid import uuid4 #Gera identificadores únicos para sessões de usuário.
import os




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

Exemplos de interação:

ENTRADA DO ALUNO: "Qual a diferença entre 'mas' e 'mais'?"
RESPOSTA IDEAL: "'Mas' é uma conjunção que indica oposição (exemplo: 'Eu estudei, mas não fui bem na prova'). Já 'mais' é um advérbio de intensidade, usado para indicar quantidade (exemplo: 'Quero mais um pedaço de bolo'). Ao terminar de explicar, pergunte ao aluno se ele conseguiu entender e se ele precisa de mais alguma ajuda"

ENTRADA DO ALUNO: "Como acentuar a palavra 'cafe'?"
RESPOSTA IDEAL: "A palavra 'café' leva acento agudo no 'é'. A regra é que as palavras oxítonas terminadas em 'a', 'e', 'o' (seguidas ou não de 's') são acentuadas.Ao terminar de explicar, pergunte ao aluno se ele conseguiu entender e se ele precisa de mais alguma ajuda !"

Se o aluno fizer uma pergunta sobre assuntos que não sejam de ortografia, responda de forma educada que sua especialidade é a ortografia da Língua Portuguesa e que você não tem conhecimento sobre o assunto. Só fale olá no começo da conversa, depois que o aluno estiver falando com você nao precisa ficar falando olá toda hora que começar uma nova frase. DE FORMA ALGUMA coloque ASTERISCOS nas respostas, volte apenas o texto. A RESPOSTA NAO PODE TER ASTERISCOS, TIRE TODOS OS ASTERISCOS POSSIVEIS   """

client = genai.Client(api_key=os.getenv("API_KEY"))

app = Flask(__name__)
app.secret_key = "chave"
socketio = SocketIO(app, cors_allowed_origins="*") #Habilita comunicação WebSocket e permite conexões de qualquer origem (ideal para testes).

active_chats = {}




def get_user_chat():
    # Verifica se a sessão do Flask já tem um session_id associado ao usuário
    if 'session_id' not in session:
        # Se não tiver, cria um novo identificador único usando uuid4 e armazena
        session['session_id'] = str(uuid4())
        print(f"Nova sessão Flask criada: {session['session_id']}")
    # Recupera o session_id atual da sessão
    session_id = session['session_id']
    # Verifica se não existe um chat associado a este session_id no dicionário
    if session_id not in active_chats:
        print(f"Criando novo chat Gemini para session_id: {session_id}")
        try:
            # Cria um novo chat com o modelo Gemini especificado e com as instruções
            chat_session = client.chats.create(
                model="gemini-2.0-flash", # Verifica se o modelo suporta chat
                config=types.GenerateContentConfig(system_instruction=instrucoes)
            )
            # Armazena o chat criado no dicionário active_chats, associando ao session_id
            active_chats[session_id] = chat_session
            print(f"Novo chat Gemini criado e armazenado para {session_id}")
        except Exception as e:
            # Registra o erro no log da aplicação e relança a exceção para ser tratada
            app.logger.error(f"Erro ao criar chat Gemini para {session_id}: {e}")
            raise
    # Verifica se o chat existe mas foi perdido (por exemplo, reinício do servidor)
    if session_id in active_chats and active_chats[session_id] is None:
        print(f"Recriando chat Gemini para session_id existente (estava None)")
        try:
            # Recria o chat da mesma forma, com o mesmo modelo e instruções
            chat_session = client.chats.create(
                model="gemini-2.0-flash",
                config=types.GenerateContentConfig(system_instruction=instrucoes)
            )
            # Armazena novamente o chat criado no active_chats
            active_chats[session_id] = chat_session
        except Exception as e:
            # Registra o erro e relança a exceção
            app.logger.error(f"Erro ao recriar chat Gemini para {session_id}: {e}")
            raise
    # Retorna o chat associado ao session_id do usuário, para ser usado nas requisições
    return active_chats[session_id]

@socketio.on('connect')
def handle_connect():
    """
    Chamado quando um cliente se conecta via WebSocket.
    """
    print(f"Cliente     : {request.sid}")
# Tenta obter/criar o chat ao conectar para inicializar a sessão Flask se necessário
    try:
        get_user_chat()
        user_session_id = session.get('session_id', 'N/A')
        print(f"Sessão Flask para {request.sid} usa session_id: {user_session_id}")
        emit('status_conexao', {'data': 'Conectado com sucesso!', 'session_id': user_session_id})
    except Exception as e:
        app.logger.error(f"Erro durante o evento connect para {request.sid}: {e}", exc_info=True)
        emit('erro', {'erro': 'Falha ao inicializar a sessão de chat no servidor.'})


@socketio.on('enviar_mensagem')
def handle_enviar_mensagem(data):
    """
    Manipulador para o evento 'enviar_mensagem' emitido pelo cliente.
    'data' deve ser um dicionário, por exemplo: {'mensagem': 'Olá, mundo!'}
    """
    try:
        mensagem_usuario = data.get("mensagem")
        app.logger.info(f"Mensagem recebida de {session.get('session_id', request.sid)}: {mensagem_usuario}")
        if not mensagem_usuario:
            emit('erro', {"erro": "Mensagem não pode ser vazia."})
            return

        user_chat = get_user_chat()
        if user_chat is None:
            emit('erro', {"erro": "Sessão de chat não pôde ser estabelecida."})
            return

        # Envia a mensagem para o Gemini
        resposta_gemini = user_chat.send_message(mensagem_usuario)
        # Extrai o texto da resposta
        resposta_texto = (
            resposta_gemini.text
            if hasattr(resposta_gemini, 'text')
            else resposta_gemini.candidates[0].content.parts[0].text
        )
        
        # *** LÓGICA REVERTIDA AQUI ***
        # Emite a resposta como uma string única (com \n) de volta para o cliente
        emit('nova_mensagem', {
            "remetente": "bot",
            "texto": resposta_texto,  # Enviando a string completa
            "session_id": session.get('session_id')
        })
        app.logger.info(f"Resposta enviada para {session.get('session_id', request.sid)}: {resposta_texto}")
    except Exception as e:
        app.logger.error(
            f"Erro ao processar 'enviar_mensagem' para {session.get('session_id', request.sid)}: {e}",
            exc_info=True
        )
        emit('erro', {"erro": f"Ocorreu um erro no servidor: {str(e)}"})


@socketio.on('disconnect')
def handle_disconnect():
    print(f"Cliente desconectado: {request.sid}, session_id: {session.get('session_id', 'N/A')}")


if __name__ == "__main__":
    socketio.run(app, debug=True)