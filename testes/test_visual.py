"""Regras visuais do painel que não podem se perder em um redesign: leitura fácil, tudo local e nome em um lugar só."""
import ast
import re
import unittest
from pathlib import Path

from kit import produto, servidor

KIT = Path(servidor.__file__).resolve().parent
PAINEL = KIT / "painel"
CSS = (PAINEL / "estilo.css").read_text(encoding="utf-8")
HTML = (PAINEL / "index.html").read_text(encoding="utf-8")

# Seletores que podem usar a fonte monoespaçada. Só números e comandos, nunca rótulos.
MONO_PERMITIDO = {
    ":root", ".num, .count, code", ".passos li::before", ".pill em", ".nota .pts b", ".why li b", ".passo-busca .n", ".etapa .n", ".seg-peso label b.num",
}


def regras_do_css():
    """[(seletor, corpo)] sem comentários."""
    texto = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    saida = []
    for m in re.finditer(r"([^{}@][^{}]*)\{([^{}]*)\}", texto):
        saida.append((" ".join(m.group(1).split()), m.group(2)))
    return saida


class TestLeituraFacil(unittest.TestCase):
    def test_corpo_em_16px(self):
        corpo = next(c for s, c in regras_do_css() if s == "body")
        self.assertRegex(corpo, r"font:\s*400 16px/")

    def test_nenhuma_letra_abaixo_de_13px(self):
        menores = []
        for seletor, corpo in regras_do_css():
            for m in re.finditer(r"font-size:\s*([\d.]+)px", corpo):
                if float(m.group(1)) < 13:
                    menores.append((seletor, m.group(0)))
            for m in re.finditer(r"font:\s*(?:\d{3}\s+)?([\d.]+)px", corpo):
                if float(m.group(1)) < 13:
                    menores.append((seletor, m.group(0)))
        self.assertEqual(menores, [])

    def test_so_pixels_conhecidos_sem_rem_ou_em_escondendo_letra_pequena(self):
        self.assertIsNone(re.search(r"font(-size)?:[^;]*\b0?\.\d+(rem|em)\b", CSS))

    def test_fonte_monoespacada_so_em_numeros_e_comandos(self):
        usam = {s for s, c in regras_do_css() if ("--font-mono" in c or "Plex Mono" in c) and s != "@font-face"}
        self.assertTrue(usam)
        self.assertLessEqual(usam, MONO_PERMITIDO, usam - MONO_PERMITIDO)

    def test_rotulo_nunca_em_maiusculas_corridas_nem_espacado(self):
        for seletor, corpo in regras_do_css():
            self.assertNotIn("text-transform", corpo, seletor)
            self.assertNotRegex(corpo, r"letter-spacing:\s*0\.0[5-9]", seletor)

    def test_alvos_de_clique_de_44px_nos_controles_principais(self):
        for seletor in (".btn", ".tab", ".pill", ".chip", ".input, .select"):
            corpo = next(c for s, c in regras_do_css() if s == seletor)
            self.assertRegex(corpo, r"min-height:\s*(4[4-9]|[5-9]\d)px", seletor)


class TestFontesLocais(unittest.TestCase):
    def test_so_ibm_plex_em_woff2_e_a_licenca(self):
        arquivos = sorted(p.name for p in (PAINEL / "fontes").iterdir())
        self.assertEqual(arquivos, [
            "LICENCA-IBM-Plex.txt", "ibm-plex-mono-latin-400-normal.woff2", "ibm-plex-mono-latin-500-normal.woff2",
            "ibm-plex-sans-latin-400-normal.woff2", "ibm-plex-sans-latin-600-normal.woff2"])

    def test_arquivos_de_fonte_sao_woff2_de_verdade(self):
        for p in (PAINEL / "fontes").glob("*.woff2"):
            self.assertEqual(p.read_bytes()[:4], b"wOF2", p.name)

    def test_o_css_so_pede_fontes_do_proprio_painel(self):
        urls = re.findall(r"url\(\s*[\"']?([^\"')]+)", CSS)
        self.assertTrue(urls)
        for u in urls:
            self.assertTrue(u.startswith("/fontes/"), u)
            self.assertTrue((PAINEL / u.lstrip("/")).is_file(), u)

    def test_nenhuma_fonte_de_servico_externo(self):
        self.assertNotRegex(CSS + HTML, r"fonts\.(googleapis|gstatic)|@import|cdn\.|typekit")

    def test_nao_ha_outra_fonte_nem_licenca_alem_da_ibm_plex(self):
        self.assertFalse(list(PAINEL.rglob("*atkinson*")) + list(PAINEL.rglob("*Atkinson*")))
        licenca = (PAINEL / "fontes" / "LICENCA-IBM-Plex.txt").read_text(encoding="utf-8")
        self.assertIn("IBM Corp", licenca)
        self.assertIn("SIL OPEN FONT LICENSE", licenca)
        creditos = (KIT.parent / "CREDITS.md").read_text(encoding="utf-8")
        self.assertIn("IBM Plex", creditos)
        self.assertNotIn("Atkinson", creditos)


class TestFormasDaNota(unittest.TestCase):
    def test_a_b_e_c_tem_formas_e_cores_diferentes(self):
        corpos = {s: c for s, c in regras_do_css()}
        formas = {letra: corpos[f".nota.{letra} .forma::before"] for letra in "ABC"}
        self.assertEqual(len(set(formas.values())), 3)
        self.assertIn("border-radius: 50%", formas["A"])       # círculo
        self.assertIn("rotate(45deg)", formas["C"])             # losango
        self.assertNotIn("50%", formas["B"])                    # quadrado arredondado
        cores = {letra: corpos[f".nota.{letra}"] for letra in "ABC"}
        self.assertEqual(len(set(cores.values())), 3)
        # A é cheia e B é só contorno: a diferença entre as duas não depende só da cor.
        self.assertIn("--cor-fundo: var(--good)", cores["A"])
        self.assertIn("--cor-fundo: transparent", cores["B"])
        self.assertIn("border-width: 3px", formas["B"])

    def test_c_nao_usa_vermelho_nem_a_cor_de_erro(self):
        c = next(corpo for s, corpo in regras_do_css() if s == ".nota.C")
        self.assertNotIn("--bad", c)
        self.assertIn("--neutral", c)


class TestNomeDoProduto(unittest.TestCase):
    def test_o_nome_esta_escrito_so_em_produto_py(self):
        achados = []
        for p in KIT.glob("*.py"):
            if p.name == "produto.py":
                continue
            arvore = ast.parse(p.read_text(encoding="utf-8"))
            docstrings = {id(n.body[0].value) for n in ast.walk(arvore)
                          if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
                          and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
            for n in ast.walk(arvore):
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings \
                        and produto.NOME in n.value:
                    achados.append(p.name)
        self.assertEqual(achados, [])

    def test_o_painel_nao_escreve_o_nome(self):
        for p in PAINEL.iterdir():
            if p.suffix in (".html", ".js", ".css", ".svg"):
                self.assertNotIn(produto.NOME, re.sub(r"/\*.*?\*/|//.*", "", p.read_text(encoding="utf-8"), flags=re.S), p.name)
        self.assertIn("{{NOME}}", HTML)

    def test_o_servidor_troca_o_nome_no_html(self):
        import tempfile
        from testes.fixtures import GeoDeMentira, MotorDeMentira
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as pasta:
            srv = servidor.Servidor(porta=0, pasta_dados=Path(pasta) / "dados", motor=MotorDeMentira(), geo=GeoDeMentira(), token="t")
            try:
                corpo = srv.servir_arquivo("/").corpo.decode("utf-8")
            finally:
                srv.server_close()
        self.assertIn(f"<title>{produto.NOME}</title>", corpo)
        self.assertIn(f"<b>{produto.NOME}</b>", corpo)
        self.assertNotIn("{{NOME}}", corpo)

    def test_sem_selo_nem_sigla_no_cabecalho_nem_no_favicon(self):
        self.assertNotIn('class="mark"', HTML)
        self.assertNotRegex(HTML, r">LK<")
        svg = (PAINEL / "favicon.svg").read_text(encoding="utf-8")
        self.assertNotIn("<text", svg)
        self.assertNotIn("LK", svg)


class TestBuscadorNaTela(unittest.TestCase):
    def test_a_palavra_motor_nao_aparece_em_texto_de_tela(self):
        ignorar = re.compile(r"[_/#.]|^motor$|motor-texto|ligar-motor|^motor:")
        achados = []
        for p in list(PAINEL.glob("*.js")) + [PAINEL / "index.html"]:
            texto = re.sub(r"/\*.*?\*/|(?<![:'\"\w])//[^\n]*", "", p.read_text(encoding="utf-8"), flags=re.S)
            for lit in re.findall(r"'([^'\n]*)'|`([^`\n]*)`|>([^<>\n]*)<", texto):
                for parte in lit:
                    if re.search(r"\bmotor\b", parte, re.I) and not ignorar.search(parte):
                        achados.append((p.name, parte[:70]))
        self.assertEqual(achados, [])

    def test_textos_do_servidor_que_aparecem_na_tela_dizem_buscador(self):
        from kit import diagnostico, ligar_motor
        textos = []
        for d in diagnostico.DIAGNOSTICOS.values():
            if d:
                textos += [d["titulo"], d["texto"]]
        textos += list(ligar_motor.MENSAGENS.values())
        for t in textos:
            self.assertNotRegex(t.replace("log-motor.txt", ""), r"\bmotor\b", t)  # o nome do arquivo é real


if __name__ == "__main__":
    unittest.main()
