import unittest

from kit import limpeza
from testes.fixtures import COLUNAS, csv_texto, leads_ficticios, linha


class TestLimpeza(unittest.TestCase):
    def test_le_e_tira_duplicados(self):
        leads, ignoradas = limpeza.ler_csv(csv_texto())
        self.assertEqual(len(leads), 11)  # 12 linhas, 1 duplicada
        self.assertEqual(ignoradas, 0)

    def test_coluna_faltando_para_com_mensagem_clara(self):
        colunas = [c for c in COLUNAS if c != "website"]
        with self.assertRaises(limpeza.ErroCSV) as e:
            limpeza.ler_csv(csv_texto(colunas=colunas))
        self.assertIn("website", str(e.exception))

    def test_linha_sem_nome_e_ignorada(self):
        texto = csv_texto([linha(1), linha(2, title="")])
        leads, ignoradas = limpeza.ler_csv(texto)
        self.assertEqual((len(leads), ignoradas), (1, 1))

    def test_bom_no_inicio_nao_atrapalha(self):
        leads, _ = limpeza.ler_csv("﻿" + csv_texto())
        self.assertEqual(len(leads), 11)

    def test_telefone_celular_e_fixo(self):
        self.assertTrue(limpeza.eh_celular(limpeza.telefone_digitos("(61) 99999-0001")))
        self.assertTrue(limpeza.eh_celular(limpeza.telefone_digitos("+55 61 98888-0003")))
        self.assertFalse(limpeza.eh_celular(limpeza.telefone_digitos("(61) 3333-0000")))
        self.assertFalse(limpeza.eh_celular(""))

    def test_numeros_com_virgula_e_milhar(self):
        self.assertEqual(limpeza.numero("4,5"), 4.5)
        self.assertEqual(limpeza.numero("4.5"), 4.5)
        self.assertIsNone(limpeza.numero(""))
        self.assertEqual(limpeza.inteiro("1.234"), 1234)
        self.assertEqual(limpeza.inteiro("80"), 80)

    def test_json_vazio_e_preenchido(self):
        for vazio in ("", "[]", "{}", "null", None):
            self.assertFalse(limpeza.json_preenchido(vazio))
        self.assertTrue(limpeza.json_preenchido('[{"a":1}]'))

    def test_rede_social(self):
        self.assertTrue(limpeza.eh_rede_social("https://www.instagram.com/x"))
        self.assertTrue(limpeza.eh_rede_social("facebook.com/x"))
        self.assertFalse(limpeza.eh_rede_social("https://meusite.invalid"))
        self.assertFalse(limpeza.eh_rede_social("https://naoinstagram.com.invalid"))
        self.assertFalse(limpeza.eh_rede_social(""))

    def test_normalizar_nome_tira_filial_acento_e_caixa(self):
        a = limpeza.normalizar_nome("Café Rede - Filial Norte")
        b = limpeza.normalizar_nome("CAFÉ  REDE")
        self.assertEqual(a, b)
        self.assertEqual(a, "cafe rede")

    def test_chave_usa_place_id_depois_cid_depois_nome(self):
        l = limpeza.limpar_linha(linha(1, place_id="", cid=""))
        self.assertTrue(l["chave"].startswith("n:"))
        l = limpeza.limpar_linha(linha(1, place_id=""))
        self.assertEqual(l["chave"], "c:cid1")
        l = limpeza.limpar_linha(linha(1))
        self.assertEqual(l["chave"], "p:pid1")

    def test_campos_do_lead(self):
        leads, _ = limpeza.ler_csv(csv_texto())
        por_nome = {l["nome"]: l for l in leads}
        completa = por_nome["Padaria Completa"]
        self.assertTrue(completa["delivery"])
        self.assertFalse(completa["reserva"])
        self.assertTrue(completa["celular"])
        self.assertEqual(completa["avaliacoes"], 200)
        self.assertEqual(completa["nota_maps"], 4.5)
        self.assertTrue(por_nome["Reserva"]["reserva"])

    def test_emails_viram_lista(self):
        l = limpeza.limpar_linha(linha(1, emails="a@x.invalid; b@x.invalid"))
        self.assertEqual(l["emails"], ["a@x.invalid", "b@x.invalid"])


if __name__ == "__main__":
    unittest.main()
