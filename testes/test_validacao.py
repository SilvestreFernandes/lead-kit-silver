import tempfile
import unittest
from pathlib import Path

from kit import validar_perfil as v
from testes.fixtures import perfil_ficticio


class TestValidacao(unittest.TestCase):
    def test_perfil_bom_passa(self):
        _, erros, avisos = v.validar(perfil_ficticio())
        self.assertEqual(erros, [])
        self.assertEqual(avisos, [])

    def test_exemplo_do_repositorio_passa(self):
        _, erros, _ = v.carregar(v.RAIZ / "entrevista" / "perfil.exemplo.json")
        self.assertEqual(erros, [])

    def test_arquivo_inexistente(self):
        _, erros, _ = v.carregar("nao-existe.json")
        self.assertTrue(erros)

    def test_json_quebrado(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "perfil.json"
            p.write_text("{quebrado", encoding="utf-8")
            _, erros, _ = v.carregar(p)
        self.assertIn("JSON válido", erros[0])

    def test_versao_desconhecida(self):
        p = perfil_ficticio()
        p["versao"] = 99
        _, erros, _ = v.validar(p)
        self.assertTrue(any("Versão" in e for e in erros))

    def test_campo_obrigatorio_vazio(self):
        p = perfil_ficticio()
        p["negocio"]["oferta"] = ""
        _, erros, _ = v.validar(p)
        self.assertTrue(any("negocio.oferta" in e for e in erros))

    def test_regra_inexistente_e_removida(self):
        p = perfil_ficticio()
        p["pontuacao"]["regras"].append({"id": "inventada", "peso": 1})
        novo, erros, avisos = v.validar(p)
        self.assertEqual(erros, [])
        self.assertTrue(any("inventada" in a for a in avisos))
        self.assertNotIn("inventada", [r["id"] for r in novo["pontuacao"]["regras"]])

    def test_peso_fora_do_limite_e_ajustado(self):
        p = perfil_ficticio()
        p["pontuacao"]["regras"][0]["peso"] = 9
        novo, _, avisos = v.validar(p)
        self.assertEqual(novo["pontuacao"]["regras"][0]["peso"], 5)
        self.assertTrue(avisos)

    def test_peso_nao_inteiro_vira_padrao(self):
        p = perfil_ficticio()
        p["pontuacao"]["regras"][0]["peso"] = "alto"
        novo, _, avisos = v.validar(p)
        self.assertEqual(novo["pontuacao"]["regras"][0]["peso"], 3)
        self.assertTrue(avisos)

    def test_cortes_invertidos_sao_descartados(self):
        p = perfil_ficticio()
        p["pontuacao"]["corte_a"] = 2
        p["pontuacao"]["corte_b"] = 5
        novo, _, avisos = v.validar(p)
        self.assertNotIn("corte_a", novo["pontuacao"])
        self.assertTrue(avisos)

    def test_cortes_validos_sao_mantidos(self):
        p = perfil_ficticio()
        p["pontuacao"]["corte_a"] = 8
        p["pontuacao"]["corte_b"] = 3
        novo, _, avisos = v.validar(p)
        self.assertEqual(novo["pontuacao"]["corte_a"], 8)
        self.assertEqual(avisos, [])

    def test_marcador_invalido(self):
        p = perfil_ficticio()
        p["mensagens"]["whatsapp"] = "Oi {apelido}. Se não fizer sentido, é só avisar."
        _, erros, _ = v.validar(p)
        self.assertTrue(any("apelido" in e for e in erros))

    def test_mensagem_sem_saida(self):
        p = perfil_ficticio()
        p["mensagens"]["whatsapp"] = "Oi {nome}, compre agora!"
        _, erros, _ = v.validar(p)
        self.assertTrue(any("saída" in e for e in erros))

    def test_dado_sensivel_e_removido(self):
        p = perfil_ficticio()
        p["negocio"]["cpf"] = "000.000.000-00"
        novo, _, avisos = v.validar(p)
        self.assertNotIn("cpf", novo["negocio"])
        self.assertTrue(any("cpf" in a for a in avisos))

    def test_porte_e_tom_invalidos(self):
        p = perfil_ficticio()
        p["cliente"]["porte"] = "gigante"
        p["abordagem"]["tom"] = "bravo"
        _, erros, _ = v.validar(p)
        self.assertEqual(len(erros), 2)

    def test_nao_altera_o_original(self):
        p = perfil_ficticio()
        p["pontuacao"]["regras"][0]["peso"] = 9
        v.validar(p)
        self.assertEqual(p["pontuacao"]["regras"][0]["peso"], 9)


if __name__ == "__main__":
    unittest.main()
