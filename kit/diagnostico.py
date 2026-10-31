"""Descobre POR QUE o motor de busca nao responde, para a tela dizer o que fazer.

O motor roda em Docker. Quando ele nao responde, o motivo pode ser o Docker nao estar instalado,
o Docker estar fechado, ou so o motor estar desligado. Cada um pede uma acao diferente.

So executa `docker info`: comando fixo, sem nada digitado pela pessoa. Nada sai do computador.
"""
import subprocess
import time

COMANDO_LIGAR_MOTOR = "docker compose up -d"
VALIDADE_DO_RESULTADO_S = 15  # nao rodar `docker info` a cada verificacao do painel

# Como abrir uma janela de comandos na pasta do kit, para quem nunca abriu um terminal.
# O painel tem a mesma lista em kit/painel/instrucoes.js (um teste confere que as duas sao iguais).
PASSOS_TERMINAL = [
    "Abra a pasta do kit no Explorador de Arquivos (a pasta onde está o arquivo docker-compose.yml).",
    "Clique na barra de endereço, no alto da janela, apague o que estiver escrito, digite powershell e aperte Enter. Vai abrir uma janela escura.",
    "Clique no botão Copiar do comando, clique dentro da janela escura, aperte Ctrl e V juntos para colar, e aperte Enter.",
]

DIAGNOSTICOS = {
    "no_ar": None,
    "docker_ausente": {
        "titulo": "O Docker não foi encontrado",
        "texto": "O kit usa o Docker Desktop para rodar o motor de busca, e ele não está instalado neste computador.",
        "passos": [
            "Peça para a sua IA conferir a instalação do Docker Desktop. Ela explica o que falta e pede a sua confirmação antes de instalar qualquer coisa.",
            "Se preferir instalar sozinho, procure Docker Desktop no site docker.com, baixe e instale. Depois abra o Docker Desktop pelo menu Iniciar (ícone da baleia) e espere ele ficar verde.",
        ],
        "comando": None,
    },
    "docker_parado": {
        "titulo": "O Docker está desligado",
        "texto": "O motor de busca roda dentro do Docker, e o Docker Desktop está fechado.",
        "passos": [
            "Abra o Docker Desktop pelo menu Iniciar (procure o ícone da baleia).",
            "Espere ele ficar verde. Pode levar um ou dois minutos.",
            *PASSOS_TERMINAL,
            "Espere uns 20 segundos e clique em Verificar de novo.",
        ],
        "comando": COMANDO_LIGAR_MOTOR,
    },
    "motor_parado": {
        "titulo": "O motor de busca está desligado",
        "texto": "O Docker está ligado, mas o motor de busca não.",
        "passos": [
            *PASSOS_TERMINAL,
            "Espere uns 20 segundos e clique em Verificar de novo.",
        ],
        "comando": COMANDO_LIGAR_MOTOR,
    },
}


def mensagem_completa(diag):
    """O mesmo conteudo em uma frase so, para quem le apenas o texto (terminal, mensagens de erro)."""
    passos = " ".join(f"{i}) {p}" for i, p in enumerate(diag["passos"], start=1))
    comando = f" Comando: {diag['comando']}" if diag.get("comando") else ""
    return f"{diag['titulo']}. {diag['texto']} Como fazer: {passos}{comando}"


def diagnosticar(motor, executar=subprocess.run):
    """Devolve {'estado', 'titulo', 'texto', 'comando'} ou None se o motor esta no ar."""
    if motor.no_ar():
        return None
    try:
        r = executar(["docker", "info"], capture_output=True, text=True, timeout=6)
    except FileNotFoundError:
        estado = "docker_ausente"
    except (subprocess.TimeoutExpired, OSError):
        estado = "docker_parado"
    else:
        estado = "motor_parado" if r.returncode == 0 else "docker_parado"
    return {"estado": estado, **DIAGNOSTICOS[estado]}


class DiagnosticoComCache:
    """Guarda o ultimo resultado por alguns segundos."""

    def __init__(self, funcao=diagnosticar, validade=VALIDADE_DO_RESULTADO_S, relogio=time.monotonic):
        self._funcao, self._validade, self._relogio = funcao, validade, relogio
        self._guardado = None

    def __call__(self, motor):
        agora = self._relogio()
        if self._guardado and agora - self._guardado[0] < self._validade:
            resultado = self._guardado[1]
            # Se o motor voltou, o resultado guardado nao vale mais.
            if resultado is None or not motor.no_ar():
                return resultado
        resultado = self._funcao(motor)
        self._guardado = (agora, resultado)
        return resultado
