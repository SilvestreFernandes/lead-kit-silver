import tempfile
import threading
import unittest
from pathlib import Path

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

    def salvar(self, busca_id, lista=None):
        banco.salvar_leads(self.conn, busca_id, lista if lista is not None else leads(),
                           "Cidade Teste", "DF", False)

    def lead_por_nome(self, nome):
        return next(l for l in banco.todos_os_leads(self.conn) if l["nome"] == nome)

    def test_busca_criada_e_atualizada(self):
        b = self.nova_busca()
        banco.atualizar_busca(self.conn, b, status="ok", job_id="abc", total_leads=3)
        d = banco.obter_busca(self.conn, b)
        self.assertEqual((d["status"], d["job_id"], d["total_leads"]), ("ok", "abc", 3))

    def test_parametros_voltam_como_dicionario(self):
        b = self.nova_busca()
        banco.atualizar_busca(self.conn, b, parametros={"depth": 3})
        self.assertEqual(banco.obter_busca(self.conn, b)["parametros"], {"depth": 3})

    def test_campo_de_busca_invalido(self):
        b = self.nova_busca()
        with self.assertRaises(ValueError):
            banco.atualizar_busca(self.conn, b, **{"status = 'x'; DROP TABLE leads; --": "ok"})
        with self.assertRaises(ValueError):
            banco.atualizar_busca(self.conn, b)

    def test_lista_buscas_da_mais_nova_para_a_mais_antiga(self):
        a, b = self.nova_busca(), self.nova_busca()
        self.assertEqual([x["id"] for x in banco.listar_buscas(self.conn)], [b, a])

    def test_buscas_abertas_viram_erro_ao_reiniciar(self):
        a, b, c = self.nova_busca(), self.nova_busca(), self.nova_busca()
        banco.atualizar_busca(self.conn, b, status="working")
        banco.atualizar_busca(self.conn, c, status="ok")
        self.assertEqual(banco.interromper_buscas_abertas(self.conn), 2)
        self.assertEqual(banco.obter_busca(self.conn, a)["status"], "erro")
        self.assertIn("Interrompida", banco.obter_busca(self.conn, b)["erro"])
        self.assertEqual(banco.obter_busca(self.conn, c)["status"], "ok")

    def test_salva_e_le_leads_com_id_inteiro(self):
        b = self.nova_busca()
        self.salvar(b)
        lidos = banco.leads_da_busca(self.conn, b)
        self.assertEqual(len(lidos), 11)
        self.assertTrue(all(isinstance(l["id"], int) for l in lidos))
        completa = self.lead_por_nome("Padaria Completa")
        self.assertIs(completa["delivery"], True)
        self.assertIs(completa["celular"], True)
        self.assertEqual(completa["emails"], [])
        self.assertEqual(banco.obter_lead(self.conn, completa["id"])["nome"], "Padaria Completa")
        self.assertIsNone(banco.obter_lead(self.conn, 9999))

    def test_mesmo_negocio_em_duas_buscas_vira_um_lead(self):
        b1, b2 = self.nova_busca(), self.nova_busca()
        self.salvar(b1)
        self.salvar(b2, leads()[:3])
        self.assertEqual(len(banco.todos_os_leads(self.conn)), 11)
        self.assertEqual(len(banco.leads_da_busca(self.conn, b2)), 3)
        self.assertEqual(len(banco.ids_da_busca(self.conn, b2)), 3)

    def test_id_do_lead_nao_muda_numa_nova_busca(self):
        b1, b2 = self.nova_busca(), self.nova_busca()
        self.salvar(b1)
        antes = self.lead_por_nome("Pão Sem Site")["id"]
        self.salvar(b2)
        self.assertEqual(self.lead_por_nome("Pão Sem Site")["id"], antes)

    def test_nova_busca_preserva_status_e_anotacao(self):
        b1, b2 = self.nova_busca(), self.nova_busca()
        self.salvar(b1)
        lid = self.lead_por_nome("Pão Sem Site")["id"]
        banco.atualizar_lead(self.conn, lid, status="contatado", anotacao="ligar terça",
                             mensagem_editada="oi!")
        self.salvar(b2)
        l = banco.obter_lead(self.conn, lid)
        self.assertEqual((l["status"], l["anotacao"], l["mensagem_editada"]),
                         ("contatado", "ligar terça", "oi!"))

    def test_nova_busca_atualiza_dados_do_maps(self):
        b1, b2 = self.nova_busca(), self.nova_busca()
        self.salvar(b1, [limpeza.limpar_linha(linha(1, review_count="10"))])
        self.salvar(b2, [limpeza.limpar_linha(linha(1, review_count="99"))])
        self.assertEqual(banco.todos_os_leads(self.conn)[0]["avaliacoes"], 99)

    def test_atualizar_so_o_que_foi_pedido(self):
        b = self.nova_busca()
        self.salvar(b)
        lid = self.lead_por_nome("Pão Sem Site")["id"]
        banco.atualizar_lead(self.conn, lid, anotacao="x")
        l = banco.obter_lead(self.conn, lid)
        self.assertEqual((l["status"], l["anotacao"]), ("novo", "x"))

    def test_atualizar_lead_inexistente_e_status_invalido(self):
        self.assertFalse(banco.atualizar_lead(self.conn, 123, status="contatado"))
        b = self.nova_busca()
        self.salvar(b)
        lid = self.lead_por_nome("Pão Sem Site")["id"]
        with self.assertRaises(ValueError):
            banco.atualizar_lead(self.conn, lid, status="vendido")

    def test_notas_gravadas_e_exclusao_nunca(self):
        b = self.nova_busca()
        self.salvar(b)
        banco.gravar_notas(self.conn, {"p:pid1": {"nota": 8, "letra": "A", "motivos": ["sem site (+3)"]}})
        l = self.lead_por_nome("Pão Sem Site")
        self.assertEqual((l["nota"], l["letra"], l["motivos"]), (8, "A", ["sem site (+3)"]))
        colunas = [c[1] for c in self.conn.execute("PRAGMA table_info(leads)")]
        self.assertFalse([c for c in colunas if "exclu" in c or "rede" in c])


class TestUmaConexaoPorThread(unittest.TestCase):
    def test_conexao_nao_pode_ser_usada_em_outra_thread(self):
        conn = banco.abrir()
        self.addCleanup(conn.close)
        erros = []

        def usar():
            try:
                conn.execute("SELECT 1")
            except Exception as e:  # sqlite3.ProgrammingError
                erros.append(type(e).__name__)

        t = threading.Thread(target=usar)
        t.start()
        t.join()
        self.assertEqual(erros, ["ProgrammingError"])

    def test_threads_com_conexoes_proprias_gravam_no_mesmo_arquivo(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = str(Path(d) / "leads.db")
            conn = banco.abrir(caminho)
            busca = banco.criar_busca(conn, "p", "C", "DF", "rapida", {}, False)
            conn.close()
            falhas = []

            def gravar(n):
                try:
                    c = banco.abrir(caminho)
                    banco.salvar_leads(c, busca, [limpeza.limpar_linha(linha(n))], "C", "DF", False)
                    c.close()
                except Exception as e:
                    falhas.append(repr(e))

            threads = [threading.Thread(target=gravar, args=(i,)) for i in range(1, 9)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            conn = banco.abrir(caminho)
            total = len(banco.todos_os_leads(conn))
            conn.close()
        self.assertEqual((falhas, total), ([], 8))


class TestBancoDaEtapa4(unittest.TestCase):
    def test_banco_antigo_ganha_as_colunas_novas_sem_perder_nada(self):
        import sqlite3
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            caminho = str(Path(d) / "antigo.db")
            conn = sqlite3.connect(caminho)
            conn.executescript("""
                CREATE TABLE buscas (id INTEGER PRIMARY KEY AUTOINCREMENT, criada_em TEXT NOT NULL,
                    categoria TEXT NOT NULL, cidade TEXT NOT NULL, uf TEXT NOT NULL, tamanho TEXT NOT NULL,
                    parametros TEXT NOT NULL, email_ligado INTEGER NOT NULL DEFAULT 0, job_id TEXT,
                    status TEXT NOT NULL DEFAULT 'criada', erro TEXT, total_leads INTEGER);
                INSERT INTO buscas (criada_em, categoria, cidade, uf, tamanho, parametros, status, total_leads)
                    VALUES ('2026-10-01T10:00:00', 'padaria', 'Sobradinho', 'DF', 'rapida', '{}', 'ok', 16);
            """)
            conn.commit()
            conn.close()
            novo = banco.abrir(caminho)
            for _ in range(2):  # abrir de novo nao quebra (migracao idempotente)
                novo.close()
                novo = banco.abrir(caminho)
            b = banco.obter_busca(novo, 1)
            novo.close()
        self.assertEqual((b["categoria"], b["total_leads"]), ("padaria", 16))
        for coluna in ("novos", "ja_existiam", "fora_da_lista", "erro_tipo", "terminou_em"):
            self.assertIn(coluna, b)
            self.assertIsNone(b[coluna])

    def test_novos_campos_da_busca_sao_gravados(self):
        conn = banco.abrir()
        self.addCleanup(conn.close)
        b = banco.criar_busca(conn, "x", "C", "DF", "rapida", {}, False)
        banco.atualizar_busca(conn, b, status="ok", novos=7, ja_existiam=3, fora_da_lista=2,
                              erro_tipo=None, terminou_em="2026-10-30T10:00:00")
        d = banco.obter_busca(conn, b)
        self.assertEqual((d["novos"], d["ja_existiam"], d["fora_da_lista"], d["terminou_em"]),
                         (7, 3, 2, "2026-10-30T10:00:00"))

    def test_chaves_existentes_inclusive_com_mais_de_500(self):
        conn = banco.abrir()
        self.addCleanup(conn.close)
        b = banco.criar_busca(conn, "x", "C", "DF", "rapida", {}, False)
        leads = [limpeza.limpar_linha(linha(n)) for n in range(1, 701)]
        banco.salvar_leads(conn, b, leads, "C", "DF", False)
        quero = [l["chave"] for l in leads] + ["p:nao-existe-1", "p:nao-existe-2"]
        achadas = banco.chaves_existentes(conn, quero)
        self.assertEqual(len(achadas), 700)
        self.assertNotIn("p:nao-existe-1", achadas)
        self.assertEqual(banco.chaves_existentes(conn, []), set())

    def test_busca_interrompida_ganha_tipo_e_hora_de_fim(self):
        conn = banco.abrir()
        self.addCleanup(conn.close)
        b = banco.criar_busca(conn, "x", "C", "DF", "rapida", {}, False)
        banco.atualizar_busca(conn, b, status="working")
        banco.interromper_buscas_abertas(conn)
        d = banco.obter_busca(conn, b)
        self.assertEqual((d["status"], d["erro_tipo"]), ("erro", "interrompida"))
        self.assertTrue(d["terminou_em"])


if __name__ == "__main__":
    unittest.main()
