"""Servidor local do Lead Kit Silver. So biblioteca padrao.

Escuta so em 127.0.0.1. Seguranca (vale para todas as rotas):
- so aceita `Host` igual a 127.0.0.1:<porta> ou localhost:<porta>;
- rotas que alteram dados exigem o cabecalho X-Token (token novo a cada inicio, entregue so no index.html);
- nenhum cabecalho CORS, e OPTIONS e recusado;
- escrita so com Content-Type application/json, corpo ate 1 MB, e `Origin` de fora e recusado;
- so serve arquivos de dentro da pasta do painel.

Uso:  python kit/servidor.py
"""
import argparse
import hmac
import json
import os
import re
import secrets
import shutil
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from kit import banco, buscar, consulta, diagnostico as diagnostico_mod, motor as motor_mod, validar_perfil  # noqa: E402
from kit.geocodificar import Geocodificador  # noqa: E402

VERSAO = "0.2.0-dev"
PORTA_PADRAO = 8787
ENDERECO = "127.0.0.1"
LIMITE_CORPO = 1_000_000
LIMITE_DRENAGEM = 8_000_000  # acima disso nem tenta ler: so responde e fecha
UFS = ("AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR",
       "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO")
# Tipo fixo por extensao: modulos JavaScript exigem text/javascript, e o Windows pode mapear .js
# para outro tipo no registro do sistema.
TIPOS_ESTATICOS = {
    ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml",
    ".png": "image/png", ".ico": "image/x-icon", ".txt": "text/plain",
}
EXTENSOES_ESTATICAS = set(TIPOS_ESTATICOS)
CABECALHOS_SEGUROS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}
CSP_HTML = ("default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


class Erro(Exception):
    """Erro de requisicao: vira JSON {'erro': mensagem} com o status dado."""

    def __init__(self, status, mensagem, **extra):
        super().__init__(mensagem)
        self.status, self.mensagem, self.extra = status, mensagem, extra


class Resposta:
    def __init__(self, status, corpo, tipo, extras=None):
        self.status, self.corpo, self.tipo, self.extras = status, corpo, tipo, extras or {}


def json_resposta(status, dados):
    return Resposta(status, json.dumps(dados, ensure_ascii=False).encode("utf-8"),
                    "application/json; charset=utf-8")


# ---------------------------------------------------------------- rotas

def rota_estado(srv, params, consulta_, corpo):
    perfil, erros, avisos = validar_perfil.carregar(srv.caminho_perfil)
    no_ar = srv.motor.no_ar()
    return 200, {
        "versao_kit": VERSAO,
        "motor_no_ar": no_ar,
        # Quando o motor nao responde: o motivo (Docker ausente, Docker parado ou so o motor parado) e o que fazer.
        "motor_diagnostico": None if no_ar else srv.diagnostico(srv.motor),
        "perfil": {"existe": srv.caminho_perfil.exists(), "valido": not erros,
                   "erros": erros, "avisos": avisos},
        "busca_em_andamento": srv.busca_ativa,
    }


def rota_opcoes(srv, params, consulta_, corpo):
    """Tudo que o painel precisa para montar formularios, vindo das regras do kit (nada duplicado no JS)."""
    esquema, regras = validar_perfil.ESQUEMA, validar_perfil.REGRAS
    return 200, {
        "regras": [{"id": rid, "texto": cfg["texto"], "peso_padrao": cfg["peso"]}
                   for rid, cfg in regras["regras"].items()],
        "exclusoes": [{"id": eid, "texto": cfg["texto"]} for eid, cfg in regras["exclusoes"].items()],
        "marcadores": esquema["marcadores"],
        "canais": esquema["canais"], "tons": esquema["tons"], "portes": esquema["portes"],
        "peso_minimo": esquema["peso_minimo"], "peso_maximo": esquema["peso_maximo"],
        "tamanhos": [{"id": t, "pontos": cfg["pontos"], "tempo_estimado": cfg["tempo_estimado"]}
                     for t, cfg in motor_mod.TAMANHOS.items()],
        "tamanhos_em_breve": list(motor_mod.TAMANHOS_EM_BREVE),
        "ufs": list(UFS),
        "cortes_padrao": regras["cortes"],
        "status_lead": list(banco.STATUS_LEAD),
    }


def _perfil_valido(srv):
    perfil, erros, avisos = validar_perfil.carregar(srv.caminho_perfil)
    if erros:
        raise Erro(409, "O perfil não existe ou não está válido. Rode a entrevista na sua IA "
                        "ou corrija o perfil.", erros=erros)
    return perfil


def rota_perfil_ler(srv, params, consulta_, corpo):
    if not srv.caminho_perfil.exists():
        raise Erro(404, "Ainda não existe um perfil. Rode a entrevista na sua IA.")
    perfil, erros, avisos = validar_perfil.carregar(srv.caminho_perfil)
    return 200, {"perfil": perfil, "erros": erros, "avisos": avisos}


def rota_perfil_gravar(srv, params, consulta_, corpo):
    perfil, erros, avisos = validar_perfil.validar(corpo)
    if erros:
        raise Erro(422, "O perfil tem problemas e não foi salvo.", erros=erros)
    srv.caminho_perfil.parent.mkdir(parents=True, exist_ok=True)
    if srv.caminho_perfil.exists():
        shutil.copy2(srv.caminho_perfil, srv.caminho_perfil.with_name("perfil.anterior.json"))
    temporario = srv.caminho_perfil.with_name("perfil.json.tmp")
    temporario.write_text(json.dumps(perfil, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporario, srv.caminho_perfil)
    return 200, {"perfil": perfil, "avisos": avisos}


def _paginacao(consulta_):
    try:
        limite = int((consulta_.get("limite") or ["200"])[0])
        deslocamento = int((consulta_.get("offset") or ["0"])[0])
    except ValueError:
        raise Erro(400, "Os filtros 'limite' e 'offset' precisam ser números.")
    if not 1 <= limite <= 1000 or deslocamento < 0:
        raise Erro(400, "O 'limite' vai de 1 a 1000 e o 'offset' não pode ser negativo.")
    return limite, deslocamento


def _leads_filtrados(srv, conn, consulta_, com_contagem=False):
    perfil = _perfil_valido(srv)
    try:
        filtros = consulta.ler_filtros(consulta_)
    except consulta.FiltroInvalido as e:
        raise Erro(400, str(e))
    ids = banco.ids_da_busca(conn, filtros["busca"]) if filtros["busca"] is not None else None
    avaliados = consulta.avaliar(conn, perfil)
    achados = consulta.filtrar(avaliados, filtros, ids)
    if com_contagem:
        # Contagem por letra com todos os filtros menos o da letra, para os botoes A, B e C.
        sem_letra = consulta.filtrar(avaliados, {**filtros, "letras": None}, ids)
        return perfil, achados, consulta.contar_por_letra(sem_letra)
    return perfil, achados


def rota_leads_listar(srv, params, consulta_, corpo):
    limite, deslocamento = _paginacao(consulta_)
    with srv.banco() as conn:
        _, achados, contagem = _leads_filtrados(srv, conn, consulta_, com_contagem=True)
    pagina = achados[deslocamento:deslocamento + limite]
    return 200, {"total": len(achados), "limite": limite, "offset": deslocamento,
                 "contagem_por_letra": contagem, "leads": [consulta.resumo(r) for r in pagina]}


def _id_inteiro(texto):
    return int(texto)  # a rota so casa com digitos


def rota_lead_ler(srv, params, consulta_, corpo):
    perfil = _perfil_valido(srv)
    lead_id = _id_inteiro(params["id"])
    with srv.banco() as conn:
        for r in consulta.avaliar(conn, perfil):
            if r["lead"]["id"] == lead_id:
                return 200, consulta.detalhe(r, perfil)
    raise Erro(404, "Não achei esse lead.")


def rota_lead_alterar(srv, params, consulta_, corpo):
    permitidos = {"status", "anotacao", "mensagem_editada"}
    extras = set(corpo) - permitidos
    if extras or not corpo:
        raise Erro(400, "Envie só estes campos: status, anotacao, mensagem_editada.")
    limites = {"anotacao": 2000, "mensagem_editada": 5000}
    for campo in ("anotacao", "mensagem_editada"):
        if campo in corpo:
            if not isinstance(corpo[campo], str) or len(corpo[campo]) > limites[campo]:
                raise Erro(400, f"O campo {campo} precisa ser texto de até {limites[campo]} letras.")
    if "status" in corpo and corpo["status"] not in banco.STATUS_LEAD:
        raise Erro(400, "O status precisa ser um destes: " + ", ".join(banco.STATUS_LEAD) + ".")
    lead_id = _id_inteiro(params["id"])
    with srv.banco() as conn:
        if not banco.atualizar_lead(conn, lead_id, corpo.get("status"), corpo.get("anotacao"),
                                    corpo.get("mensagem_editada")):
            raise Erro(404, "Não achei esse lead.")
        l = banco.obter_lead(conn, lead_id)
    return 200, {"id": l["id"], "status": l["status"], "anotacao": l["anotacao"],
                 "mensagem_editada": l["mensagem_editada"]}


def rota_reavaliar(srv, params, consulta_, corpo):
    perfil = _perfil_valido(srv)
    with srv.banco() as conn:
        avaliados = consulta.avaliar(conn, perfil)
        banco.gravar_notas(conn, {r["lead"]["chave"]: r for r in avaliados})
    por_letra = {"A": 0, "B": 0, "C": 0}
    for r in avaliados:
        por_letra[r["letra"]] += 1
    return 200, {"leads": len(avaliados), "por_letra": por_letra}


def _texto(corpo, campo, maximo=80):
    valor = corpo.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise Erro(400, f"Falta preencher: {campo}.")
    valor = valor.strip()
    if len(valor) > maximo or any(ord(c) < 32 for c in valor):
        raise Erro(400, f"O campo {campo} está grande demais ou tem caractere inválido.")
    return valor


def rota_busca_criar(srv, params, consulta_, corpo):
    categoria, cidade = _texto(corpo, "categoria"), _texto(corpo, "cidade")
    uf = _texto(corpo, "uf", 2).upper()
    if uf not in UFS:
        raise Erro(400, "A sigla do estado (uf) não existe. Exemplo: DF.")
    tamanho = corpo.get("tamanho", "rapida")
    if tamanho not in motor_mod.TAMANHOS:
        raise Erro(400, "O tamanho precisa ser: " + ", ".join(sorted(motor_mod.TAMANHOS)) + ".")
    email = corpo.get("email", False)
    if not isinstance(email, bool):
        raise Erro(400, "O campo email precisa ser true ou false.")
    perfil = _perfil_valido(srv)
    if not srv.motor.no_ar():
        motivo = srv.diagnostico(srv.motor)
        if motivo:  # None significa que o motor voltou agora mesmo
            raise Erro(503, diagnostico_mod.mensagem_completa(motivo), motor_diagnostico=motivo)
    with srv.trava_busca:
        if srv.busca_ativa is not None:
            raise Erro(409, "Já existe uma busca em andamento. Espere ela terminar.",
                       busca_em_andamento=srv.busca_ativa)
        with srv.banco() as conn:
            busca_id = buscar.iniciar_busca(conn, categoria, cidade, uf, tamanho, email)
        srv.busca_ativa = busca_id
    threading.Thread(target=srv.trabalho_da_busca, args=(busca_id, perfil), daemon=True).start()
    return 202, {"id": busca_id, "status": "criada"}


def _busca_publica(srv, busca):
    d = {k: busca[k] for k in ("id", "criada_em", "terminou_em", "categoria", "cidade", "uf", "tamanho",
                               "email_ligado", "status", "erro", "erro_tipo", "total_leads", "novos",
                               "ja_existiam", "fora_da_lista")}
    andamento = srv.progresso.get(busca["id"])
    d["etapa"] = andamento["etapa"] if andamento else None
    d["segundos"] = andamento["segundos"] if andamento else None
    d["ponto"] = andamento["ponto"] if andamento else None
    tamanho = motor_mod.TAMANHOS.get(busca["tamanho"], {})
    d["pontos"] = tamanho.get("pontos")
    d["tempo_estimado"] = tamanho.get("tempo_estimado")
    return d


def rota_buscas_listar(srv, params, consulta_, corpo):
    with srv.banco() as conn:
        return 200, {"buscas": [_busca_publica(srv, b) for b in banco.listar_buscas(conn)]}


def rota_busca_ler(srv, params, consulta_, corpo):
    with srv.banco() as conn:
        busca = banco.obter_busca(conn, _id_inteiro(params["id"]))
    if not busca:
        raise Erro(404, "Não achei essa busca.")
    return 200, _busca_publica(srv, busca)


TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def rota_exportar(srv, params, consulta_, corpo):
    formato = (consulta_.get("formato") or ["csv"])[0]
    if formato not in ("csv", "xlsx"):
        raise Erro(400, "O formato precisa ser csv ou xlsx.")
    with srv.banco() as conn:
        perfil, achados = _leads_filtrados(srv, conn, consulta_)
    if formato == "xlsx":
        return Resposta(200, consulta.exportar_xlsx(achados, perfil), TIPO_XLSX,
                        {"Content-Disposition": 'attachment; filename="leads.xlsx"'})
    texto = consulta.exportar_csv(achados)
    return Resposta(200, texto.encode("utf-8"), "text/csv; charset=utf-8",
                    {"Content-Disposition": 'attachment; filename="leads.csv"'})


# Rotas de LEITURA que mesmo assim exigem o token, porque entregam os dados dos leads em arquivo.
ROTAS_COM_TOKEN_NA_LEITURA = {rota_exportar}

# metodo, caminho, funcao, escreve?
ROTAS = [
    ("GET", r"/api/estado", rota_estado, False),
    ("GET", r"/api/opcoes", rota_opcoes, False),
    ("GET", r"/api/perfil", rota_perfil_ler, False),
    ("PUT", r"/api/perfil", rota_perfil_gravar, True),
    ("GET", r"/api/leads", rota_leads_listar, False),
    ("POST", r"/api/leads/reavaliar", rota_reavaliar, True),
    ("GET", r"/api/leads/(?P<id>\d+)", rota_lead_ler, False),
    ("PATCH", r"/api/leads/(?P<id>\d+)", rota_lead_alterar, True),
    ("POST", r"/api/buscas", rota_busca_criar, True),
    ("GET", r"/api/buscas", rota_buscas_listar, False),
    ("GET", r"/api/buscas/(?P<id>\d+)", rota_busca_ler, False),
    ("GET", r"/api/exportar", rota_exportar, False),
]
ROTAS = [(m, re.compile(c + r"\Z"), f, e) for m, c, f, e in ROTAS]


# ---------------------------------------------------------------- servidor

class Manipulador(BaseHTTPRequestHandler):
    server_version = "LeadKit"
    sys_version = ""

    def log_message(self, formato, *args):
        pass

    # Todo metodo cai no mesmo tratador. OPTIONS e HEAD acabam em 405: nao existe pre-voo (CORS).
    def do_GET(self): self._tratar("GET")
    def do_POST(self): self._tratar("POST")
    def do_PUT(self): self._tratar("PUT")
    def do_PATCH(self): self._tratar("PATCH")
    def do_DELETE(self): self._tratar("DELETE")
    def do_OPTIONS(self): self._tratar("OPTIONS")
    def do_HEAD(self): self._tratar("HEAD")

    def _tratar(self, metodo):
        self._corpo_lido = False
        try:
            resposta = self._resolver(metodo)
        except Erro as e:
            resposta = json_resposta(e.status, {"erro": e.mensagem, **e.extra})
        except Exception as e:  # nunca vaza detalhe interno para quem chamou
            print(f"Erro interno em {metodo} {self.path}: {e!r}", file=sys.stderr)
            resposta = json_resposta(500, {"erro": "Algo deu errado dentro do kit. Veja a janela do servidor."})
        self._descartar_corpo()
        self._enviar(resposta)

    def _descartar_corpo(self):
        """Le o corpo que sobrou antes de responder, senao fechar a conexao pode perder a resposta."""
        if self._corpo_lido:
            return
        self._corpo_lido = True
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return
        if 0 < tamanho <= LIMITE_CORPO:
            self.rfile.read(tamanho)
        elif LIMITE_CORPO < tamanho <= LIMITE_DRENAGEM:
            # Corpo grande demais: le e joga fora (sem guardar), com tempo curto, para o cliente
            # conseguir ler o 413. Fechar a conexao com dados pendentes pode derrubar a resposta.
            self.connection.settimeout(0.5)
            restante = tamanho
            try:
                while restante > 0:
                    pedaco = self.rfile.read(min(65536, restante))
                    if not pedaco:
                        break
                    restante -= len(pedaco)
            except OSError:
                pass

    def _resolver(self, metodo):
        srv = self.server
        # 1. Host: defende contra DNS rebinding e acesso por outro nome ou pelo IP da rede.
        if (self.headers.get("Host") or "").lower() not in srv.hosts_permitidos:
            raise Erro(403, f"Endereço não permitido. Abra o painel por http://127.0.0.1:{srv.porta}")
        # 2. Origin de outro site (pagina qualquer tentando falar com o servidor local).
        origem = self.headers.get("Origin")
        if origem is not None and origem not in srv.origens_permitidas:
            raise Erro(403, "Pedido de outro site recusado.")

        partes = urlsplit(self.path)
        caminho = unquote(partes.path)
        consulta_ = parse_qs(partes.query)

        achou_caminho, escolhida = False, None
        for m, regex, funcao, escreve in ROTAS:
            casou = regex.match(caminho)
            if casou:
                achou_caminho = True
                if m == metodo:
                    escolhida = (funcao, casou.groupdict(), escreve)
                    break
        if escolhida is None and achou_caminho:
            raise Erro(405, "Esse método não é aceito aqui.")
        if escolhida is None and caminho.startswith("/api/"):
            raise Erro(404, "Não achei essa rota.")
        if escolhida is None:
            if metodo != "GET":
                raise Erro(405, "Esse método não é aceito aqui.")
            return srv.servir_arquivo(caminho)

        funcao, params, escreve = escolhida
        corpo = {}
        if escreve:
            corpo = self._ler_corpo_de_escrita()
        elif funcao in ROTAS_COM_TOKEN_NA_LEITURA:
            self._exigir_token()
        status, dados = None, None
        resultado = funcao(srv, params, consulta_, corpo)
        if isinstance(resultado, Resposta):
            return resultado
        status, dados = resultado
        return json_resposta(status, dados)

    def _exigir_token(self):
        enviado = self.headers.get("X-Token") or ""
        if not hmac.compare_digest(enviado.encode("utf-8"), self.server.token.encode("utf-8")):
            raise Erro(401, "Falta a permissão para alterar dados. Recarregue o painel.")

    def _ler_corpo_de_escrita(self):
        self._exigir_token()
        tipo = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if tipo != "application/json":
            raise Erro(415, "Envie o corpo como application/json.")
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise Erro(400, "Content-Length inválido.")
        if tamanho > LIMITE_CORPO:
            raise Erro(413, "O pedido é grande demais.")
        bruto = self.rfile.read(tamanho) if tamanho else b""
        self._corpo_lido = True
        if not bruto:
            return {}
        try:
            corpo = json.loads(bruto.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise Erro(400, "O corpo do pedido não é um JSON válido.")
        if not isinstance(corpo, dict):
            raise Erro(400, "O corpo do pedido precisa ser um objeto JSON.")
        return corpo

    def _enviar(self, r):
        self.send_response(r.status)
        self.send_header("Content-Type", r.tipo)
        self.send_header("Content-Length", str(len(r.corpo)))
        for nome, valor in {**CABECALHOS_SEGUROS, **r.extras}.items():
            self.send_header(nome, valor)
        if r.tipo.startswith("text/html"):
            self.send_header("Content-Security-Policy", CSP_HTML)
        self.end_headers()
        self.wfile.write(r.corpo)


class Servidor(ThreadingHTTPServer):
    allow_reuse_address = False  # no Windows isso deixaria outro programa pegar a mesma porta
    daemon_threads = True

    def __init__(self, porta=PORTA_PADRAO, pasta_dados=None, pasta_painel=None, motor=None, geo=None,
                 token=None, endereco=ENDERECO, dormir=time.sleep, diagnostico=None):
        if endereco != ENDERECO:
            raise ValueError("O servidor só pode escutar em 127.0.0.1.")
        super().__init__((endereco, porta), Manipulador)
        self.porta = self.server_address[1]
        self.hosts_permitidos = {f"127.0.0.1:{self.porta}", f"localhost:{self.porta}"}
        self.origens_permitidas = {f"http://{h}" for h in self.hosts_permitidos}
        self.token = token or secrets.token_urlsafe(32)
        pasta_dados = Path(pasta_dados) if pasta_dados else RAIZ / "dados"
        self.caminho_perfil = pasta_dados / "perfil.json"
        self.caminho_banco = pasta_dados / "leads.db"
        self.pasta_painel = Path(pasta_painel) if pasta_painel else RAIZ / "kit" / "painel"
        self.motor = motor or motor_mod.Motor()
        self.geo = geo or Geocodificador(arquivo_cache=pasta_dados / "cache_geocodificacao.json")
        self.dormir = dormir
        self.diagnostico = diagnostico or diagnostico_mod.DiagnosticoComCache()
        self.trava_busca = threading.Lock()
        self.busca_ativa = None
        self.progresso = {}
        pasta_dados.mkdir(parents=True, exist_ok=True)
        with self.banco() as conn:
            banco.interromper_buscas_abertas(conn)

    def banco(self):
        """Uma conexao nova por uso, na thread de quem pede. Use com `with`: fecha ao sair."""
        return _ConexaoDoUso(self.caminho_banco)

    def trabalho_da_busca(self, busca_id, perfil):
        inicio = time.monotonic()

        def progresso(etapa, segundos=None, ponto=None, pontos=None):
            self.progresso[busca_id] = {"etapa": etapa, "segundos": int(time.monotonic() - inicio), "ponto": ponto}

        conn = banco.abrir(self.caminho_banco)
        try:
            buscar.executar_busca(conn, busca_id, perfil, self.motor, self.geo, progresso, self.dormir)
        except Exception as e:
            # executar_busca ja marcou a busca como 'erro' no banco.
            print(f"Busca {busca_id} terminou com erro: {e}", file=sys.stderr)
        finally:
            conn.close()
            self.progresso.pop(busca_id, None)
            with self.trava_busca:
                self.busca_ativa = None

    def servir_arquivo(self, caminho):
        if caminho in ("", "/"):
            caminho = "/index.html"
        relativo = caminho.lstrip("/")
        if "\\" in relativo or "\x00" in relativo or Path(relativo).suffix.lower() not in EXTENSOES_ESTATICAS:
            raise Erro(404, "Não achei esse arquivo.")
        base = self.pasta_painel.resolve()
        alvo = (base / relativo).resolve()
        if not alvo.is_relative_to(base) or not alvo.is_file():
            raise Erro(404, "Não achei esse arquivo.")
        dados = alvo.read_bytes()
        tipo = TIPOS_ESTATICOS[alvo.suffix.lower()]
        if alvo.suffix.lower() == ".html":
            dados = dados.replace(b"{{TOKEN}}", self.token.encode("ascii"))
        if tipo.startswith("text/") or tipo == "image/svg+xml":
            tipo += "; charset=utf-8"
        return Resposta(200, dados, tipo)


class _ConexaoDoUso:
    def __init__(self, caminho):
        self.caminho = caminho

    def __enter__(self):
        self.conn = banco.abrir(self.caminho)
        return self.conn

    def __exit__(self, *erro):
        self.conn.close()


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Servidor local do Lead Kit Silver.")
    p.add_argument("--porta", type=int, default=PORTA_PADRAO)
    p.add_argument("--motor", default=motor_mod.URL_PADRAO)
    args = p.parse_args(argv)
    try:
        servidor = Servidor(porta=args.porta, motor=motor_mod.Motor(args.motor))
    except OSError:
        print(f"Não consegui usar a porta {args.porta}. Ela já está em uso. "
              f"Feche o outro programa ou use --porta com outro número.")
        return 1
    except motor_mod.ErroMotor as e:
        print(f"Erro: {e}")
        return 1
    print(f"Servidor no ar: http://127.0.0.1:{servidor.porta}  (Ctrl+C para parar)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor parado.")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
