"""Testes do servidor local. Servidor de verdade em 127.0.0.1 (porta livre), motor e mapas simulados."""
import contextlib
import csv
import http.client
import io
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import types
import time
import unittest
from pathlib import Path

from kit import banco, limpeza, servidor
from kit import diagnostico as diagnostico_mod
from kit.ligar_motor import LigadorDoMotor
from kit import motor as motor_mod
from kit.geocodificar import CidadeNaoEncontrada
from testes.fixtures import (GeoDeMentira, MotorDeMentira, csv_texto, leads_em_massa, linha, perfil_ficticio)

TOKEN = "token-de-teste-123"


class Resp:
    def __init__(self, status, cabecalhos, corpo):
        self.status, self.cabecalhos, self.corpo = status, cabecalhos, corpo

    @property
    def json(self):
        return json.loads(self.corpo.decode("utf-8"))

    @property
    def texto(self):
        return self.corpo.decode("utf-8")

    def cabecalho(self, nome):
        return self.cabecalhos.get(nome.lower())


class Base(unittest.TestCase):
    """Sobe um servidor por teste, com pasta de dados e painel temporarios."""
    com_perfil = True
    com_leads = True

    def setUp(self):
        # No Windows um arquivo recem-criado pode ficar preso por instantes (antivirus, indexador).
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.apagar_pasta_temporaria)
        self.raiz = Path(self._tmp.name)
        self.dados, self.painel = self.raiz / "dados", self.raiz / "painel"
        self.dados.mkdir()
        self.painel.mkdir()
        (self.painel / "index.html").write_text(
            '<meta name="token" content="{{TOKEN}}"><p>painel</p>', encoding="utf-8")
        (self.painel / "app.js").write_text("console.log('ok');", encoding="utf-8")
        (self.raiz / "segredo.html").write_text("SEGREDO-FORA-DO-PAINEL", encoding="utf-8")
        (self.raiz / "segredo.js").write_text("SEGREDO-JS", encoding="utf-8")
        (self.painel / "dados.json").write_text('{"nao":"servir"}', encoding="utf-8")
        if self.com_perfil:
            self.gravar_perfil(perfil_ficticio())
        self.motor, self.geo = MotorDeMentira(), GeoDeMentira()
        # Nenhum teste roda o Docker de verdade: o executor e sempre falso.
        self.comandos = []
        self.ligador = LigadorDoMotor(self.raiz, self.dados, executar=self.executor_falso)
        self.iniciar_servidor()
        if self.com_leads:
            self.popular_banco()

    def diagnostico_falso(self, motor):
        """Nos testes nunca se roda `docker info` de verdade."""
        from kit import diagnostico as d
        return None if motor.no_ar() else {"estado": "motor_parado", **d.DIAGNOSTICOS["motor_parado"]}

    def executor_falso(self, comando, **kwargs):
        self.comandos.append((comando, kwargs))
        return types.SimpleNamespace(returncode=0)

    def iniciar_servidor(self):
        self.srv = servidor.Servidor(porta=0, pasta_dados=self.dados, pasta_painel=self.painel,
                                     motor=self.motor, geo=self.geo, token=TOKEN, diagnostico=self.diagnostico_falso,
                                     ligador=self.ligador)
        self.porta = self.srv.porta
        threading.Thread(target=self.srv.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
        self.addCleanup(self.parar_servidor, self.srv)

    def apagar_pasta_temporaria(self, tentativas=8):
        """Apaga a pasta do teste. No Windows o banco pode ficar preso por instantes, entao tenta de novo.

        Se mesmo assim nao der, escreve a mensagem completa do erro (nao e falha de teste: a pasta fica no
        temp do sistema), para a causa poder ser investigada.
        """
        for n in range(1, tentativas + 1):
            try:
                shutil.rmtree(self._tmp.name)
                return
            except FileNotFoundError:
                return
            except OSError as e:
                erro = e
                time.sleep(0.25 * n)
        sys.stderr.write("\n[aviso] nao consegui apagar " + self._tmp.name + f" depois de {tentativas} tentativas: "
                         f"{type(erro).__name__}: {erro}\n")

    @staticmethod
    def parar_servidor(srv):
        # Uma busca iniciada pelo teste pode ainda estar gravando no banco: espera ela acabar antes de fechar.
        fim = time.time() + 15
        while srv.busca_ativa is not None and time.time() < fim:
            time.sleep(0.05)
        srv.shutdown()
        srv.server_close()

    def gravar_perfil(self, perfil):
        (self.dados / "perfil.json").write_text(json.dumps(perfil), encoding="utf-8")

    def popular_banco(self, linhas=None):
        conn = banco.abrir(str(self.dados / "leads.db"))
        bid = banco.criar_busca(conn, "padaria", "Cidade Teste", "DF", "rapida", {}, False)
        banco.salvar_leads(conn, bid, limpeza.ler_csv(csv_texto(linhas))[0], "Cidade Teste", "DF", False)
        conn.close()
        return bid

    def lead_id(self, nome):
        conn = banco.abrir(str(self.dados / "leads.db"))
        try:
            return next(l["id"] for l in banco.todos_os_leads(conn) if l["nome"] == nome)
        finally:
            conn.close()

    def pedir(self, metodo, caminho, corpo=None, host="auto", token=None, cabecalhos=None,
              tipo="application/json", bruto=None, tamanho_declarado=None):
        """Faz o pedido controlando cada cabecalho. host=None nao manda Host nenhum."""
        con = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=20)
        try:
            con.putrequest(metodo, caminho, skip_host=True, skip_accept_encoding=True)
            if host == "auto":
                host = f"127.0.0.1:{self.porta}"
            if host is not None:
                con.putheader("Host", host)
            dados = bruto if bruto is not None else (json.dumps(corpo).encode() if corpo is not None else b"")
            if token is not None:
                con.putheader("X-Token", token)
            if tipo and (dados or tamanho_declarado):
                con.putheader("Content-Type", tipo)
            if dados or tamanho_declarado or metodo in ("POST", "PUT", "PATCH"):
                con.putheader("Content-Length", str(tamanho_declarado if tamanho_declarado is not None else len(dados)))
            for k, v in (cabecalhos or {}).items():
                con.putheader(k, v)
            con.endheaders(dados if tamanho_declarado is None else b"")
            r = con.getresponse()
            return Resp(r.status, {k.lower(): v for k, v in r.getheaders()}, r.read())
        finally:
            con.close()

    def ler(self, caminho, **kw):
        return self.pedir("GET", caminho, **kw)

    def escrever(self, metodo, caminho, corpo=None, **kw):
        kw.setdefault("token", TOKEN)
        return self.pedir(metodo, caminho, corpo if corpo is not None else {}, **kw)

    def esperar_busca(self, busca_id, limite=10):
        fim = time.time() + limite
        while time.time() < fim:
            d = self.ler(f"/api/buscas/{busca_id}").json
            if d["status"] in ("ok", "erro"):
                return d
            time.sleep(0.05)
        self.fail("a busca não terminou a tempo")

# ===================================================== botao "Ligar o motor"

class TestLigarMotor(Base):
    def esperar_ligador(self):
        self.ligador.thread.join(10)
        self.assertFalse(self.ligador.thread.is_alive())

    def test_sem_token_da_401_e_nada_roda(self):
        self.motor.ligado = False
        self.assertEqual(self.pedir("POST", "/api/motor/ligar", {}).status, 401)
        self.assertEqual(self.pedir("POST", "/api/motor/ligar", {}, token="errado").status, 401)
        self.assertEqual(self.comandos, [])

    def test_liga_com_comando_fixo_sem_shell_na_pasta_do_kit(self):
        self.motor.ligado = False
        r = self.escrever("POST", "/api/motor/ligar")
        self.assertEqual((r.status, r.json), (202, {"estado": "ligando"}))
        self.esperar_ligador()
        comando, kwargs = self.comandos[0]
        self.assertEqual(comando, ["docker", "compose", "-f", str((self.raiz / "docker-compose.yml").resolve()), "up", "-d"])
        self.assertNotIn("shell", kwargs)
        self.assertEqual(kwargs["cwd"], str(self.raiz))
        self.assertEqual(kwargs["timeout"], 600)
        self.assertEqual(self.ler("/api/estado").json["ligando_motor"]["estado"], "ok")

    def test_responde_na_hora_sem_esperar_o_comando(self):
        self.motor.ligado = False
        solto = threading.Event()
        self.ligador._executar = lambda c, **k: (solto.wait(10), types.SimpleNamespace(returncode=0))[1]
        inicio = time.time()
        r = self.escrever("POST", "/api/motor/ligar")
        self.assertEqual(r.status, 202)
        self.assertLess(time.time() - inicio, 3)
        estado = self.ler("/api/estado").json["ligando_motor"]
        self.assertEqual(estado["estado"], "ligando")
        self.assertIn("alguns minutos", estado["mensagem"])
        solto.set()
        self.esperar_ligador()

    def test_segundo_clique_durante_a_execucao_nao_dispara_outro_comando(self):
        self.motor.ligado = False
        solto = threading.Event()
        self.ligador._executar = lambda c, **k: (self.comandos.append(c), solto.wait(10), types.SimpleNamespace(returncode=0))[2]
        self.assertEqual(self.escrever("POST", "/api/motor/ligar").status, 202)
        self.assertEqual(self.escrever("POST", "/api/motor/ligar").status, 202)
        solto.set()
        self.esperar_ligador()
        self.assertEqual(len(self.comandos), 1)

    def test_motor_ja_ligado_da_409_e_nao_roda_nada(self):
        r = self.escrever("POST", "/api/motor/ligar")
        self.assertEqual(r.status, 409)
        self.assertEqual(self.comandos, [])

    def test_docker_parado_ou_ausente_recusa_e_nao_roda_nada(self):
        self.motor.ligado = False
        for estado in ("docker_parado", "docker_ausente"):
            self.srv.diagnostico = lambda m, e=estado: {"estado": e, **diagnostico_mod.DIAGNOSTICOS[e]}
            r = self.escrever("POST", "/api/motor/ligar")
            self.assertEqual(r.status, 409, estado)
            self.assertIn("digite powershell" if estado == "docker_parado" else "Docker", r.json["erro"])
        self.assertEqual(self.comandos, [])

    def test_nada_do_navegador_chega_ao_comando(self):
        self.motor.ligado = False
        r = self.escrever("POST", "/api/motor/ligar", {"comando": "calc.exe", "args": ["--x"], "cwd": "C:\\", "shell": True},
                          cabecalhos={"X-Comando": "calc.exe"})
        self.assertEqual(r.status, 202)
        self.esperar_ligador()
        self.assertEqual(self.comandos[0][0][:3], ["docker", "compose", "-f"])
        self.assertNotIn("calc", " ".join(self.comandos[0][0]))
        self.assertEqual(self.comandos[0][0][-2:], ["up", "-d"])

    def test_erro_do_comando_vira_mensagem_simples_e_o_detalhe_vai_para_o_log(self):
        self.motor.ligado = False

        def falha(comando, stdout=None, **kw):
            stdout.write(b"Error response from daemon: SEGREDO-DO-LOG\n")
            return types.SimpleNamespace(returncode=1)

        self.ligador._executar = falha
        self.escrever("POST", "/api/motor/ligar")
        self.esperar_ligador()
        estado = self.ler("/api/estado").json["ligando_motor"]
        self.assertEqual(estado["estado"], "erro")
        self.assertIn("log-motor.txt", estado["mensagem"])
        self.assertNotIn("SEGREDO-DO-LOG", json.dumps(estado))
        self.assertIn("SEGREDO-DO-LOG", (self.dados / "log-motor.txt").read_text(encoding="utf-8"))

    def test_tempo_esgotado_e_docker_ausente_viram_mensagem_simples(self):
        self.motor.ligado = False
        for erro, trecho in ((subprocess.TimeoutExpired("docker", 600), "10 minutos"), (FileNotFoundError(), "Não encontrei o Docker")):
            def levanta(comando, **kw):
                raise erro
            self.ligador._executar = levanta
            self.escrever("POST", "/api/motor/ligar")
            self.esperar_ligador()
            estado = self.ler("/api/estado").json["ligando_motor"]
            self.assertEqual(estado["estado"], "erro")
            self.assertIn(trecho, estado["mensagem"])

    def test_o_log_nao_e_servido_por_nenhuma_rota(self):
        (self.dados / "log-motor.txt").write_text("SEGREDO-DO-LOG", encoding="utf-8")
        # O log fica em dados/, fora da pasta que o servidor serve como painel.
        self.assertFalse(self.ligador.arquivo_log.resolve().is_relative_to(self.srv.pasta_painel.resolve()))
        self.assertEqual(self.ligador.arquivo_log.parent, self.dados)
        for caminho in ("/log-motor.txt", "/dados/log-motor.txt", "/../dados/log-motor.txt", "/%2e%2e/dados/log-motor.txt",
                        "/api/log-motor.txt", "/api/motor/log", "/api/motor/ligar/log"):
            r = self.ler(caminho)
            self.assertIn(r.status, (400, 404, 405), caminho)
            self.assertNotIn(b"SEGREDO-DO-LOG", r.corpo, caminho)
        for caminho in ROTAS_DE_LEITURA:
            self.assertNotIn(b"SEGREDO-DO-LOG", self.ler(caminho).corpo, caminho)

    def test_rotas_nao_listam_nada_para_ler_o_log(self):
        rotas = [f.__name__ for _, _, f, _ in servidor.ROTAS]
        self.assertNotIn("rota_motor_log", rotas)
        self.assertEqual([c.pattern for m, c, f, e in servidor.ROTAS if "motor" in c.pattern], [r"/api/motor/ligar\Z"])


# ===================================================== degrau 1: segurança

ROTAS_DE_LEITURA = ["/api/estado", "/api/perfil", "/api/leads", "/api/leads/1", "/api/buscas",
                    "/api/buscas/1", "/api/exportar", "/", "/app.js"]
ROTAS_DE_ESCRITA = [("PUT", "/api/perfil"), ("POST", "/api/buscas"), ("PATCH", "/api/leads/1"),
                    ("POST", "/api/leads/reavaliar"), ("POST", "/api/motor/ligar")]


class TestSeguranca(Base):
    def test_host_errado_e_recusado_em_toda_rota_de_leitura(self):
        for host in ("evil.invalid", "evil.invalid:80", "127.0.0.1:9999", "localhost:9999",
                     "192.168.0.10", "127.0.0.1", "localhost", "0.0.0.0", "", None):
            for caminho in ROTAS_DE_LEITURA:
                with self.subTest(host=host, caminho=caminho):
                    r = self.ler(caminho, host=host)
                    self.assertEqual(r.status, 403)
                    self.assertIn("Endereço não permitido", r.json["erro"])

    def test_host_errado_e_recusado_em_toda_rota_de_escrita_mesmo_com_token(self):
        for host in ("evil.invalid", f"192.168.0.10:{self.porta}", None):
            for metodo, caminho in ROTAS_DE_ESCRITA:
                with self.subTest(host=host, caminho=caminho):
                    self.assertEqual(self.escrever(metodo, caminho, host=host).status, 403)

    def test_hosts_validos_passam(self):
        for host in (f"127.0.0.1:{self.porta}", f"localhost:{self.porta}", f"LOCALHOST:{self.porta}"):
            with self.subTest(host=host):
                self.assertEqual(self.ler("/api/estado", host=host).status, 200)

    def test_escrita_sem_token_ou_com_token_errado_e_recusada(self):
        for metodo, caminho in ROTAS_DE_ESCRITA:
            for token in (None, "", "errado", TOKEN + "x", TOKEN[:-1]):
                with self.subTest(caminho=caminho, token=token):
                    r = self.pedir(metodo, caminho, {}, token=token)
                    self.assertEqual(r.status, 401)

    def test_recusa_de_token_nao_altera_nada(self):
        antes = (self.dados / "perfil.json").read_text(encoding="utf-8")
        self.pedir("PUT", "/api/perfil", perfil_ficticio(), token="errado")
        self.assertEqual((self.dados / "perfil.json").read_text(encoding="utf-8"), antes)
        self.assertEqual(self.pedir("PATCH", f"/api/leads/{self.lead_id('Pão Sem Site')}",
                                    {"status": "fechado"}).status, 401)
        self.assertEqual(self.ler(f"/api/leads/{self.lead_id('Pão Sem Site')}").json["status"], "novo")

    def test_token_certo_deixa_escrever(self):
        self.assertEqual(self.escrever("POST", "/api/leads/reavaliar").status, 200)

    def test_leitura_nao_exige_token(self):
        self.assertEqual(self.ler("/api/estado").status, 200)

    def test_nenhuma_resposta_tem_cabecalho_de_cors(self):
        respostas = [
            self.ler("/api/estado"), self.ler("/api/nao-existe"), self.ler("/", host="evil.invalid"),
            self.pedir("POST", "/api/leads/reavaliar", {}), self.pedir("OPTIONS", "/api/estado"),
            self.escrever("POST", "/api/leads/reavaliar"), self.ler("/app.js"), self.ler("/"),
            self.pedir("DELETE", "/api/estado"),
            self.ler("/api/estado", cabecalhos={"Origin": f"http://127.0.0.1:{self.porta}"}),
        ]
        for r in respostas:
            self.assertEqual([k for k in r.cabecalhos if k.startswith("access-control")], [], r.status)

    def test_options_e_recusado_sem_cors(self):
        r = self.pedir("OPTIONS", "/api/leads/reavaliar", cabecalhos={
            "Access-Control-Request-Method": "POST"})
        self.assertEqual(r.status, 405)
        self.assertNotIn("access-control-allow-origin", r.cabecalhos)

    def test_preflight_de_outro_site_e_recusado(self):
        r = self.pedir("OPTIONS", "/api/leads/reavaliar", cabecalhos={
            "Origin": "http://evil.invalid", "Access-Control-Request-Method": "POST"})
        self.assertEqual(r.status, 403)
        self.assertNotIn("access-control-allow-origin", r.cabecalhos)

    def test_origin_de_outro_site_e_recusado_mesmo_com_token_e_em_leitura(self):
        for origem in ("http://evil.invalid", "null", "https://127.0.0.1:%d" % self.porta,
                       "http://127.0.0.1:1"):
            with self.subTest(origem=origem):
                self.assertEqual(self.escrever("POST", "/api/leads/reavaliar",
                                               cabecalhos={"Origin": origem}).status, 403)
                self.assertEqual(self.ler("/api/estado", cabecalhos={"Origin": origem}).status, 403)

    def test_origin_do_proprio_servidor_passa(self):
        for host in ("127.0.0.1", "localhost"):
            origem = f"http://{host}:{self.porta}"
            self.assertEqual(self.escrever("POST", "/api/leads/reavaliar",
                                           cabecalhos={"Origin": origem}).status, 200)

    def test_escrita_so_com_content_type_json(self):
        for tipo in ("text/plain", "application/x-www-form-urlencoded", "multipart/form-data", None):
            with self.subTest(tipo=tipo):
                r = self.pedir("POST", "/api/leads/reavaliar", bruto=b"{}", token=TOKEN, tipo=tipo)
                self.assertEqual(r.status, 415)

    def test_content_type_json_com_charset_passa(self):
        r = self.pedir("POST", "/api/leads/reavaliar", {}, token=TOKEN, tipo="application/json; charset=utf-8")
        self.assertEqual(r.status, 200)

    def test_corpo_grande_demais(self):
        r = self.pedir("PUT", "/api/perfil", token=TOKEN, tamanho_declarado=2_000_000)
        self.assertEqual(r.status, 413)
        r = self.pedir("PUT", "/api/perfil", bruto=b"x" * 1_100_000, token=TOKEN)
        self.assertEqual(r.status, 413)

    def test_json_quebrado_ou_que_nao_e_objeto(self):
        for bruto in (b"{quebrado", b"[1,2]", b"\"texto\"", b"\xff\xfe"):
            with self.subTest(bruto=bruto):
                self.assertEqual(self.pedir("POST", "/api/buscas", bruto=bruto, token=TOKEN).status, 400)

    def test_token_nunca_aparece_fora_do_index(self):
        corpos = [self.ler(c).texto for c in ("/api/estado", "/api/perfil", "/api/leads", "/api/buscas",
                                               "/api/nao-existe", "/app.js")]
        corpos.append(self.ler("/", host="evil.invalid").texto)
        corpos.append(self.pedir("POST", "/api/leads/reavaliar", {}, token="errado").texto)
        corpos.append(json.dumps(self.ler("/api/estado").cabecalhos))
        for c in corpos:
            self.assertNotIn(TOKEN, c)

    def test_servidor_so_escuta_em_127_0_0_1(self):
        self.assertEqual(self.srv.server_address[0], "127.0.0.1")
        for endereco in ("0.0.0.0", "192.168.0.1", "", "::"):
            with self.subTest(endereco=endereco), self.assertRaises(ValueError):
                servidor.Servidor(porta=0, pasta_dados=self.dados, pasta_painel=self.painel,
                                  endereco=endereco)

    def test_cabecalhos_de_protecao_nas_respostas(self):
        r = self.ler("/api/estado")
        self.assertEqual(r.cabecalho("X-Content-Type-Options"), "nosniff")
        self.assertEqual(r.cabecalho("Cache-Control"), "no-store")
        self.assertEqual(r.cabecalho("X-Frame-Options"), "DENY")
        self.assertIn("frame-ancestors 'none'", self.ler("/").cabecalho("Content-Security-Policy"))

    def test_rota_inexistente_e_metodo_errado(self):
        self.assertEqual(self.ler("/api/nao-existe").status, 404)
        self.assertEqual(self.pedir("DELETE", "/api/estado").status, 405)
        self.assertEqual(self.pedir("POST", "/api/estado", {}, token=TOKEN).status, 405)
        self.assertEqual(self.ler("/api/leads/reavaliar").status, 405)
        self.assertEqual(self.ler("/api/leads/abc").status, 404)

    def test_erro_interno_nao_vaza_detalhe(self):
        (self.dados / "perfil.json").unlink()
        (self.dados / "perfil.json").mkdir()  # ler isso como arquivo vai estourar
        with contextlib.redirect_stderr(io.StringIO()):
            r = self.ler("/api/estado")
        self.assertEqual(r.status, 500)
        self.assertNotIn("Traceback", r.texto)
        self.assertNotIn(str(self.dados), r.texto)
        self.assertIn("Algo deu errado", r.json["erro"])

    def test_varias_requisicoes_ao_mesmo_tempo(self):
        resultados = []

        def chamar():
            resultados.append(self.ler("/api/leads").status)

        threads = [threading.Thread(target=chamar) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(resultados, [200] * 8)


# ===================================================== degrau 2: estado

class TestEstado(Base):
    def test_tudo_certo(self):
        d = self.ler("/api/estado").json
        self.assertEqual(d["versao_kit"], servidor.VERSAO)
        self.assertTrue(d["motor_no_ar"])
        self.assertEqual(d["perfil"], {"existe": True, "valido": True, "erros": [], "avisos": []})
        self.assertIsNone(d["busca_em_andamento"])

    def test_motor_desligado(self):
        self.motor.ligado = False
        self.assertFalse(self.ler("/api/estado").json["motor_no_ar"])

    def test_perfil_invalido_lista_os_problemas(self):
        p = perfil_ficticio()
        p["negocio"]["oferta"] = ""
        self.gravar_perfil(p)
        d = self.ler("/api/estado").json["perfil"]
        self.assertEqual((d["existe"], d["valido"]), (True, False))
        self.assertTrue(any("negocio.oferta" in e for e in d["erros"]))

    def test_perfil_ausente(self):
        (self.dados / "perfil.json").unlink()
        d = self.ler("/api/estado").json["perfil"]
        self.assertEqual((d["existe"], d["valido"]), (False, False))


# ===================================================== degrau 3: perfil

class TestPerfil(Base):
    def test_ler(self):
        d = self.ler("/api/perfil").json
        self.assertEqual(d["perfil"]["negocio"]["oferta"], "Sites para negócios locais")
        self.assertEqual(d["erros"], [])

    def test_ler_sem_perfil(self):
        (self.dados / "perfil.json").unlink()
        r = self.ler("/api/perfil")
        self.assertEqual(r.status, 404)
        self.assertIn("entrevista", r.json["erro"])

    def test_gravar_invalido_da_422_e_nao_muda_o_arquivo(self):
        antes = (self.dados / "perfil.json").read_text(encoding="utf-8")
        p = perfil_ficticio()
        p["mensagens"]["whatsapp"] = "compre {apelido}"
        r = self.escrever("PUT", "/api/perfil", p)
        self.assertEqual(r.status, 422)
        self.assertTrue(r.json["erros"])
        self.assertEqual((self.dados / "perfil.json").read_text(encoding="utf-8"), antes)
        self.assertFalse((self.dados / "perfil.anterior.json").exists())

    def test_gravar_valido_guarda_o_anterior(self):
        antigo = (self.dados / "perfil.json").read_text(encoding="utf-8")
        novo = perfil_ficticio()
        novo["negocio"]["oferta"] = "Contabilidade para pequenos negócios"
        r = self.escrever("PUT", "/api/perfil", novo)
        self.assertEqual(r.status, 200)
        gravado = json.loads((self.dados / "perfil.json").read_text(encoding="utf-8"))
        self.assertEqual(gravado["negocio"]["oferta"], "Contabilidade para pequenos negócios")
        self.assertEqual((self.dados / "perfil.anterior.json").read_text(encoding="utf-8"), antigo)
        self.assertFalse((self.dados / "perfil.json.tmp").exists())
        self.assertEqual(self.ler("/api/perfil").json["perfil"]["negocio"]["oferta"],
                         "Contabilidade para pequenos negócios")

    def test_gravar_corrige_peso_e_avisa(self):
        p = perfil_ficticio()
        p["pontuacao"]["regras"][0]["peso"] = 9
        r = self.escrever("PUT", "/api/perfil", p)
        self.assertEqual(r.status, 200)
        self.assertTrue(r.json["avisos"])
        self.assertEqual(r.json["perfil"]["pontuacao"]["regras"][0]["peso"], 5)

    def test_gravar_sem_perfil_anterior_nao_cria_backup(self):
        (self.dados / "perfil.json").unlink()
        self.assertEqual(self.escrever("PUT", "/api/perfil", perfil_ficticio()).status, 200)
        self.assertFalse((self.dados / "perfil.anterior.json").exists())

    def test_gravar_remove_dado_sensivel(self):
        p = perfil_ficticio()
        p["negocio"]["cpf"] = "000.000.000-00"
        self.escrever("PUT", "/api/perfil", p)
        self.assertNotIn("cpf", (self.dados / "perfil.json").read_text(encoding="utf-8"))


# ===================================================== degrau 4: leads

class TestLeads(Base):
    def listar(self, consulta=""):
        return self.ler("/api/leads" + consulta).json

    def nomes(self, consulta=""):
        return [l["nome"] for l in self.listar(consulta)["leads"]]

    def test_padrao_esconde_excluidos_e_ordena_por_nota(self):
        d = self.listar()
        self.assertEqual(d["leads"][0]["nome"], "Pão Sem Site")
        self.assertEqual(d["leads"][0]["letra"], "A")
        self.assertNotIn("Sem Telefone", self.nomes())
        self.assertNotIn("Café Rede", self.nomes())

    def test_excluidos_com_o_motivo(self):
        d = self.listar("?excluidos=sim")
        motivos = {l["nome"]: l["excluido_por"] for l in d["leads"]}
        self.assertEqual(motivos["Sem Telefone"], "sem telefone")
        self.assertIn("possível rede (nome repetido em 3 endereços)", motivos["Café Rede"])
        self.assertEqual(self.listar("?excluidos=todos")["total"], 11)

    def test_filtros(self):
        self.assertEqual(self.nomes("?letra=A"), ["Pão Sem Site"])
        self.assertEqual(self.nomes("?q=pao%20sem"), ["Pão Sem Site"])
        self.assertEqual(self.nomes("?q=restaurante"), ["Reserva"])
        self.assertEqual(self.nomes("?status=fechado"), [])
        self.assertEqual(self.nomes("?busca=999"), [])

    def test_filtro_por_busca(self):
        self.assertEqual(self.listar("?busca=1")["total"], self.listar()["total"])

    def test_paginacao(self):
        d = self.listar("?limite=2&offset=1")
        self.assertEqual((len(d["leads"]), d["total"], d["limite"], d["offset"]), (2, self.listar()["total"], 2, 1))

    def test_filtros_invalidos_dao_400_em_portugues(self):
        for q in ("?letra=Z", "?status=vendido", "?busca=x", "?excluidos=talvez", "?limite=0",
                  "?limite=abc", "?limite=5000", "?offset=-1"):
            with self.subTest(q=q):
                r = self.ler("/api/leads" + q)
                self.assertEqual(r.status, 400)
                self.assertIn("erro", r.json)

    def test_sem_perfil_valido_da_409(self):
        (self.dados / "perfil.json").unlink()
        r = self.ler("/api/leads")
        self.assertEqual(r.status, 409)
        self.assertIn("perfil", r.json["erro"])

    def test_detalhe_do_lead(self):
        d = self.ler(f"/api/leads/{self.lead_id('Pão Sem Site')}").json
        self.assertEqual(d["nome"], "Pão Sem Site")
        self.assertIn("sem site (+3)", d["motivos"])
        self.assertEqual(d["frase_do_motivo"], "não achei um site no perfil do Google Maps")
        msg = d["mensagens"]["whatsapp"]
        self.assertFalse(msg["padrao"])
        self.assertIn("Notei que não achei um site no perfil do Google Maps.", msg["texto"])
        self.assertEqual(d["mensagem_editada"], "")

    def test_detalhe_usa_modelo_provisorio_se_o_perfil_nao_tem(self):
        p = perfil_ficticio()
        p["mensagens"] = {}
        self.gravar_perfil(p)
        msg = self.ler(f"/api/leads/{self.lead_id('Pão Sem Site')}").json["mensagens"]["whatsapp"]
        self.assertTrue(msg["padrao"])
        self.assertIn("não escrevo mais", msg["texto"])

    def test_lead_inexistente(self):
        self.assertEqual(self.ler("/api/leads/99999").status, 404)

    def test_alterar_status_anotacao_e_mensagem(self):
        lid = self.lead_id("Pão Sem Site")
        r = self.escrever("PATCH", f"/api/leads/{lid}", {"status": "contatado", "anotacao": "ligar terça"})
        self.assertEqual(r.status, 200)
        self.assertEqual((r.json["status"], r.json["anotacao"]), ("contatado", "ligar terça"))
        self.escrever("PATCH", f"/api/leads/{lid}", {"mensagem_editada": "Oi, minha versão"})
        d = self.ler(f"/api/leads/{lid}").json
        self.assertEqual((d["status"], d["anotacao"], d["mensagem_editada"]),
                         ("contatado", "ligar terça", "Oi, minha versão"))
        self.assertEqual(self.nomes("?status=contatado"), ["Pão Sem Site"])

    def test_alterar_com_valor_invalido(self):
        lid = self.lead_id("Pão Sem Site")
        for corpo in ({"status": "vendido"}, {"status": 3}, {"anotacao": 5}, {"anotacao": "x" * 2001},
                      {"mensagem_editada": "x" * 5001}, {"nome": "outro"}, {}, {"status": "novo", "id": 9}):
            with self.subTest(corpo=str(corpo)[:40]):
                self.assertEqual(self.escrever("PATCH", f"/api/leads/{lid}", corpo).status, 400)

    def test_alterar_lead_inexistente(self):
        self.assertEqual(self.escrever("PATCH", "/api/leads/99999", {"status": "novo"}).status, 404)

    def test_possivel_rede_e_recalculada_e_nunca_gravada(self):
        self.assertIn("Café Rede", [l["nome"] for l in self.listar("?excluidos=sim")["leads"]])
        # tira um dos tres enderecos do banco: a marca some sozinha, nada ficou gravado
        conn = banco.abrir(str(self.dados / "leads.db"))
        conn.execute("DELETE FROM leads_busca WHERE lead_id IN (SELECT id FROM leads WHERE chave='p:pid6c')")
        conn.execute("DELETE FROM leads WHERE chave='p:pid6c'")
        conn.commit()
        colunas = [c[1] for c in conn.execute("PRAGMA table_info(leads)")]
        conn.close()
        self.assertFalse([c for c in colunas if "rede" in c or "exclu" in c])
        excluidos = [l["nome"] for l in self.listar("?excluidos=sim")["leads"]]
        self.assertNotIn("Café Rede", excluidos)
        self.assertIn("Café Rede", self.nomes())

    def test_leitura_e_escrita_ao_mesmo_tempo(self):
        lid = self.lead_id("Pão Sem Site")
        resultados = []

        def ler():
            resultados.append(self.ler("/api/leads").status)

        def escrever(i):
            resultados.append(self.escrever("PATCH", f"/api/leads/{lid}", {"anotacao": f"n{i}"}).status)

        threads = [threading.Thread(target=ler) for _ in range(6)]
        threads += [threading.Thread(target=escrever, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(resultados, [200] * 12)


# ===================================================== degrau 5: reavaliar

class TestReavaliar(Base):
    def test_mudar_o_perfil_muda_notas_sem_perder_o_trabalho_do_usuario(self):
        lid = self.lead_id("Pão Sem Site")
        self.escrever("PATCH", f"/api/leads/{lid}", {"status": "contatado", "anotacao": "ligar"})
        antes = self.ler(f"/api/leads/{lid}").json
        self.assertEqual(antes["letra"], "A")
        p = perfil_ficticio()
        p["pontuacao"]["regras"] = [{"id": "nota_baixa", "peso": 5}]
        self.escrever("PUT", "/api/perfil", p)
        r = self.escrever("POST", "/api/leads/reavaliar")
        self.assertEqual(r.status, 200)
        self.assertEqual(r.json["leads"], 11)
        self.assertEqual(sum(r.json["por_letra"].values()), 11)
        depois = self.ler(f"/api/leads/{lid}").json
        self.assertNotEqual((depois["nota"], depois["letra"]), (antes["nota"], antes["letra"]))
        self.assertEqual((depois["status"], depois["anotacao"]), ("contatado", "ligar"))
        conn = banco.abrir(str(self.dados / "leads.db"))
        gravado = banco.obter_lead(conn, lid)
        conn.close()
        self.assertEqual((gravado["nota"], gravado["letra"]), (depois["nota"], depois["letra"]))

    def test_sem_perfil_valido_da_409(self):
        (self.dados / "perfil.json").unlink()
        self.assertEqual(self.escrever("POST", "/api/leads/reavaliar").status, 409)


# ===================================================== degrau 6: buscas

CORPO_BUSCA = {"categoria": "padaria", "cidade": "Cidade Teste", "uf": "df", "tamanho": "rapida"}


class TestBuscas(Base):
    com_leads = False

    def criar(self, **mudancas):
        corpo = {**CORPO_BUSCA, **mudancas}
        return self.escrever("POST", "/api/buscas", {k: v for k, v in corpo.items() if v is not None})

    def test_busca_roda_do_comeco_ao_fim_pela_api(self):
        r = self.criar()
        self.assertEqual(r.status, 202)
        d = self.esperar_busca(r.json["id"])
        self.assertEqual((d["status"], d["total_leads"], d["uf"]), ("ok", 11, "DF"))
        self.assertEqual(self.motor.pedidos[0]["keywords"], ["padaria em Cidade Teste DF"])
        self.assertEqual(self.geo.chamadas, [("Cidade Teste", "DF")])
        leads = self.ler(f"/api/leads?busca={r.json['id']}").json
        self.assertEqual(leads["leads"][0]["nome"], "Pão Sem Site")
        self.assertIsNone(self.ler("/api/estado").json["busca_em_andamento"])

    def test_progresso_aparece_no_meio_da_busca(self):
        self.motor.segurar = threading.Event()
        bid = self.criar().json["id"]
        fim = time.time() + 5
        d = self.ler(f"/api/buscas/{bid}").json
        while d["etapa"] != "Esperando o motor" and time.time() < fim:
            time.sleep(0.02)
            d = self.ler(f"/api/buscas/{bid}").json
        self.assertEqual((d["status"], d["etapa"]), ("working", "Esperando o motor"))
        self.assertEqual(self.ler("/api/estado").json["busca_em_andamento"], bid)
        self.motor.segurar.set()
        final = self.esperar_busca(bid)
        self.assertEqual(final["status"], "ok")
        self.assertIsNone(final["etapa"])

    def test_so_uma_busca_por_vez(self):
        self.motor.segurar = threading.Event()
        primeira = self.criar().json["id"]
        r = self.criar(categoria="restaurante")
        self.assertEqual(r.status, 409)
        self.assertEqual(r.json["busca_em_andamento"], primeira)
        self.motor.segurar.set()
        self.esperar_busca(primeira)
        self.assertEqual(self.criar(categoria="restaurante").status, 202)

    def test_campos_invalidos(self):
        casos = [dict(categoria=None), dict(categoria="  "), dict(categoria="x" * 81), dict(categoria=5),
                 dict(cidade=None), dict(uf=None), dict(uf="ZZ"), dict(uf="DFX"), dict(tamanho="gigante"),
                 dict(email="sim"), dict(cidade="com\nquebra")]
        for mudancas in casos:
            with self.subTest(mudancas=str(mudancas)[:40]):
                self.assertEqual(self.criar(**mudancas).status, 400)
        self.assertEqual(self.motor.pedidos, [])

    def test_perfil_invalido_da_409_e_nao_cria_busca(self):
        (self.dados / "perfil.json").unlink()
        self.assertEqual(self.criar().status, 409)
        self.assertEqual(self.ler("/api/buscas").json["buscas"], [])

    def test_motor_desligado_da_503(self):
        self.motor.ligado = False
        r = self.criar()
        self.assertEqual(r.status, 503)
        self.assertIn("docker compose up -d", r.json["erro"])

    def test_erro_do_motor_aparece_na_busca(self):
        self.motor.falha = motor_mod.ErroMotor("passou do tempo")
        d = self.esperar_busca(self.criar().json["id"])
        self.assertEqual((d["status"], d["erro"]), ("erro", "passou do tempo"))
        self.assertIsNone(self.ler("/api/estado").json["busca_em_andamento"])

    def test_erro_inesperado_tambem_libera_o_servidor(self):
        self.motor.falha = RuntimeError("quebrou")
        with contextlib.redirect_stderr(io.StringIO()):
            d = self.esperar_busca(self.criar().json["id"])
        self.assertEqual(d["status"], "erro")
        self.assertEqual(self.criar().status, 202)

    def test_listar_e_ler_buscas(self):
        a = self.criar().json["id"]
        self.esperar_busca(a)
        b = self.criar(categoria="academia").json["id"]
        self.esperar_busca(b)
        ids = [x["id"] for x in self.ler("/api/buscas").json["buscas"]]
        self.assertEqual(ids, [b, a])
        self.assertEqual(self.ler("/api/buscas/9999").status, 404)

    def test_resposta_da_busca_nao_vaza_o_pedido_interno(self):
        d = self.esperar_busca(self.criar().json["id"])
        self.assertNotIn("parametros", d)
        self.assertNotIn("job_id", d)

    def test_busca_pendurada_de_antes_vira_erro_ao_reiniciar(self):
        conn = banco.abrir(str(self.dados / "leads.db"))
        bid = banco.criar_busca(conn, "x", "C", "DF", "rapida", {}, False)
        banco.atualizar_busca(conn, bid, status="working")
        conn.close()
        self.iniciar_servidor()  # novo servidor na mesma pasta, como depois de fechar e abrir o kit
        d = self.ler(f"/api/buscas/{bid}").json
        self.assertEqual(d["status"], "erro")
        self.assertIn("Interrompida", d["erro"])


# ===================================================== degrau 7: exportar

class TestExportar(Base):
    def baixar(self, consulta=""):
        return self.ler("/api/exportar" + consulta, token=TOKEN)

    def linhas(self, r):
        return list(csv.reader(io.StringIO(r.texto.lstrip("﻿"))))

    def test_csv_utf8_com_bom_e_nome_do_arquivo(self):
        r = self.baixar()
        self.assertEqual(r.status, 200)
        self.assertTrue(r.cabecalho("Content-Type").startswith("text/csv"))
        self.assertIn("attachment", r.cabecalho("Content-Disposition"))
        self.assertTrue(r.corpo.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(self.linhas(r)[0][:3], ["Nota", "Pontos", "Negócio"])

    def test_usa_os_mesmos_filtros_da_lista(self):
        self.assertEqual(len(self.linhas(self.baixar("?letra=A"))), 2)
        self.assertEqual(len(self.linhas(self.baixar("?excluidos=todos"))), 12)
        self.assertEqual(len(self.linhas(self.baixar())), 1 + self.ler("/api/leads").json["total"])

    def test_filtro_invalido_da_400(self):
        self.assertEqual(self.baixar("?letra=Z").status, 400)

    def test_sem_perfil_da_409(self):
        (self.dados / "perfil.json").unlink()
        self.assertEqual(self.baixar().status, 409)

    def test_formula_e_telefone_com_mais_saem_protegidos(self):
        conn = banco.abrir(str(self.dados / "leads.db"))
        bid = banco.criar_busca(conn, "x", "C", "DF", "rapida", {}, False)
        perigosos = [
            linha(50, title="=HYPERLINK(\"http://x.invalid\")", phone="+55 61 98888-0050"),
            linha(51, title="Estrangeiro", phone="+1 202 555 0151"),
            linha(52, title="@arroba", phone="(61) 3333-0052"),
        ]
        banco.salvar_leads(conn, bid, limpeza.ler_csv(csv_texto(perigosos))[0], "C", "DF", False)
        conn.close()
        linhas = {l[2].lstrip("'"): l for l in self.linhas(self.baixar("?excluidos=todos"))[1:]}
        self.assertEqual(linhas['=HYPERLINK("http://x.invalid")'][2][0], "'")
        self.assertEqual(linhas['=HYPERLINK("http://x.invalid")'][7], "(61) 98888-0050")
        self.assertEqual(linhas["Estrangeiro"][7], "'+1 202 555 0151")
        self.assertEqual(linhas["@arroba"][2], "'@arroba")
        for l in self.linhas(self.baixar("?excluidos=todos"))[1:]:
            for celula in (l[2], l[7], l[13], l[16], l[17]):
                self.assertFalse(celula.startswith(("=", "+", "-", "@", "\t", "\r")), celula)


# ===================================================== degrau 8: painel estático

class TestEstatico(Base):
    def test_index_leva_o_token_do_servidor(self):
        r = self.ler("/")
        self.assertEqual(r.status, 200)
        self.assertTrue(r.cabecalho("Content-Type").startswith("text/html"))
        self.assertIn(f'content="{TOKEN}"', r.texto)
        self.assertNotIn("{{TOKEN}}", r.texto)
        self.assertEqual(self.ler("/index.html").status, 200)

    def test_token_novo_a_cada_inicio(self):
        outro = servidor.Servidor(porta=0, pasta_dados=self.dados, pasta_painel=self.painel,
                                  motor=self.motor, geo=self.geo)
        self.addCleanup(outro.server_close)
        self.assertNotEqual(outro.token, TOKEN)
        self.assertGreaterEqual(len(outro.token), 32)

    def test_javascript_e_servido_com_o_tipo_certo(self):
        r = self.ler("/app.js")
        self.assertEqual(r.status, 200)
        self.assertIn("javascript", r.cabecalho("Content-Type"))

    def test_nao_sai_da_pasta_do_painel(self):
        tentativas = ["/../segredo.html", "/../segredo.js", "/%2e%2e/segredo.html", "/%2e%2e%2fsegredo.js",
                      "/..%5csegredo.html", "/..\\segredo.html", "/./../segredo.js",
                      "//..//segredo.html", "/app.js/../../segredo.js", "/..%00/segredo.html"]
        for caminho in tentativas:
            with self.subTest(caminho=caminho):
                r = self.ler(caminho)
                self.assertEqual(r.status, 404)
                self.assertNotIn("SEGREDO", r.texto)

    def test_so_serve_extensoes_do_painel(self):
        self.assertEqual(self.ler("/dados.json").status, 404)
        self.assertEqual(self.ler("/nao-existe.js").status, 404)
        self.assertEqual(self.ler("/..").status, 404)
        self.assertEqual(self.ler("/sub/").status, 404)

    def test_so_get_serve_arquivo(self):
        self.assertEqual(self.pedir("POST", "/", {}, token=TOKEN).status, 405)
        self.assertEqual(self.pedir("PUT", "/index.html", {}, token=TOKEN).status, 405)

    def test_pasta_do_painel_vazia_da_404_e_nao_quebra(self):
        (self.painel / "index.html").unlink()
        self.assertEqual(self.ler("/").status, 404)



# ===================================================== etapa 1 da fase 3: xlsx, opcoes e contagem

class TestExportarXlsx(Base):
    def baixar(self, consulta=""):
        return self.ler("/api/exportar?formato=xlsx" + consulta, token=TOKEN)

    def test_devolve_um_xlsx_de_verdade(self):
        r = self.baixar()
        self.assertEqual(r.status, 200)
        self.assertIn("spreadsheetml.sheet", r.cabecalho("Content-Type"))
        self.assertIn('filename="leads.xlsx"', r.cabecalho("Content-Disposition"))
        self.assertTrue(r.corpo.startswith(b"PK"))
        import zipfile
        z = zipfile.ZipFile(io.BytesIO(r.corpo))
        self.assertIn("xl/worksheets/sheet1.xml", z.namelist())

    def test_usa_os_mesmos_filtros_da_lista(self):
        import zipfile
        import re as _re

        def linhas(consulta):
            z = zipfile.ZipFile(io.BytesIO(self.baixar(consulta).corpo))
            return len(_re.findall(r"<row ", z.read("xl/worksheets/sheet1.xml").decode("utf-8"))) - 1

        self.assertEqual(linhas(""), self.ler("/api/leads").json["total"])
        self.assertEqual(linhas("&letra=A"), 1)
        self.assertEqual(linhas("&excluidos=todos"), 11)

    def test_formato_invalido_filtro_invalido_e_sem_perfil(self):
        self.assertEqual(self.ler("/api/exportar?formato=pdf", token=TOKEN).status, 400)
        self.assertEqual(self.baixar("&letra=Z").status, 400)
        (self.dados / "perfil.json").unlink()
        self.assertEqual(self.baixar().status, 409)

    def test_csv_continua_sendo_o_padrao(self):
        self.assertTrue(self.ler("/api/exportar", token=TOKEN).cabecalho("Content-Type").startswith("text/csv"))
        self.assertTrue(self.ler("/api/exportar?formato=csv", token=TOKEN).cabecalho("Content-Type").startswith("text/csv"))


class TestExportarExigeToken(Base):
    """A exportacao entrega os dados dos leads em arquivo, entao leva o token como as escritas."""

    def test_sem_token_ou_com_token_errado_e_recusada(self):
        for formato in ("csv", "xlsx"):
            for token in (None, "", "errado", TOKEN + "x"):
                with self.subTest(formato=formato, token=token):
                    r = self.ler(f"/api/exportar?formato={formato}", token=token)
                    self.assertEqual(r.status, 401)
                    self.assertNotIn("Pão Sem Site".encode("utf-8"), r.corpo)  # nenhum dado vaza na recusa
                    self.assertEqual(r.json["erro"], "Falta a permissão para alterar dados. Recarregue o painel.")

    def test_com_token_certo_baixa(self):
        self.assertEqual(self.ler("/api/exportar?formato=xlsx", token=TOKEN).status, 200)
        self.assertEqual(self.ler("/api/exportar", token=TOKEN).status, 200)

    def test_host_errado_vence_o_token(self):
        self.assertEqual(self.ler("/api/exportar", token=TOKEN, host="evil.invalid").status, 403)

    def test_origin_de_fora_vence_o_token(self):
        r = self.ler("/api/exportar", token=TOKEN, cabecalhos={"Origin": "http://evil.invalid"})
        self.assertEqual(r.status, 403)

    def test_as_outras_leituras_continuam_sem_token(self):
        for caminho in ("/api/estado", "/api/leads", "/api/perfil", "/api/opcoes", "/api/buscas"):
            self.assertEqual(self.ler(caminho).status, 200, caminho)


class TestOpcoes(Base):
    def test_traz_tudo_que_o_formulario_precisa(self):
        d = self.ler("/api/opcoes").json
        ids = [r["id"] for r in d["regras"]]
        self.assertEqual(ids, list(servidor.validar_perfil.REGRAS["regras"]))
        self.assertEqual(next(r for r in d["regras"] if r["id"] == "sem_site"),
                         {"id": "sem_site", "texto": "sem site", "peso_padrao": 3})
        self.assertIn("franquia", [e["id"] for e in d["exclusoes"]])
        self.assertEqual(d["marcadores"], ["nome", "cidade", "categoria", "motivo", "meu_nome", "minha_empresa"])
        self.assertEqual((d["peso_minimo"], d["peso_maximo"]), (0, 5))
        self.assertEqual(d["cortes_padrao"], {"a": 0.7, "b": 0.4})
        self.assertEqual(d["status_lead"], ["novo", "contatado", "respondeu", "fechado", "descartado"])
        self.assertEqual(len(d["ufs"]), 27)
        self.assertIn("rapida", [t["id"] for t in d["tamanhos"]])

    def test_nao_exige_perfil_nem_token(self):
        (self.dados / "perfil.json").unlink()
        self.assertEqual(self.ler("/api/opcoes").status, 200)

    def test_tem_as_mesmas_regras_que_o_validador_aceita(self):
        d = self.ler("/api/opcoes").json
        p = perfil_ficticio()
        p["pontuacao"]["regras"] = [{"id": r["id"], "peso": r["peso_padrao"]} for r in d["regras"]]
        r = self.escrever("PUT", "/api/perfil", p)
        self.assertEqual(r.status, 200, r.texto)
        self.assertEqual(r.json["avisos"], [])


class TestContagemPorLetra(Base):
    def test_lista_traz_a_contagem_por_letra(self):
        d = self.ler("/api/leads").json
        self.assertEqual(set(d["contagem_por_letra"]), {"A", "B", "C"})
        self.assertEqual(sum(d["contagem_por_letra"].values()), d["total"])

    def test_filtrar_por_letra_nao_zera_a_contagem_das_outras(self):
        todos = self.ler("/api/leads").json["contagem_por_letra"]
        so_a = self.ler("/api/leads?letra=A").json
        self.assertEqual(so_a["total"], todos["A"])
        self.assertEqual(so_a["contagem_por_letra"], todos)

    def test_contagem_respeita_os_outros_filtros(self):
        d = self.ler("/api/leads?q=pao%20sem").json
        self.assertEqual(sum(d["contagem_por_letra"].values()), 1)
        d = self.ler("/api/leads?excluidos=sim").json
        self.assertEqual(sum(d["contagem_por_letra"].values()), d["total"])

class TestBuscaMediaPelaApi(Base):
    com_leads = False

    def test_media_roda_pela_api_e_mostra_o_ponto_no_progresso(self):
        csvs = [csv_texto([linha(n, title=f"Negócio {n}") for n in range(a, a + 4)]) for a in (1, 3, 5, 7, 9)]
        self.motor.csv = csvs
        self.srv.dormir = lambda s: None  # sem esperar os 15 s entre pontos
        r = self.escrever("POST", "/api/buscas", {**CORPO_BUSCA, "tamanho": "media"})
        self.assertEqual(r.status, 202)
        d = self.esperar_busca(r.json["id"])
        self.assertEqual((d["status"], d["total_leads"], d["tamanho"]), ("ok", 12, "media"))
        self.assertEqual(len(self.motor.pedidos), 5)
        self.assertEqual(self.ler(f"/api/leads?busca={r.json['id']}&excluidos=todos").json["total"], 12)

    def test_ampla_e_recusada_e_aparece_como_em_breve(self):
        self.assertEqual(self.escrever("POST", "/api/buscas", {**CORPO_BUSCA, "tamanho": "ampla"}).status, 400)
        d = self.ler("/api/opcoes").json
        self.assertEqual(d["tamanhos_em_breve"], ["ampla"])
        self.assertEqual({t["id"]: t["pontos"] for t in d["tamanhos"]}, {"rapida": 1, "media": 5})


class TestListaGrande(Base):
    """650 leads FICTICIOS: o painel carrega por partes de 100 e nada se perde nem se repete."""
    com_leads = False

    def setUp(self):
        super().setUp()
        self.popular_banco(leads_em_massa(650))

    def pagina(self, offset, limite=100, extra=""):
        return self.ler(f"/api/leads?limite={limite}&offset={offset}&excluidos=todos{extra}").json

    def test_650_leads_em_partes_de_100_sem_repetir_nem_perder(self):
        ids, total = [], None
        for offset in range(0, 700, 100):
            d = self.pagina(offset)
            total = d["total"]
            ids += [l["id"] for l in d["leads"]]
        self.assertEqual(total, 650)
        self.assertEqual(len(ids), 650)
        self.assertEqual(len(set(ids)), 650)

    def test_a_ordem_das_partes_e_a_mesma_de_uma_chamada_so(self):
        em_partes = [l["id"] for o in range(0, 700, 100) for l in self.pagina(o)["leads"]]
        inteira = [l["id"] for l in self.pagina(0, limite=1000)["leads"]]
        self.assertEqual(em_partes, inteira)

    def test_a_mesma_parte_pedida_duas_vezes_e_igual(self):
        self.assertEqual(self.pagina(200)["leads"], self.pagina(200)["leads"])

    def test_melhores_primeiro_e_excluidos_no_fim(self):
        leads = self.pagina(0, limite=1000)["leads"]
        dentro = [l for l in leads if not l["excluido_por"]]
        fora = [l for l in leads if l["excluido_por"]]
        self.assertEqual(leads, dentro + fora)
        notas = [l["nota"] for l in dentro]
        self.assertEqual(notas, sorted(notas, reverse=True))
        self.assertTrue(fora)  # ha excluidos (sem telefone e rede ficticia)

    def test_padrao_nao_mostra_excluidos_e_a_contagem_bate(self):
        d = self.ler("/api/leads?limite=1000").json
        self.assertTrue(all(not l["excluido_por"] for l in d["leads"]))
        self.assertEqual(sum(d["contagem_por_letra"].values()), d["total"])
        todos = self.ler("/api/leads?limite=1000&excluidos=todos").json
        self.assertGreater(todos["total"], d["total"])

    def test_pedir_alem_do_fim_devolve_lista_vazia(self):
        d = self.pagina(650)
        self.assertEqual((d["total"], d["leads"]), (650, []))
        self.assertEqual(self.pagina(5000)["leads"], [])

    def test_rede_ficticia_e_marcada_nas_tres_unidades(self):
        d = self.ler("/api/leads?limite=1000&excluidos=sim&q=rede%20ficticia").json
        self.assertGreaterEqual(d["total"], 3)
        self.assertTrue(all("possível rede" in l["excluido_por"] for l in d["leads"]))

    def test_650_leads_respondem_em_tempo_razoavel(self):
        import time as _t
        inicio = _t.perf_counter()
        for offset in (0, 100, 200):
            self.pagina(offset)
        self.assertLess(_t.perf_counter() - inicio, 5.0)  # folga grande: o objetivo e pegar um desastre


class TestPorQueEWhatsapp(Base):
    def test_resumo_traz_o_por_que_curto_e_nao_o_longo(self):
        l = next(x for x in self.ler("/api/leads?limite=1000").json["leads"] if x["nome"] == "Pão Sem Site")
        self.assertEqual(l["por_que_curto"][0], "sem site")
        self.assertNotIn("por_que", l)
        self.assertNotIn("whatsapp_numero", l)

    def test_detalhe_traz_frases_simples_com_pontos(self):
        d = self.ler(f"/api/leads/{self.lead_id('Pão Sem Site')}").json
        textos = [i["texto"] for i in d["por_que"]]
        self.assertIn("Não achei um site no perfil do Google Maps.", textos)
        self.assertIn("A nota no Google Maps é 4,7.", textos)
        self.assertIn("O perfil tem 80 avaliações no Google Maps.", textos)
        self.assertEqual(next(i["pontos"] for i in d["por_que"] if i["rotulo"] == "sem site"), 3)
        self.assertEqual(sum(i["pontos"] for i in d["por_que"]), d["nota"])
        for t in textos:
            self.assertTrue(t[0].isupper() and t.endswith("."), t)
            self.assertNotIn("—", t)

    def test_lead_sem_regra_batida_tem_lista_vazia(self):
        d = self.ler(f"/api/leads/{self.lead_id('Nota Péssima')}").json
        self.assertEqual(d["por_que"], [])

    def test_whatsapp_numero_so_para_celular_e_so_digitos(self):
        celular = self.ler(f"/api/leads/{self.lead_id('Pão Sem Site')}").json
        self.assertEqual(celular["whatsapp_numero"], "5561999990001")
        self.assertTrue(celular["whatsapp_numero"].isdigit())
        fixo = self.ler(f"/api/leads/{self.lead_id('Só Rede Social')}").json
        self.assertIsNone(fixo["whatsapp_numero"])

    def test_whatsapp_numero_ignora_o_que_nao_e_digito(self):
        self.popular_banco([linha(70, title="Telefone Sujo", phone='(61) 99999-0070"><script>', website="")])
        d = self.ler(f"/api/leads/{self.lead_id('Telefone Sujo')}").json
        if d["whatsapp_numero"] is not None:
            self.assertRegex(d["whatsapp_numero"], r"^55\d{11}$")


class TestFiltrosRapidosNaApi(Base):
    com_leads = False

    def setUp(self):
        super().setUp()
        p = perfil_ficticio()
        p["exclusoes"] = []
        self.gravar_perfil(p)
        self.popular_banco(leads_em_massa(300))

    def lista(self, consulta=""):
        return self.ler("/api/leads?limite=1000&excluidos=todos" + consulta).json

    def test_sem_site_so_traz_leads_sem_site_e_a_nota_explica_igual(self):
        d = self.lista("&sem_site=1")
        self.assertTrue(0 < d["total"] < 300)
        for l in d["leads"]:
            self.assertEqual(l["site"], "")
            self.assertIn("sem site", l["por_que_curto"])  # a regra de nota concorda com o filtro

    def test_com_celular_so_traz_celular_e_a_nota_explica_igual(self):
        d = self.lista("&celular=1")
        self.assertTrue(0 < d["total"] < 300)
        for l in d["leads"]:
            self.assertTrue(l["celular"])
            self.assertIn("telefone provavelmente é WhatsApp", l["por_que_curto"])

    def test_quem_fica_de_fora_do_filtro_nao_tem_a_regra(self):
        todos = self.lista()["leads"]
        com = {l["id"] for l in self.lista("&sem_site=1")["leads"]}
        for l in todos:
            self.assertEqual(l["id"] in com, "sem site" in l["por_que_curto"], l["nome"])

    def test_combina_com_os_outros_filtros_e_com_a_contagem(self):
        d = self.lista("&sem_site=1&celular=1&letra=A")
        self.assertTrue(all(l["letra"] == "A" and l["site"] == "" and l["celular"] for l in d["leads"]))
        so_filtros = self.lista("&sem_site=1&celular=1")
        self.assertEqual(sum(so_filtros["contagem_por_letra"].values()), so_filtros["total"])
        self.assertEqual(d["contagem_por_letra"], so_filtros["contagem_por_letra"])  # a letra nao zera as outras

    def test_valor_invalido_da_400(self):
        self.assertEqual(self.ler("/api/leads?sem_site=talvez").status, 400)
        self.assertEqual(self.ler("/api/leads?celular=7").status, 400)

    def test_a_exportacao_respeita_os_filtros_rapidos(self):
        import zipfile
        import re as _re
        r = self.ler("/api/exportar?formato=xlsx&excluidos=todos&sem_site=1&celular=1", token=TOKEN)
        linhas = len(_re.findall(r"<row ", zipfile.ZipFile(io.BytesIO(r.corpo)).read("xl/worksheets/sheet1.xml").decode("utf-8"))) - 1
        self.assertEqual(linhas, self.lista("&sem_site=1&celular=1")["total"])


class TestEtapa4NoServidor(Base):
    com_leads = False

    def criar(self, **extra):
        return self.escrever("POST", "/api/buscas", {**CORPO_BUSCA, **extra})

    def test_estado_traz_o_motivo_quando_o_motor_esta_desligado(self):
        self.motor.ligado = False
        d = self.ler("/api/estado").json
        self.assertFalse(d["motor_no_ar"])
        self.assertEqual(d["motor_diagnostico"]["estado"], "motor_parado")
        self.assertEqual(d["motor_diagnostico"]["comando"], "docker compose up -d")

    def test_estado_sem_diagnostico_quando_o_motor_esta_no_ar(self):
        d = self.ler("/api/estado").json
        self.assertTrue(d["motor_no_ar"])
        self.assertIsNone(d["motor_diagnostico"])

    def test_docker_parado_aparece_no_estado_e_no_503(self):
        from kit import diagnostico as dg
        self.srv.diagnostico = lambda motor: {"estado": "docker_parado", **dg.DIAGNOSTICOS["docker_parado"]}
        self.motor.ligado = False
        self.assertEqual(self.ler("/api/estado").json["motor_diagnostico"]["estado"], "docker_parado")
        r = self.criar()
        self.assertEqual(r.status, 503)
        self.assertIn("O Docker está desligado", r.json["erro"])
        self.assertIn("Abra o Docker Desktop", r.json["erro"])
        self.assertEqual(r.json["motor_diagnostico"]["estado"], "docker_parado")

    def test_503_por_motor_parado_diz_o_comando(self):
        self.motor.ligado = False
        r = self.criar()
        self.assertEqual(r.status, 503)
        self.assertIn("docker compose up -d", r.json["erro"])

    def test_busca_publica_traz_contagens_e_tempo_estimado(self):
        bid = self.criar().json["id"]
        d = self.esperar_busca(bid)
        self.assertEqual((d["total_leads"], d["novos"], d["ja_existiam"], d["fora_da_lista"]), (11, 11, 0, 4))
        self.assertEqual((d["pontos"], d["tempo_estimado"]), (1, "cerca de 1 minuto"))
        self.assertTrue(d["criada_em"] and d["terminou_em"])
        self.assertIsNone(d["erro_tipo"])
        segunda = self.esperar_busca(self.criar().json["id"])
        self.assertEqual((segunda["novos"], segunda["ja_existiam"]), (0, 11))

    def test_busca_com_erro_traz_o_tipo(self):
        self.geo.erro = CidadeNaoEncontrada("Não achei a cidade X-DF. Confira o nome e a sigla do estado.")
        d = self.esperar_busca(self.criar().json["id"])
        self.assertEqual((d["status"], d["erro_tipo"]), ("erro", "cidade"))
        self.assertIn("Não achei a cidade", d["erro"])

    def test_resultado_zero_nao_e_erro(self):
        self.motor.csv = csv_texto([])
        d = self.esperar_busca(self.criar().json["id"])
        self.assertEqual((d["status"], d["total_leads"], d["erro"], d["erro_tipo"]), ("ok", 0, None, None))

    def test_ponto_atual_aparece_durante_a_busca_media(self):
        self.motor.segurar = threading.Event()
        self.srv.dormir = lambda s: None
        bid = self.criar(tamanho="media").json["id"]
        d = self.ler(f"/api/buscas/{bid}").json
        fim = time.time() + 5
        while d["etapa"] != "Esperando o motor (ponto 1 de 5)" and time.time() < fim:
            time.sleep(0.02)
            d = self.ler(f"/api/buscas/{bid}").json
        self.assertEqual((d["status"], d["ponto"], d["pontos"]), ("working", 1, 5))
        self.assertEqual(d["tempo_estimado"], "cerca de 5 a 6 minutos")
        self.motor.segurar.set()
        self.esperar_busca(bid)

    def test_busca_em_andamento_continua_depois_de_recarregar_a_pagina(self):
        self.motor.segurar = threading.Event()
        bid = self.criar().json["id"]
        # "recarregar a pagina" = outro cliente perguntando de novo: o estado vem do servidor
        self.assertEqual(self.ler("/api/estado").json["busca_em_andamento"], bid)
        r = self.criar(categoria="restaurante")
        self.assertEqual((r.status, r.json["busca_em_andamento"]), (409, bid))
        self.motor.segurar.set()
        self.esperar_busca(bid)

    def test_nao_existe_rota_de_cancelar_busca(self):
        bid = self.criar().json["id"]
        self.esperar_busca(bid)
        for metodo, caminho in (("DELETE", f"/api/buscas/{bid}"), ("PUT", f"/api/buscas/{bid}"),
                                ("PATCH", f"/api/buscas/{bid}")):
            self.assertEqual(self.escrever(metodo, caminho).status, 405, caminho)
        for caminho in (f"/api/buscas/{bid}/cancelar", f"/api/buscas/{bid}/cancel", "/api/buscas/cancelar"):
            self.assertIn(self.escrever("POST", caminho).status, (404, 405), caminho)
        rotas = {(m, regex.pattern) for m, regex, _f, _e in servidor.ROTAS}
        self.assertFalse([r for r in rotas if "cancel" in r[1].lower() or r[0] == "DELETE"])

    def test_opcoes_trazem_o_tempo_estimado_de_cada_tamanho(self):
        d = self.ler("/api/opcoes").json
        self.assertEqual({t["id"]: t["tempo_estimado"] for t in d["tamanhos"]},
                         {"rapida": "cerca de 1 minuto", "media": "cerca de 5 a 6 minutos"})
        self.assertEqual(d["tamanhos_em_breve"], ["ampla"])


if __name__ == "__main__":
    unittest.main()
