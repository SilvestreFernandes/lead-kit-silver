"""Cliente do motor (gosom/google-maps-scraper em Docker). So biblioteca padrao.

Fala com a API do motor direto pelo Python: o corpo do pedido e montado com json.dumps, nunca
digitado no terminal com aspas escapadas. So aceita o motor em 127.0.0.1 ou localhost.

Parametros confirmados com execucao real na fase 0 (docs/planejamento/fase0-verificacao-motor.md):
lang com 2 letras ("pt"), lat e lon como texto, max_time em segundos, status "working" e depois "ok".
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

URL_PADRAO = "http://127.0.0.1:8080"
ZOOM = 15
RAIO_METROS = 10000

# PROVISORIO. Apenas depth 1 (rapida) foi medido como padrao: 16 linhas em cerca de 30 s.
# depth 3 e 5 deram os mesmos 20 negocios em 50 s na medicao da fase 1, entao a profundidade
# sozinha nao diferencia media de ampla. Os valores de media e ampla ficam aqui, num lugar so,
# ate o Silvestre decidir a alavanca (ver fase0-verificacao-motor.md). Os max_time sao folga.
TAMANHOS = {
    "rapida": {"depth": 1, "max_time": 180},
    "media": {"depth": 3, "max_time": 300},
    "ampla": {"depth": 5, "max_time": 600},
}

STATUS_PRONTO = "ok"
STATUS_TRABALHANDO = "working"


class ErroMotor(Exception):
    """Algo deu errado ao falar com o motor. A mensagem ja vem em portugues simples."""


def _conferir_endereco(base):
    host = urllib.parse.urlparse(base).hostname
    if host not in ("127.0.0.1", "localhost"):
        raise ErroMotor("O motor só pode ficar no próprio computador (127.0.0.1).")


class Motor:
    def __init__(self, base=URL_PADRAO, abrir=None, dormir=time.sleep, relogio=time.monotonic):
        _conferir_endereco(base)
        self.base = base.rstrip("/")
        self._abrir = abrir or self._abrir_de_verdade
        self._dormir, self._relogio = dormir, relogio

    @staticmethod
    def _abrir_de_verdade(req):
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()

    def _chamar(self, caminho, corpo=None):
        dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
        req = urllib.request.Request(
            self.base + caminho, data=dados, method="POST" if dados is not None else "GET",
            headers={"Content-Type": "application/json"})
        try:
            return self._abrir(req)
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode("utf-8", "replace")[:300]
            raise ErroMotor(f"O motor recusou o pedido ({e.code}): {detalhe}")
        except (urllib.error.URLError, OSError):
            raise ErroMotor("O motor não está respondendo. Suba ele com: docker compose up -d "
                            "(e espere uns segundos).")

    def no_ar(self):
        try:
            status, _ = self._chamar("/api/v1/jobs")
            return status == 200
        except ErroMotor:
            return False

    def montar_pedido(self, palavra, lat, lon, tamanho="rapida", email=False, nome="lead-kit"):
        if tamanho not in TAMANHOS:
            raise ErroMotor("Tamanho de busca desconhecido: " + tamanho)
        t = TAMANHOS[tamanho]
        return {
            "name": nome, "keywords": [palavra], "lang": "pt", "zoom": ZOOM,
            "lat": str(lat), "lon": str(lon), "fast_mode": False, "radius": RAIO_METROS,
            "depth": t["depth"], "email": bool(email), "max_time": t["max_time"],
        }

    def criar_job(self, pedido):
        status, corpo = self._chamar("/api/v1/jobs", pedido)
        try:
            return json.loads(corpo)["id"]
        except (KeyError, ValueError, TypeError):
            raise ErroMotor(f"O motor respondeu ({status}) mas não devolveu o número da busca.")

    def status(self, job_id):
        _, corpo = self._chamar(f"/api/v1/jobs/{job_id}")
        dados = json.loads(corpo)
        return dados.get("Status") or dados.get("status") or ""

    def esperar(self, job_id, intervalo=5, limite=None, ao_esperar=None):
        """Espera o job terminar. Devolve o status final ('ok'). Outro status vira erro claro."""
        limite = limite if limite is not None else 900
        inicio = self._relogio()
        while True:
            self._dormir(intervalo)
            atual = self.status(job_id)
            if atual == STATUS_PRONTO:
                return atual
            if atual != STATUS_TRABALHANDO:
                raise ErroMotor(f"A busca terminou com o status inesperado {atual!r}. "
                                "Esse status ainda não foi visto nos testes do kit.")
            decorrido = self._relogio() - inicio
            if decorrido > limite:
                raise ErroMotor(f"A busca passou de {limite} segundos e foi abandonada. "
                                "Tente de novo com uma busca menor.")
            if ao_esperar:
                ao_esperar(decorrido)

    def baixar_csv(self, job_id):
        _, corpo = self._chamar(f"/api/v1/jobs/{job_id}/download")
        return corpo.decode("utf-8-sig")
