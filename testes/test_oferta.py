"""Tela Minha oferta: o que o painel calcula sozinho precisa bater com o que o kit calcula."""
import unittest
from pathlib import Path

from kit import pontuacao, servidor, validar_perfil
from testes.fixtures import perfil_ficticio

PAINEL = Path(servidor.__file__).resolve().parent / "painel"


def cortes_do_kit(soma):
    perfil = perfil_ficticio()
    perfil["pontuacao"] = {"regras": [{"id": "sem_site", "peso": soma}] if soma else []}
    return pontuacao.cortes(perfil)


class TestOferta(unittest.TestCase):
    def test_cortes_automaticos_do_painel_batem_com_os_do_kit(self):
        # Os mesmos valores esperados estao em testes/js/oferta.test.mjs ("cortes automaticos").
        for soma, esperado in ((10, (7, 4)), (7, (5, 3)), (1, (1, 1)), (0, (0, 0))):
            self.assertEqual(tuple(cortes_do_kit(soma)), esperado, soma)

    def test_toda_regra_e_exclusao_tem_descricao_para_o_formulario(self):
        for rid, cfg in validar_perfil.REGRAS["regras"].items():
            self.assertTrue(cfg.get("descricao"), rid)
        for eid, cfg in validar_perfil.REGRAS["exclusoes"].items():
            self.assertTrue(cfg.get("descricao"), eid)

    def test_os_pesos_padrao_nao_foram_mudados(self):
        pesos = {rid: cfg["peso"] for rid, cfg in validar_perfil.REGRAS["regras"].items()}
        self.assertEqual(pesos, {"sem_site": 3, "so_instagram": 2, "nota_alta": 2, "nota_baixa": 2,
                                 "muitas_avaliacoes": 1, "poucas_avaliacoes": 1, "celular": 2, "delivery": 1,
                                 "reserva": 1, "sem_email": 1})
        self.assertEqual(validar_perfil.REGRAS["cortes"], {"a": 0.7, "b": 0.4})

    def test_a_tela_so_edita_campos_das_12_perguntas(self):
        tela = (PAINEL / "tela-oferta.js").read_text(encoding="utf-8")
        for campo in ("negocio.oferta", "negocio.nome", "negocio.empresa", "cliente.tipos", "cliente.porte",
                      "cliente.regioes", "negocio.atendimento", "cliente.exemplo", "abordagem.canais",
                      "abordagem.tom", "abordagem.oferta_entrada", "abordagem.volume_semana",
                      "conformidade.restricoes", "exclusoes", "pontuacao.regras"):
            objeto, _, chave = campo.partition(".")
            self.assertIn(chave or objeto, tela, campo)

    def test_texto_da_tela_nao_usa_travessao(self):
        for nome in ("tela-oferta.js", "oferta-util.js"):
            texto = (PAINEL / nome).read_text(encoding="utf-8")
            self.assertNotIn("—", texto, nome)
            self.assertNotIn("–", texto, nome)


if __name__ == "__main__":
    unittest.main()
