"""Testes do painel que nao precisam de navegador: olham os arquivos como texto e servem o painel de verdade.

O comportamento na tela (estados, tema, teclado) e conferido no navegador, ver testes/demo_painel.py.
"""
import re
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from kit import servidor

PAINEL = Path(servidor.__file__).resolve().parent / "painel"
ARQUIVOS = sorted(p for p in PAINEL.rglob("*") if p.is_file())
CODIGO = [p for p in ARQUIVOS if p.suffix in (".html", ".js", ".css")]
JS = [p for p in ARQUIVOS if p.suffix == ".js"]
HTML = [p for p in ARQUIVOS if p.suffix == ".html"]

# Unicas URLs externas que o painel pode citar (abrir conversa no WhatsApp, quando a tela de leads existir).
URLS_PERMITIDAS = ("https://wa.me/",)


def ler(p):
    return p.read_text(encoding="utf-8")


def codigo(p):
    """O arquivo sem comentarios: as regras de seguranca valem para o que roda, nao para o que explica."""
    texto = ler(p)
    if p.suffix in (".js", ".css"):
        texto = re.sub(r"/\*.*?\*/", "", texto, flags=re.S)
    if p.suffix == ".js":
        texto = re.sub(r"(?<![:\w'\"])//.*$", "", texto, flags=re.M)
    return texto


class TestSegurancaDoCodigo(unittest.TestCase):
    def test_ha_arquivos_para_testar(self):
        nomes = {p.name for p in ARQUIVOS}
        for esperado in ("index.html", "estilo.css", "app.js", "api.js", "util.js", "dom.js", "tema.js"):
            self.assertIn(esperado, nomes)

    def test_nada_de_innerhtml_eval_ou_atributos_de_evento_em_js(self):
        proibidos = re.compile(
            r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|\beval\s*\(|new\s+Function|"
            r"setAttribute\(\s*['\"]on|javascript:")
        for p in CODIGO:
            achou = proibidos.search(codigo(p))
            self.assertIsNone(achou, f"{p.name}: {achou.group(0) if achou else ''}")

    def test_html_sem_script_inline_nem_atributo_de_evento(self):
        for p in HTML:
            texto = ler(p)
            self.assertIsNone(re.search(r"<script(?![^>]*\bsrc=)[^>]*>", texto), p.name)  # a CSP bloquearia
            self.assertIsNone(re.search(r"\son[a-z]+\s*=", texto), p.name)

    def test_nenhuma_url_externa(self):
        for p in CODIGO:
            for url in re.findall(r"https?://[^\s'\"`)]+", ler(p)):
                self.assertTrue(url.startswith(URLS_PERMITIDAS), f"{p.name}: {url}")

    def test_sem_endereco_fixo_do_servidor_no_js(self):
        for p in JS:
            self.assertIsNone(re.search(r"127\.0\.0\.1|localhost", codigo(p)), p.name)

    def test_fetch_so_no_api_js(self):
        rede = re.compile(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource")
        for p in JS:
            if p.name == "api.js":
                self.assertIn("fetch(", codigo(p))
            else:
                self.assertIsNone(rede.search(codigo(p)), p.name)

    def test_token_nunca_vai_para_o_armazenamento_do_navegador(self):
        for p in JS:
            for linha in ler(p).splitlines():
                if re.search(r"localStorage|sessionStorage|document\.cookie|indexedDB", linha):
                    self.assertNotIn("token", linha.lower(), f"{p.name}: {linha.strip()}")

    def test_sem_travessao_em_nenhum_texto(self):
        for p in ARQUIVOS:
            if p.suffix in (".png", ".ico"):
                continue
            texto = ler(p)
            self.assertNotIn("—", texto, p.name)  # travessao
            self.assertNotIn("–", texto, p.name)  # traco medio


class TestPaginaEImportacoes(unittest.TestCase):
    def setUp(self):
        self.html = ler(PAINEL / "index.html")

    def test_basico_da_pagina(self):
        self.assertIn('<html lang="pt-BR">', self.html)
        self.assertIn('name="viewport"', self.html)
        self.assertIn('name="token" content="{{TOKEN}}"', self.html)
        self.assertIn("<title>Lead Kit Silver</title>", self.html)
        self.assertIn('rel="icon"', self.html)

    def test_tudo_que_o_html_referencia_existe(self):
        for caminho in re.findall(r'(?:src|href)="(/[^"#]+)"', self.html):
            self.assertTrue((PAINEL / caminho.lstrip("/")).is_file(), caminho)

    def test_tudo_que_o_js_importa_existe(self):
        for p in JS:
            texto = ler(p)
            for rel in re.findall(r"from\s+'(\./[^']+)'", texto) + re.findall(r"import\(\s*'(\./[^']+)'", texto):
                self.assertTrue((PAINEL / rel).is_file(), f"{p.name} importa {rel}")

    def test_cada_aba_do_html_tem_modulo_de_tela(self):
        abas = re.findall(r'data-aba="(\w+)"', self.html)
        self.assertEqual(abas, ["buscar", "leads", "oferta"])
        for aba in abas:
            self.assertTrue((PAINEL / f"tela-{aba}.js").is_file(), aba)

    def test_abas_do_html_e_do_util_sao_as_mesmas(self):
        util = ler(PAINEL / "util.js")
        achou = re.search(r"export const ABAS = \[([^\]]*)\]", util)
        self.assertEqual(re.findall(r"'(\w+)'", achou.group(1)), re.findall(r'data-aba="(\w+)"', self.html))


class TestContratoComAApi(unittest.TestCase):
    """Toda rota que o JavaScript chama existe no servidor, com o metodo certo."""

    @staticmethod
    def chamadas():
        achadas = []
        for p in JS:
            texto = ler(p)
            for caminho in re.findall(r"\bler\(\s*['\"`](/api/[^'\"`?]*)", texto):
                achadas.append(("GET", caminho, p.name))
            for caminho in re.findall(r"\bbaixar\(\s*['\"`](/api/[^'\"`?]*)", texto):
                achadas.append(("GET", caminho, p.name))
            for metodo, caminho in re.findall(r"\bescrever\(\s*['\"](\w+)['\"]\s*,\s*['\"`](/api/[^'\"`?]*)", texto):
                achadas.append((metodo, caminho, p.name))
        return achadas

    def test_achou_chamadas(self):
        self.assertIn(("GET", "/api/estado", "app.js"), self.chamadas())

    def test_toda_chamada_tem_rota(self):
        for metodo, caminho, arquivo in self.chamadas():
            real = re.sub(r"\$\{[^}]*\}", "1", caminho)
            casou = [(m, escreve) for m, regex, _f, escreve in servidor.ROTAS if regex.match(real)]
            self.assertTrue(casou, f"{arquivo} chama {caminho}, que nao existe no servidor")
            self.assertIn(metodo, [m for m, _ in casou], f"{arquivo}: {metodo} {caminho}")
            for (m, escreve), (_m, _r, funcao, _e) in zip(casou, [r for r in servidor.ROTAS if r[1].match(real)]):
                if m == metodo:
                    # escrita leva token; leitura nao, exceto as que entregam arquivo (exportar)
                    esperado = metodo != "GET" or funcao in servidor.ROTAS_COM_TOKEN_NA_LEITURA
                    self.assertEqual(escreve or funcao in servidor.ROTAS_COM_TOKEN_NA_LEITURA, esperado)


class TestPainelServidoDeVerdade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.srv = servidor.Servidor(porta=0, pasta_dados=Path(cls._tmp.name), token="token-de-teste")
        threading.Thread(target=cls.srv.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.porta}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls._tmp.cleanup()

    def baixar(self, caminho):
        with urllib.request.urlopen(self.base + caminho, timeout=10) as r:
            return r.status, r.headers["Content-Type"], r.read()

    def test_todo_arquivo_do_painel_e_servido_com_o_tipo_certo(self):
        esperado = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}
        for p in ARQUIVOS:
            caminho = "/" + p.relative_to(PAINEL).as_posix()
            status, tipo, _ = self.baixar(caminho)
            self.assertEqual(status, 200, caminho)
            self.assertTrue(tipo.startswith(esperado[p.suffix]), f"{caminho}: {tipo}")

    def test_raiz_leva_o_token_e_nenhum_outro_arquivo_leva(self):
        _, _, corpo = self.baixar("/")
        self.assertIn(b'content="token-de-teste"', corpo)
        self.assertNotIn(b"{{TOKEN}}", corpo)
        for p in JS + [PAINEL / "estilo.css"]:
            _, _, dados = self.baixar("/" + p.name)
            self.assertNotIn(b"token-de-teste", dados, p.name)


if __name__ == "__main__":
    unittest.main()
