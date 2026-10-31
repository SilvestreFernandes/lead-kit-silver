"""Liga o motor de busca (`docker compose up -d`) a pedido do painel, em segundo plano.

Seguranca:
- o comando e fixo e sem shell: lista de argumentos montada aqui, nunca com texto vindo do navegador;
- usa o caminho absoluto do docker-compose.yml do kit e roda a partir da pasta do kit;
- no Windows nao abre janela de console;
- a saida do comando vai para dados/log-motor.txt (fora do git e nao servido por nenhuma rota).
  O painel so recebe uma mensagem simples.
"""
import subprocess
import sys
import threading
import time

LIMITE_DO_COMANDO_S = 600  # a primeira vez pode baixar a imagem do motor
NOME_DO_LOG = "log-motor.txt"

MENSAGENS = {
    "ligando": "Ligando o motor. Pode levar alguns minutos, principalmente na primeira vez, "
               "porque o Docker pode precisar baixar o motor.",
    "ok": "O comando terminou. Espere o motor responder e clique em Verificar de novo se a tela não mudar.",
    "docker_ausente": "Não encontrei o Docker neste computador.",
    "demorou": "O Docker demorou mais de 10 minutos e o kit parou de esperar. Abra o Docker Desktop, "
               "veja se ele está verde e tente de novo.",
    "erro": "O Docker não conseguiu ligar o motor. Os detalhes ficaram salvos no arquivo dados/log-motor.txt, "
            "dentro da pasta do kit. Mostre esse arquivo para a sua IA pedir ajuda.",
}


class LigadorDoMotor:
    def __init__(self, pasta_kit, pasta_dados, executar=subprocess.run, limite_s=LIMITE_DO_COMANDO_S,
                 relogio=time.time):
        self.pasta_kit = pasta_kit
        self.arquivo_compose = (pasta_kit / "docker-compose.yml").resolve()
        self.arquivo_log = pasta_dados / NOME_DO_LOG
        self._executar, self.limite_s, self._relogio = executar, limite_s, relogio
        self._trava = threading.Lock()
        self._situacao = None   # None, ou {"estado": "ligando" | "ok" | "erro", "mensagem": str}
        self.thread = None

    @property
    def comando(self):
        return ["docker", "compose", "-f", str(self.arquivo_compose), "up", "-d"]

    def situacao(self):
        with self._trava:
            return dict(self._situacao) if self._situacao else None

    def esta_ligando(self):
        s = self.situacao()
        return bool(s and s["estado"] == "ligando")

    def iniciar(self):
        """True se comecou agora, False se ja havia um comando rodando."""
        with self._trava:
            if self._situacao and self._situacao["estado"] == "ligando":
                return False
            self._situacao = {"estado": "ligando", "mensagem": MENSAGENS["ligando"]}
        self.thread = threading.Thread(target=self._trabalho, daemon=True)
        self.thread.start()
        return True

    def _definir(self, estado, chave):
        with self._trava:
            self._situacao = {"estado": estado, "mensagem": MENSAGENS[chave]}

    def _trabalho(self):
        opcoes = {"cwd": str(self.pasta_kit), "timeout": self.limite_s, "stdin": subprocess.DEVNULL}
        if sys.platform == "win32":
            opcoes["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self.arquivo_log.parent.mkdir(parents=True, exist_ok=True)
            with open(self.arquivo_log, "wb") as log:
                log.write(f"$ {' '.join(self.comando)}\n".encode("utf-8"))
                log.flush()
                try:
                    r = self._executar(self.comando, stdout=log, stderr=subprocess.STDOUT, **opcoes)
                except FileNotFoundError:
                    log.write(b"docker nao encontrado\n")
                    self._definir("erro", "docker_ausente")
                    return
                except subprocess.TimeoutExpired:
                    log.write(f"\nparou de esperar depois de {self.limite_s} s\n".encode("utf-8"))
                    self._definir("erro", "demorou")
                    return
            self._definir("ok" if r.returncode == 0 else "erro", "ok" if r.returncode == 0 else "erro")
        except Exception as e:  # qualquer falha aqui vira mensagem simples, nunca derruba o servidor
            print(f"Falha ao ligar o motor: {type(e).__name__}: {e}", file=sys.stderr)
            self._definir("erro", "erro")
