import tempfile
import unittest
from pathlib import Path

from kit import testar_api
from testes.test_servidor import Base


class TestTestarApi(Base):
    """Roda o script de verdade contra um servidor de teste (motor e mapas simulados)."""
    com_leads = False

    def rodar(self, *argv):
        linhas = []
        codigo = testar_api.main(["--porta", str(self.porta), *argv], saida=linhas.append)
        return codigo, "\n".join(linhas)

    def test_estado(self):
        codigo, texto = self.rodar("estado")
        self.assertEqual(codigo, 0)
        self.assertIn("Motor de busca: ligado", texto)
        self.assertIn("Perfil: válido", texto)

    def test_buscar_do_comeco_ao_fim_e_depois_consultar(self):
        codigo, texto = self.rodar("buscar", "--categoria", "padaria", "--cidade", "Cidade Teste",
                                   "--uf", "DF")
        self.assertEqual(codigo, 0, texto)
        self.assertIn("terminou: 11 negócios", texto)
        self.assertIn("Pão Sem Site", texto)
        self.assertIn("sem site (+3)", texto)
        _, leads = self.rodar("leads", "--letra", "A")
        self.assertIn("Pão Sem Site", leads)
        lid = self.lead_id("Pão Sem Site")
        _, detalhe = self.rodar("lead", str(lid))
        self.assertIn("Mensagem de whatsapp", detalhe)
        _, marcado = self.rodar("marcar", str(lid), "--status", "contatado", "--anotacao", "ligar terça")
        self.assertIn("contatado", marcado)
        _, re = self.rodar("reavaliar")
        self.assertIn("11 leads reavaliados", re)

    def test_exportar_grava_o_arquivo(self):
        self.rodar("buscar", "--categoria", "padaria", "--cidade", "Cidade Teste", "--uf", "DF")
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            arquivo = Path(d) / "leads.csv"
            codigo, _ = self.rodar("exportar", "--arquivo", str(arquivo))
            self.assertEqual(codigo, 0)
            self.assertTrue(arquivo.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_erro_da_api_vira_mensagem(self):
        codigo, texto = self.rodar("buscar", "--categoria", "padaria", "--cidade", "X", "--uf", "ZZ")
        self.assertEqual(codigo, 1)
        self.assertIn("400", texto)
        self.assertIn("estado", texto)

    def test_servidor_desligado(self):
        linhas = []
        codigo = testar_api.main(["--porta", "9", "estado"], saida=linhas.append)
        self.assertEqual(codigo, 1)
        self.assertIn("python kit/servidor.py", linhas[0])


if __name__ == "__main__":
    unittest.main()
