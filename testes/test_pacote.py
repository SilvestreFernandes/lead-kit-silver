"""O .zip do pacote: o que entra, o que nunca entra, e que o arquivo é sempre o mesmo para a mesma entrada."""
import hashlib
import importlib.util
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def carregar_script():
    spec = importlib.util.spec_from_file_location("montar_pacote", RAIZ / "construcao" / "montar_pacote.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


montar_pacote = carregar_script()


def mini_repo(pasta, extras=()):
    """Um repositório de mentira só com o mínimo indispensável."""
    for nome in montar_pacote.INDISPENSAVEIS:
        arquivo = pasta / nome
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(f"conteudo de {nome}\n", encoding="utf-8")
    for nome, texto in extras:
        arquivo = pasta / nome
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(texto, encoding="utf-8")
    return pasta


class TestPacoteDeVerdade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.destino, cls.erros, cls.avisos = montar_pacote.montar(cls.tmp.name)
        cls.nomes = zipfile.ZipFile(cls.destino).namelist()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_monta_sem_erro_e_o_zip_esta_inteiro(self):
        self.assertEqual(self.erros, [])
        self.assertIsNone(zipfile.ZipFile(self.destino).testzip())

    def test_tem_o_que_o_comprador_precisa(self):
        for nome in ("LICENSE", "CREDITS.md", "docker-compose.yml", "kit/servidor.py", "kit/painel/index.html",
                     "kit/painel/fontes/LICENCA-IBM-Plex.txt", "entrevista/esquema.json", "entrevista/perfil.exemplo.json"):
            self.assertIn(nome, self.nomes)

    def test_nunca_leva_dados_planejamento_testes_nem_ferramentas_de_desenvolvimento(self):
        for nome in self.nomes:
            self.assertFalse(montar_pacote.proibido(nome), nome)
            for pedaco in ("dados/", "testes/", "docs/planejamento", "prints/", ".claude/agents", "impeccable", "__pycache__",
                           "PRODUCT.md", "construcao/", "dist/"):
                self.assertNotIn(pedaco, nome)
            self.assertFalse(nome.endswith((".csv", ".db", ".pyc", ".env")), nome)

    def test_o_claude_md_de_desenvolvimento_nao_entra(self):
        raiz = (RAIZ / "CLAUDE.md").read_bytes()
        if "CLAUDE.md" in self.nomes:
            self.assertNotEqual(zipfile.ZipFile(self.destino).read("CLAUDE.md"), raiz)

    def test_o_mesmo_pacote_sai_identico_duas_vezes(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as outra:
            destino2, erros2, _ = montar_pacote.montar(outra)
            self.assertEqual(erros2, [])
            self.assertEqual(hashlib.sha256(destino2.read_bytes()).hexdigest(), hashlib.sha256(self.destino.read_bytes()).hexdigest())

    def test_entradas_em_ordem_e_com_data_fixa(self):
        self.assertEqual(self.nomes, sorted(self.nomes))
        for info in zipfile.ZipFile(self.destino).infolist():
            self.assertEqual(info.date_time, montar_pacote.DATA_FIXA)

    def test_o_nome_do_arquivo_vem_do_nome_do_produto_e_da_versao(self):
        from kit import produto, servidor
        self.assertTrue(self.destino.name.endswith(f"-{servidor.VERSAO}.zip"))
        self.assertTrue(self.destino.name.startswith(produto.NOME.lower().replace(" ", "-")))

    def test_avisa_do_que_ainda_falta_das_instrucoes_para_a_ia(self):
        faltando = {a.removeprefix("ainda falta: ") for a in self.avisos}
        for peca in montar_pacote.PECAS_DAS_INSTRUCOES:
            self.assertEqual(peca in faltando, peca not in self.nomes, peca)


class TestRegrasDoScript(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name) / "repo"
        self.raiz.mkdir()

    def test_o_conteudo_de_pacote_vai_para_a_raiz_do_zip(self):
        mini_repo(self.raiz, [("pacote/CLAUDE.md", "do comprador"), ("pacote/.claude/skills/lead-kit/SKILL.md", "skill"),
                              ("pacote/iniciar.bat", "@echo off"), ("CLAUDE.md", "de desenvolvimento")])
        destino, erros, _ = montar_pacote.montar(Path(self._tmp.name) / "saida", raiz=self.raiz)
        self.assertEqual(erros, [])
        z = zipfile.ZipFile(destino)
        self.assertEqual(z.read("CLAUDE.md"), b"do comprador")  # nunca o de desenvolvimento
        self.assertIn(".claude/skills/lead-kit/SKILL.md", z.namelist())
        self.assertIn("iniciar.bat", z.namelist())
        self.assertFalse([n for n in z.namelist() if n.startswith("pacote/")])

    def test_falta_de_peca_indispensavel_impede_o_zip(self):
        mini_repo(self.raiz)
        (self.raiz / "LICENSE").unlink()
        destino, erros, _ = montar_pacote.montar(Path(self._tmp.name) / "saida", raiz=self.raiz)
        self.assertIsNone(destino)
        self.assertIn("falta no pacote: LICENSE", erros)

    def test_arquivo_proibido_no_caminho_para_tudo(self):
        mini_repo(self.raiz, [("kit/perfil.json", "{}"), ("kit/leads.db", "x"), ("entrevista/lista.csv", "a,b")])
        destino, erros, _ = montar_pacote.montar(Path(self._tmp.name) / "saida", raiz=self.raiz)
        self.assertIsNone(destino)
        for nome in ("kit/perfil.json", "kit/leads.db", "entrevista/lista.csv"):
            self.assertIn(f"arquivo proibido no pacote: {nome}", erros)
        self.assertFalse((Path(self._tmp.name) / "saida").exists() and list((Path(self._tmp.name) / "saida").glob("*.zip")))

    def test_dados_e_pastas_de_ferramenta_dentro_do_pacote_tambem_param(self):
        mini_repo(self.raiz, [("pacote/dados/perfil.json", "{}"), ("pacote/.claude/skills/impeccable/SKILL.md", "x"),
                              ("pacote/.claude/agents/a.md", "x"), ("pacote/instalacao.json", "{}")])
        _, erros, _ = montar_pacote.montar(Path(self._tmp.name) / "saida", raiz=self.raiz)
        for nome in ("dados/perfil.json", ".claude/skills/impeccable/SKILL.md", ".claude/agents/a.md", "instalacao.json"):
            self.assertIn(f"arquivo proibido no pacote: {nome}", erros)

    def test_modo_completo_falha_enquanto_faltar_peca_das_instrucoes(self):
        mini_repo(self.raiz)
        destino, erros, avisos = montar_pacote.montar(Path(self._tmp.name) / "saida", completo=True, raiz=self.raiz)
        self.assertIsNone(destino)
        self.assertIn("ainda falta: INSTALAR.md", erros)
        self.assertEqual(avisos, [])

    def test_pycache_nunca_entra(self):
        mini_repo(self.raiz, [("kit/__pycache__/x.cpython-313.pyc", "x"), ("kit/outro.pyc", "x")])
        destino, erros, _ = montar_pacote.montar(Path(self._tmp.name) / "saida", raiz=self.raiz)
        self.assertEqual(erros, [])
        self.assertFalse([n for n in zipfile.ZipFile(destino).namelist() if "pycache" in n or n.endswith(".pyc")])


class TestGitignore(unittest.TestCase):
    def ignorado(self, caminho):
        r = subprocess.run(["git", "check-ignore", "-q", caminho], cwd=RAIZ, capture_output=True)
        return r.returncode == 0

    @unittest.skipUnless(shutil.which("git"), "git não está instalado")
    def test_ferramentas_de_desenvolvimento_ficam_de_fora_e_a_skill_do_produto_fica_dentro(self):
        for caminho in (".claude/skills/impeccable/SKILL.md", ".claude/agents/impeccable-documenter.md", ".impeccable/config.json",
                        "dados/perfil.json", "dist/pacote.zip", "x.csv"):
            self.assertTrue(self.ignorado(caminho), caminho)
        for caminho in ("pacote/.claude/skills/lead-kit/SKILL.md", "pacote/CLAUDE.md", "pacote/AGENTS.md", "pacote/iniciar.bat",
                        "construcao/montar_pacote.py"):
            self.assertFalse(self.ignorado(caminho), caminho)


if __name__ == "__main__":
    unittest.main()
