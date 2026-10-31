"""Regra ausente do perfil e regra com peso 0 precisam dar exatamente a mesma nota, letra, motivos e cortes.

A tela Minha oferta mostra as duas coisas como "Ignorar".
"""
import copy
import unittest

from kit import banco, limpeza, pontuacao, validar_perfil
from testes.fixtures import csv_texto, leads_em_massa, perfil_ficticio


def leads():
    conn = banco.abrir()
    bid = banco.criar_busca(conn, "padaria", "Cidade Teste", "DF", "rapida", {}, True)
    banco.salvar_leads(conn, bid, limpeza.ler_csv(csv_texto(leads_em_massa(300)))[0], "Cidade Teste", "DF", True)
    try:
        return banco.todos_os_leads(conn)
    finally:
        conn.close()


def perfil_com(regras, **pontuacao_extra):
    p = perfil_ficticio()
    p["pontuacao"] = {"regras": regras, **pontuacao_extra}
    return p


def resultado(perfil, todos):
    return [(r["nota"], r["letra"], tuple(r["motivos"]), r["motivo_principal_id"], r["excluido_por"])
            for r in pontuacao.avaliar_todos(copy.deepcopy(todos), perfil)], pontuacao.cortes(perfil)


class TestAusenteIgualPesoZero(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.todos = leads()

    def test_cada_regra_do_kit_ausente_ou_com_peso_zero_da_o_mesmo_resultado(self):
        base = [{"id": "sem_site", "peso": 3}, {"id": "celular", "peso": 2}, {"id": "nota_alta", "peso": 2}]
        for rid, cfg in validar_perfil.REGRAS["regras"].items():
            if any(r["id"] == rid for r in base):
                continue
            ausente = perfil_com(copy.deepcopy(base))
            zero = perfil_com(copy.deepcopy(base) + [{"id": rid, "peso": 0}])
            self.assertEqual(resultado(ausente, self.todos), resultado(zero, self.todos), rid)

    def test_regra_que_ja_marca_ponto_vira_ignorar_sem_diferenca(self):
        for rid in ("sem_site", "celular", "nota_alta", "muitas_avaliacoes", "so_instagram"):
            completo = [{"id": r, "peso": 2} for r in ("sem_site", "celular", "nota_alta", "muitas_avaliacoes", "so_instagram")]
            sem = [r for r in completo if r["id"] != rid]
            com_zero = [dict(r, peso=0) if r["id"] == rid else dict(r) for r in completo]
            self.assertEqual(resultado(perfil_com(sem), self.todos), resultado(perfil_com(com_zero), self.todos), rid)

    def test_com_cortes_manuais_tambem_sao_iguais(self):
        base = [{"id": "sem_site", "peso": 3}, {"id": "celular", "peso": 2}]
        a = perfil_com(copy.deepcopy(base), corte_a=4, corte_b=2)
        b = perfil_com(copy.deepcopy(base) + [{"id": "delivery", "peso": 0}], corte_a=4, corte_b=2)
        self.assertEqual(resultado(a, self.todos), resultado(b, self.todos))

    def test_soma_dos_pesos_e_cortes_automaticos_nao_mudam(self):
        a = perfil_com([{"id": "sem_site", "peso": 3}, {"id": "celular", "peso": 2}])
        b = perfil_com([{"id": "sem_site", "peso": 3}, {"id": "celular", "peso": 2}, {"id": "reserva", "peso": 0}])
        self.assertEqual(pontuacao.soma_dos_pesos(a), pontuacao.soma_dos_pesos(b))
        self.assertEqual(pontuacao.cortes(a), pontuacao.cortes(b))

    def test_o_validador_aceita_peso_zero(self):
        perfil, erros, avisos = validar_perfil.validar(perfil_com([{"id": "sem_site", "peso": 0}]))
        self.assertEqual(erros, [])
        self.assertEqual(perfil["pontuacao"]["regras"], [{"id": "sem_site", "peso": 0}])
        self.assertEqual(avisos, [])


if __name__ == "__main__":
    unittest.main()
