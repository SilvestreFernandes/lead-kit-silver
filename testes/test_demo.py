"""Teste de fumaca da demonstracao do painel: todo estado sobe e responde o que promete."""
import json
import shutil
import threading
import unittest
import urllib.request

from testes import demo_painel


class TestDemoDoPainel(unittest.TestCase):
    def subir(self, estado):
        srv = demo_painel.montar(estado, 0)
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
        self.addCleanup(lambda: (srv.shutdown(), srv.server_close(), shutil.rmtree(srv.pasta_temporaria, ignore_errors=True)))
        return srv

    def ler(self, srv, caminho):
        with urllib.request.urlopen(f"http://127.0.0.1:{srv.porta}{caminho}", timeout=10) as r:
            return json.loads(r.read())

    def test_todo_estado_sobe(self):
        for estado in demo_painel.ESTADOS:
            with self.subTest(estado=estado):
                srv = self.subir(estado)
                d = self.ler(srv, "/api/estado")
                self.assertEqual(d["motor_no_ar"], estado != "motor_desligado")
                esperado = {"perfil_ausente": (False, False), "perfil_invalido": (True, False)}.get(estado, (True, True))
                self.assertEqual((d["perfil"]["existe"], d["perfil"]["valido"]), esperado)

    def test_normal_tem_excluidos_um_lead_acompanhado_e_um_nome_malicioso(self):
        srv = self.subir("normal")
        todos = self.ler(srv, "/api/leads?excluidos=todos&limite=100")["leads"]
        self.assertEqual(len(todos), 10)
        self.assertEqual(len([l for l in todos if l["excluido_por"]]), 4)
        self.assertTrue(any(l["status"] == "contatado" for l in todos))
        self.assertTrue(any("<img" in l["nome"] for l in todos))

    def test_muitos_tem_650_leads(self):
        srv = self.subir("muitos")
        self.assertEqual(self.ler(srv, "/api/leads?excluidos=todos&limite=1")["total"], 650)

    def test_regulado_mostra_a_restricao_no_perfil(self):
        srv = self.subir("regulado")
        self.assertIn("advocacia", self.ler(srv, "/api/perfil")["perfil"]["conformidade"]["restricoes"])

    def test_sem_leads_nao_tem_busca_e_tudo_excluido_tem_lista_vazia(self):
        sem = self.subir("sem_leads")
        self.assertEqual((self.ler(sem, "/api/leads")["total"], self.ler(sem, "/api/buscas")["buscas"]), (0, []))
        todos = self.subir("tudo_excluido")
        self.assertEqual(self.ler(todos, "/api/leads")["total"], 0)
        self.assertEqual(self.ler(todos, "/api/leads?excluidos=todos")["total"], 5)
        self.assertEqual(len(self.ler(todos, "/api/buscas")["buscas"]), 1)

    def test_a_demo_usa_pasta_temporaria_e_nunca_a_pasta_dados_de_verdade(self):
        from pathlib import Path
        srv = self.subir("normal")
        real = Path(demo_painel.RAIZ) / "dados"
        self.assertNotEqual(srv.caminho_banco.parent.resolve(), real.resolve())
        self.assertNotIn(str(real.resolve()), str(srv.caminho_banco.resolve()))


if __name__ == "__main__":
    unittest.main()
