"""A planilha de amostra do produto: limpa, realista e sem dados de teste de seguranca."""
import re
import unittest

from testes.gerar_exemplo_planilha import avaliar_exemplo, leads_de_exemplo

PROIBIDAS = ("fictício", "ficticio", "rede fict", "sem telefone", "<", ">", "javascript", "alert", "script",
             "onerror", "=hyperlink", "teste de seguran")


class TestExemploDaPlanilha(unittest.TestCase):
    def setUp(self):
        self.avaliados, self.perfil = avaliar_exemplo()

    def test_de_oito_a_dez_negocios_de_uma_cidade_so(self):
        self.assertTrue(8 <= len(self.avaliados) <= 10)
        self.assertEqual({r["lead"]["cidade"] for r in self.avaliados}, {"Brasília"})

    def test_notas_variadas_e_nenhum_excluido(self):
        self.assertEqual({r["letra"] for r in self.avaliados}, {"A", "B", "C"})
        self.assertEqual([r["lead"]["nome"] for r in self.avaliados if r["excluido_por"]], [])

    def test_nenhum_texto_de_teste_de_seguranca_nem_nome_de_dado_falso_obvio(self):
        for l in leads_de_exemplo():
            texto = " ".join(str(v) for v in l.values()).lower()
            for proibida in PROIBIDAS:
                self.assertNotIn(proibida, texto, (l["title"], proibida))

    def test_endereco_e_telefone_com_formato_brasileiro(self):
        for l in leads_de_exemplo():
            self.assertTrue(l["address"].endswith("Brasília - DF"), l["title"])
            self.assertRegex(l["phone"], r"^\(61\) 9?\d{4}-\d{4}$", l["title"])

    def test_nenhum_nome_repetido(self):
        nomes = [l["title"] for l in leads_de_exemplo()]
        self.assertEqual(len(nomes), len(set(nomes)))


if __name__ == "__main__":
    unittest.main()
