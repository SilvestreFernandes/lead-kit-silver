import unittest

from kit import limpeza, modelos, pontuacao
from testes.fixtures import linha, perfil_ficticio


def lead(**campos):
    l = limpeza.limpar_linha(linha(1, **campos))
    l["cidade"] = "Cidade Teste"
    return l


class TestModelos(unittest.TestCase):
    def test_troca_todos_os_marcadores(self):
        perfil = perfil_ficticio()
        texto = modelos.preencher("{nome}|{cidade}|{categoria}|{meu_nome}|{minha_empresa}|{motivo}",
                                  lead(website=""), perfil, "sem_site")
        self.assertEqual(texto, "Negócio Fictício 1|Cidade Teste|Padaria|Teste|Empresa Teste|"
                                "não achei um site no perfil do Google Maps")

    def test_marcador_desconhecido_fica_como_esta(self):
        self.assertEqual(modelos.preencher("Oi {apelido}", lead(), perfil_ficticio(), None), "Oi {apelido}")

    def test_frase_com_dado_do_lead_usa_virgula_decimal(self):
        self.assertEqual(modelos.frase_do_motivo(lead(review_rating="4.7"), "nota_alta"),
                         "a nota no Google Maps é 4,7")
        self.assertEqual(modelos.frase_do_motivo(lead(review_rating="5.0"), "nota_alta"),
                         "a nota no Google Maps é 5")
        self.assertEqual(modelos.frase_do_motivo(lead(review_count="80"), "muitas_avaliacoes"),
                         "o perfil tem 80 avaliações no Google Maps")

    def test_sem_motivo_usa_frase_neutra(self):
        self.assertEqual(modelos.frase_do_motivo(lead(), None),
                         "o perfil aparece no Google Maps em Cidade Teste")

    def test_toda_regra_tem_frase_sem_marcador_invalido(self):
        for rid, cfg in modelos.REGRAS["regras"].items():
            self.assertTrue(cfg.get("frase"), rid)
            for m in modelos.MARCADOR.findall(cfg["frase"]):
                self.assertIn(m, {"nota_maps", "avaliacoes", "cidade"}, rid)
            self.assertNotIn("—", cfg["frase"])

    def test_frase_segue_a_regra_que_mais_pesou(self):
        perfil = perfil_ficticio()
        l = lead(website="", review_rating="4.7", review_count="80", phone="(61) 99999-0001")
        r = pontuacao.pontuar(l, perfil)
        self.assertEqual(r["motivo_principal_id"], "sem_site")
        msg = modelos.mensagens_do_lead(l, perfil, r["motivo_principal_id"])["whatsapp"]["texto"]
        self.assertIn("não achei um site", msg)

    def test_modelo_do_perfil_vence_o_provisorio(self):
        perfil = perfil_ficticio()
        m = modelos.mensagens_do_lead(lead(), perfil, None)
        self.assertEqual(list(m), ["whatsapp"])
        self.assertFalse(m["whatsapp"]["padrao"])
        self.assertTrue(m["whatsapp"]["texto"].startswith("Oi, Negócio Fictício 1!"))

    def test_sem_modelo_no_perfil_usa_o_provisorio_marcado(self):
        perfil = perfil_ficticio()
        perfil["mensagens"] = {}
        perfil["abordagem"]["canais"] = ["whatsapp", "email", "ligacao"]
        m = modelos.mensagens_do_lead(lead(), perfil, "sem_site")
        self.assertEqual(set(m), {"whatsapp", "email"})  # ligacao nao tem modelo
        self.assertTrue(all(v["padrao"] for v in m.values()))
        self.assertIn("não escrevo mais", m["whatsapp"]["texto"])

    def test_modelos_provisorios_passam_no_validador(self):
        from kit import validar_perfil
        perfil = perfil_ficticio()
        perfil["mensagens"] = dict(modelos.MODELOS_PROVISORIOS)
        _, erros, _ = validar_perfil.validar(perfil)
        self.assertEqual(erros, [])


if __name__ == "__main__":
    unittest.main()
