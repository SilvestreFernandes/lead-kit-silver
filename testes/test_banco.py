import unittest

from kit import banco, limpeza
from testes.fixtures import csv_texto, linha


def leads():
    return limpeza.ler_csv(csv_texto())[0]


class TestBanco(unittest.TestCase):
    def setUp(self):
        self.conn = banco.abrir()
        self.addCleanup(self.conn.close)

    def nova_busca(self, **kw):
        return banco.criar_busca(self.conn, "padaria", "Cidade Teste", "DF", "rapida",
                                 {"depth": 1}, kw.get("email", False))

    def test_busca_criada_e_atualizada(self):
        b = self.nova_busca()
        banco.atualizar_busca(self.conn, b, status="ok", job_id="abc", total_leads=3)
        d = banco.obter_busca(self.conn, b)
        self.assertEqual((d["status"], d["job_id"], d["total_leads"]), ("ok", "abc", 3))

    def test_campo_de_busca_invalido(self):
        b = self.nova_busca()
        with self.assertRaises(ValueError):
            banco.atualizar_busca(self.conn, b, **{"status = 'x'; DROP TABLE leads; --": "ok"})
        with self.assertRaises(ValueError):
            banco.atualizar_busca(self.conn, b)

    def test_salva_e_le_leads(self):
        b = self.nova_busca()
        banco.salvar_leads(self.conn, b, leads(), "Cidade Teste", "DF", False)
        lidos = banco.leads_da_busca(self.conn, b)
        self.assertEqual(len(lidos), 11)
        completa = next(l for l in lidos if l["nome"] == "Padaria Completa")
        self.assertIs(completa["delivery"], True)
        self.assertIs(completa["celular"], True)
        self.assertEqual(completa["emails"], [])

    def test_mesmo_negocio_em_duas_buscas_vira_um_lead(self):
        b1, b2 = self.nova_busca(), self.nova_busca()
        banco.salvar_leads(self.conn, b1, leads(), "Cidade Teste", "DF", False)
        banco.salvar_leads(self.conn, b2, leads()[:3], "Cidade Teste", "DF", False)
        self.assertEqual(len(banco.todos_os_leads(self.conn)), 11)
        self.assertEqual(len(banco.leads_da_busca(self.conn, b2)), 3)

    def test_nova_busca_preserva_status_e_anotacao(self):
        b1, b2 = self.nova_busca(), self.nova_busca()
        banco.salvar_leads(self.conn, b1, leads(), "Cidade Teste", "DF", False)
        banco.mudar_status(self.conn, "p:pid1", "contatado")
        self.conn.execute("UPDATE leads SET anotacao='ligar terça' WHERE chave='p:pid1'")
        banco.salvar_leads(self.conn, b2, leads(), "Cidade Teste", "DF", False)
        l = next(x for x in banco.todos_os_leads(self.conn) if x["chave"] == "p:pid1")
        self.assertEqual((l["status"], l["anotacao"]), ("contatado", "ligar terça"))

    def test_nova_busca_atualiza_dados_do_maps(self):
        b1, b2 = self.nova_busca(), self.nova_busca()
        banco.salvar_leads(self.conn, b1, [limpeza.limpar_linha(linha(1, review_count="10"))], "C", "DF", False)
        banco.salvar_leads(self.conn, b2, [limpeza.limpar_linha(linha(1, review_count="99"))], "C", "DF", False)
        self.assertEqual(banco.todos_os_leads(self.conn)[0]["avaliacoes"], 99)

    def test_status_invalido(self):
        with self.assertRaises(ValueError):
            banco.mudar_status(self.conn, "p:pid1", "vendido")

    def test_notas_gravadas_e_exclusao_nunca(self):
        b = self.nova_busca()
        banco.salvar_leads(self.conn, b, leads(), "Cidade Teste", "DF", False)
        banco.gravar_notas(self.conn, {"p:pid1": {"nota": 8, "letra": "A", "motivos": ["sem site (+3)"]}})
        l = next(x for x in banco.todos_os_leads(self.conn) if x["chave"] == "p:pid1")
        self.assertEqual((l["nota"], l["letra"], l["motivos"]), (8, "A", ["sem site (+3)"]))
        colunas = [c[1] for c in self.conn.execute("PRAGMA table_info(leads)")]
        self.assertFalse([c for c in colunas if "exclu" in c or "rede" in c])


if __name__ == "__main__":
    unittest.main()
