"""Roda os testes de JavaScript do painel com o Node, se ele estiver instalado.

O Node e so ferramenta de desenvolvimento: o kit nao depende dele, e quem nao tem Node pula este teste.
"""
import shutil
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")


@unittest.skipUnless(NODE, "Node não está instalado: testes de JavaScript pulados")
class TestJavaScriptDoPainel(unittest.TestCase):
    def test_util_api_e_tela_de_leads(self):
        r = subprocess.run([NODE, "--test", "testes/js/util.test.mjs", "testes/js/leads.test.mjs"], cwd=RAIZ,
                           capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
