import unittest

from kit import limpeza, pontuacao
from testes.fixtures import csv_texto, linha, perfil_ficticio


def lead(**campos):
    return limpeza.limpar_linha(linha(1, **campos))


class TestPontuacao(unittest.TestCase):
    def test_cortes_padrao_sao_70_e_40_por_cento_arredondados_para_cima(self):
        perfil = perfil_ficticio()  # soma 3+2+2+1+2 = 10
        self.assertEqual(pontuacao.cortes(perfil), (7, 4))
        perfil["pontuacao"]["regras"] = [{"id": "sem_site", "peso": 3}, {"id": "celular", "peso": 2}]
        self.assertEqual(pontuacao.cortes(perfil), (4, 2))  # 3,5 -> 4 e 2,0 -> 2

    def test_perfil_sobrescreve_os_cortes(self):
        perfil = perfil_ficticio()
        perfil["pontuacao"]["corte_a"], perfil["pontuacao"]["corte_b"] = 9, 1
        self.assertEqual(pontuacao.cortes(perfil), (9, 1))

    def test_lead_sem_site_celular_e_nota_alta_vira_a(self):
        r = pontuacao.pontuar(lead(website="", phone="(61) 99999-0001", review_rating="4.7",
                                   review_count="80"), perfil_ficticio())
        self.assertEqual(r["nota"], 3 + 2 + 2 + 1)
        self.assertEqual(r["letra"], "A")
        self.assertIn("sem site (+3)", r["motivos"])
        self.assertEqual(r["motivo_principal"], "sem site")

    def test_lead_comum_vira_c(self):
        r = pontuacao.pontuar(lead(), perfil_ficticio())
        self.assertEqual((r["nota"], r["letra"]), (0, "C"))
        self.assertEqual(r["motivos"], [])
        self.assertEqual(r["motivo_principal"], "")

    def test_nota_4_vale_so_um_ponto(self):
        r = pontuacao.pontuar(lead(review_rating="4.0"), perfil_ficticio())
        self.assertEqual(r["motivos"], ["nota alta (+1)"])

    def test_nota_ausente_nao_pontua_nem_quebra(self):
        r = pontuacao.pontuar(lead(review_rating="", review_count=""), perfil_ficticio())
        self.assertEqual(r["nota"], 0)

    def test_nota_baixa_e_poucas_avaliacoes(self):
        perfil = perfil_ficticio()
        perfil["pontuacao"]["regras"] = [{"id": "nota_baixa", "peso": 2}, {"id": "poucas_avaliacoes", "peso": 1}]
        r = pontuacao.pontuar(lead(review_rating="3.5", review_count="5"), perfil)
        self.assertEqual(r["nota"], 3)

    def test_so_instagram(self):
        r = pontuacao.pontuar(lead(website="https://instagram.com/x"), perfil_ficticio())
        self.assertEqual(r["motivos"], ["site é só uma rede social (+2)"])

    def test_delivery_e_reserva(self):
        perfil = perfil_ficticio()
        perfil["pontuacao"]["regras"] = [{"id": "delivery", "peso": 1}, {"id": "reserva", "peso": 1}]
        r = pontuacao.pontuar(lead(order_online='[{"a":1}]', reservations='[{"b":2}]'), perfil)
        self.assertEqual(r["nota"], 2)

    def test_sem_email_so_vale_com_email_ligado(self):
        perfil = perfil_ficticio()
        perfil["pontuacao"]["regras"] = [{"id": "sem_email", "peso": 1}]
        self.assertEqual(pontuacao.pontuar(lead(), perfil, email_ligado=False)["nota"], 0)
        self.assertEqual(pontuacao.pontuar(lead(), perfil, email_ligado=True)["nota"], 1)
        self.assertEqual(pontuacao.pontuar(lead(emails="a@x.invalid"), perfil, email_ligado=True)["nota"], 0)

    def test_regra_desligada_nao_conta(self):
        perfil = perfil_ficticio()
        perfil["pontuacao"]["regras"] = [{"id": "celular", "peso": 2}]
        r = pontuacao.pontuar(lead(website=""), perfil)
        self.assertEqual(r["nota"], 0)

    def test_mesma_lista_mesma_nota(self):
        leads, _ = limpeza.ler_csv(csv_texto())
        a = [(r["lead"]["nome"], r["nota"]) for r in pontuacao.avaliar_todos(leads, perfil_ficticio())]
        b = [(r["lead"]["nome"], r["nota"]) for r in pontuacao.avaliar_todos(list(reversed(leads)), perfil_ficticio())]
        self.assertEqual(a, b)


class TestExclusoes(unittest.TestCase):
    def setUp(self):
        self.leads, _ = limpeza.ler_csv(csv_texto())
        self.por_nome = {}
        self.perfil = perfil_ficticio()

    def avaliar(self, perfil=None):
        return {r["lead"]["nome"]: r for r in pontuacao.avaliar_todos(self.leads, perfil or self.perfil)}

    def test_sem_telefone(self):
        self.assertEqual(self.avaliar()["Sem Telefone"]["excluido_por"], "sem telefone")

    def test_rede_com_tres_enderecos(self):
        r = self.avaliar()
        for nome in ("Café Rede", "Café Rede - Filial Norte", "CAFÉ REDE"):
            self.assertIn("possível rede", r[nome]["excluido_por"])
            self.assertIn("3 endereços", r[nome]["excluido_por"])

    def test_rede_com_dois_enderecos_nao_exclui(self):
        self.leads = [l for l in self.leads if l["place_id"] != "pid6c"]
        self.assertIsNone(self.avaliar()["Café Rede"]["excluido_por"])

    def test_rede_nao_e_gravada_no_lead(self):
        self.avaliar()
        for l in self.leads:
            self.assertNotIn("excluido_por", l)
            self.assertNotIn("rede", l)

    def test_rede_so_vale_se_a_exclusao_estiver_ativa(self):
        self.perfil["exclusoes"] = ["sem_telefone"]
        self.assertIsNone(self.avaliar()["Café Rede"]["excluido_por"])

    def test_nota_muito_baixa(self):
        self.perfil["exclusoes"] = ["nota_muito_baixa"]
        r = self.avaliar()
        self.assertEqual(r["Nota Péssima"]["excluido_por"], "nota muito baixa")
        self.assertIsNone(r["Só Rede Social"]["excluido_por"])  # 3,5 passa

    def test_concorrente_por_nome_e_por_site(self):
        self.perfil["exclusoes"] = ["concorrente"]
        self.perfil["exclusoes_concorrentes"] = ["concorrente fictício"]
        self.assertEqual(self.avaliar()["Concorrente Fictício"]["excluido_por"], "concorrente da sua lista")
        self.perfil["exclusoes_concorrentes"] = ["concorrente.invalid"]
        self.assertEqual(self.avaliar()["Concorrente Fictício"]["excluido_por"], "concorrente da sua lista")

    def test_concorrente_sem_lista_nao_faz_nada(self):
        self.perfil["exclusoes"] = ["concorrente"]
        self.assertTrue(all(r["excluido_por"] is None for r in self.avaliar().values()))

    def test_categoria_evitada(self):
        self.perfil["exclusoes"] = ["categoria"]
        self.perfil["exclusoes_categorias"] = ["restaurante"]
        self.assertEqual(self.avaliar()["Reserva"]["excluido_por"], "categoria que você quer evitar")

    def test_excluidos_vao_para_o_fim_da_lista(self):
        ordem = pontuacao.avaliar_todos(self.leads, self.perfil)
        achou_excluido = False
        for r in ordem:
            if r["excluido_por"]:
                achou_excluido = True
            else:
                self.assertFalse(achou_excluido, "lead normal depois de excluido")


if __name__ == "__main__":
    unittest.main()
