import os
import ast
from dotenv import load_dotenv

class KeyManager:
    """
    Gerencia um pool de chaves de API, permitindo a troca para a próxima
    chave disponível em caso de falha ou uso excessivo.
    """
    def __init__(self, key_env_var="GEMINI_API_KEYS"):
        """
        Inicializa o gerenciador de chaves.

        Args:
            key_env_var (str): Nome da variável de ambiente que contém a lista de chaves.
        """
        load_dotenv()
        self.keys = self._load_keys(key_env_var)
        self.current_key_index = 0
        if not self.keys:
            raise ValueError("Nenhuma chave de API encontrada na variável de ambiente.")

    def _load_keys(self, key_env_var):
        """
        Carrega a lista de chaves do arquivo .env.
        """
        keys_str = os.getenv(key_env_var)
        if keys_str:
            try:
                # Usa ast.literal_eval para converter a string em uma lista Python
                return ast.literal_eval(keys_str)
            except (ValueError, SyntaxError) as e:
                print(f"Erro ao ler as chaves do .env: {e}")
                return []
        return []

    def get_current_key(self):
        """
        Retorna a chave de API atualmente ativa.
        """
        return self.keys[self.current_key_index]

    def switch_key(self):
        """
        Troca para a próxima chave de API na lista.
        Se chegar ao final, volta para a primeira chave.
        """
        if len(self.keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.keys)
            print(f"Chave de API trocada. Usando a chave no índice: {self.current_key_index}")
        else:
            print("Apenas uma chave disponível. A troca não é necessária.")

    def get_all_keys(self):
        """
        Retorna a lista completa de chaves.
        """
        return self.keys

# --- Exemplo de Uso ---
# Este bloco de código demonstra como usar a classe KeyManager no seu projeto.

if __name__ == "__main__":
    # 1. Crie uma instância do gerenciador de chaves.
    key_manager = KeyManager()

    # 2. Obtenha a chave atual.
    current_key = key_manager.get_current_key()
    print(f"Chave inicial: {current_key}")

    # 3. Simule o uso da API e uma falha que exige a troca.
    # No seu código real, você faria uma chamada à API do Gemini aqui
    # e, se a chamada falhar (por exemplo, devido a um erro 429 - Too Many Requests),
    # você chamaria o método switch_key().
    print("Simulando falha de chave...")
    key_manager.switch_key()

    # 4. Obtenha a nova chave para continuar as operações.
    new_key = key_manager.get_current_key()
    print(f"Nova chave após a troca: {new_key}")

    # Você pode continuar a trocar as chaves conforme necessário.
    print("Simulando nova falha...")
    key_manager.switch_key()
    next_key = key_manager.get_current_key()
    print(f"Próxima chave: {next_key}")