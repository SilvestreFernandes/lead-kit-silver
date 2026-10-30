import json
import tempfile
import unittest
from pathlib import Path

from kit import banco, buscar
from kit import motor as m
from kit.geocodificar import ErroGeocodificacao
from testes.fixtures import GeoDeMentira, MotorDeMentira, csv_texto, linha, perfil_ficticio


class TestBuscar(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.pasta = Path(self._tmp.name)
        self.perfil = self.pasta / "perfil.json"
        self.perfil.write_text(json.dumps(perfil_ficticio()), encoding="utf-8")
        self.banco = self.pasta / "leads.db"
        self.linhas = []

    def args(self, *extra):
        return buscar.ler_argumentos([
            "--categoria", "padaria", "--cidade", "Cidade Teste", "--uf", "df",
            "--perfil", str(self.perfil), "--banco", str(self.banco), *extra])

    def rodar(self, motor=None, geo=None, *extra):
        self.linhas = []
        codigo = buscar.executar(self.args(*extra), motor or MotorDeMentira(), geo or GeoDeMentira(),
                                 saida=self.linhas.append)
        return codigo, "\n".join(self.linhas)

    def test_busca_completa_lista_leads_com_nota_e_motivos(self):
        motor, geo = MotorDeMentira(), GeoDeMentira()
        codigo, texto = self.rodar(motor, geo)
        self.assertEqual(codigo, 0)
        self.assertEqual(geo.chamadas, [("Cidade Teste", "DF")])
        self.assertEqual(motor.pedidos[0]["keywords"], ["padaria em Cidade Teste DF"])
        self.assertEqual(motor.pedidos[0]["lat"], "-15.65")
        self.assertIn("Achei 11 negócios", texto)
        self.assertIn("Pão Sem Site", texto)
        self.assertIn("sem site (+3)", texto)

    def test_melhor_lead_vem_primeiro(self):
        _, texto = self.rodar()
        corpo = texto.split("Negócio")[1].splitlines()[1:]
        self.assertIn("Pão Sem Site", corpo[0])

    def test_excluidos_aparecem_separados_com_motivo(self):
        _, texto = self.rodar()
        parte = texto.split("Excluídos:")[1]
        self.assertIn("Sem Telefone", parte)
        self.assertIn("sem telefone", parte)
        self.assertIn("possível rede (nome repetido em 3 endereços)", parte)

    def test_grava_busca_leads_e_notas_no_banco(self):
        self.rodar()
        conn = banco.abrir(str(self.banco))
        self.addCleanup(conn.close)
        busca = banco.obter_busca(conn, 1)
        self.assertEqual((busca["status"], busca["job_id"], busca["total_leads"]), ("ok", "job1", 11))
        l = next(x for x in banco.todos_os_leads(conn) if x["nome"] == "Pão Sem Site")
        self.assertEqual((l["letra"], l["nota"]), ("A", 8))

    def test_segunda_busca_nao_duplica_leads(self):
        self.rodar()
        self.rodar()
        conn = banco.abrir(str(self.banco))
        self.addCleanup(conn.close)
        self.assertEqual(len(banco.todos_os_leads(conn)), 11)

    def test_limite_corta_a_lista(self):
        _, texto = self.rodar(None, None, "--limite", "2")
        self.assertIn("e mais", texto)

    def test_perfil_ausente(self):
        self.perfil.unlink()
        codigo, texto = self.rodar()
        self.assertEqual(codigo, 1)
        self.assertIn("Não achei o perfil", texto)

    def test_perfil_invalido_nao_chama_o_motor(self):
        p = perfil_ficticio()
        p["negocio"]["oferta"] = ""
        self.perfil.write_text(json.dumps(p), encoding="utf-8")
        motor = MotorDeMentira()
        codigo, texto = self.rodar(motor)
        self.assertEqual((codigo, motor.pedidos), (1, []))
        self.assertIn("negocio.oferta", texto)

    def test_motor_desligado(self):
        codigo, texto = self.rodar(MotorDeMentira(ligado=False))
        self.assertEqual(codigo, 1)
        self.assertIn("docker compose up -d", texto)

    def test_cidade_nao_achada(self):
        codigo, texto = self.rodar(None, GeoDeMentira(ErroGeocodificacao("Não achei a cidade X-DF.")))
        self.assertEqual(codigo, 1)
        self.assertIn("Não achei a cidade", texto)

    def test_erro_do_motor_marca_a_busca_como_erro(self):
        codigo, texto = self.rodar(MotorDeMentira(falha=m.ErroMotor("passou do tempo")))
        self.assertEqual(codigo, 1)
        self.assertIn("passou do tempo", texto)
        conn = banco.abrir(str(self.banco))
        self.addCleanup(conn.close)
        busca = banco.obter_busca(conn, 1)
        self.assertEqual((busca["status"], busca["erro"]), ("erro", "passou do tempo"))

    def test_csv_com_formato_inesperado(self):
        codigo, texto = self.rodar(MotorDeMentira(csv="a,b\n1,2\n"))
        self.assertEqual(codigo, 1)
        self.assertIn("colunas esperadas", texto)

    def test_email_ligado_vai_no_pedido_e_ativa_sem_email(self):
        p = perfil_ficticio()
        p["pontuacao"]["regras"] = [{"id": "sem_email", "peso": 1}]
        self.perfil.write_text(json.dumps(p), encoding="utf-8")
        motor = MotorDeMentira()
        _, texto = self.rodar(motor, None, "--email")
        self.assertTrue(motor.pedidos[0]["email"])
        self.assertIn("nenhum e-mail publicado (+1)", texto)

    def test_sem_email_ligado_a_regra_nao_marca_ninguem(self):
        p = perfil_ficticio()
        p["pontuacao"]["regras"] = [{"id": "sem_email", "peso": 1}]
        self.perfil.write_text(json.dumps(p), encoding="utf-8")
        _, texto = self.rodar()
        self.assertNotIn("nenhum e-mail publicado", texto)

    def test_executar_busca_avisa_cada_etapa_em_ordem(self):
        conn = banco.abrir(str(self.banco))
        self.addCleanup(conn.close)
        bid = buscar.iniciar_busca(conn, "padaria", "Cidade Teste", "DF", "rapida", False)
        etapas = []
        buscar.executar_busca(conn, bid, perfil_ficticio(), MotorDeMentira(), GeoDeMentira(),
                              lambda etapa, seg=None: etapas.append(etapa))
        sem_repeticao = [e for i, e in enumerate(etapas) if i == 0 or e != etapas[i - 1]]
        self.assertEqual(sem_repeticao, ["Achando a cidade no mapa", "Enviando a busca ao motor",
                                         "Esperando o motor", "Lendo os resultados",
                                         "Calculando as notas"])

    def test_erro_inesperado_tambem_marca_a_busca(self):
        conn = banco.abrir(str(self.banco))
        self.addCleanup(conn.close)
        bid = buscar.iniciar_busca(conn, "padaria", "Cidade Teste", "DF", "rapida", False)
        with self.assertRaises(RuntimeError):
            buscar.executar_busca(conn, bid, perfil_ficticio(), MotorDeMentira(falha=RuntimeError("quebrou")),
                                  GeoDeMentira())
        busca = banco.obter_busca(conn, bid)
        self.assertEqual(busca["status"], "erro")
        self.assertIn("quebrou", busca["erro"])

    def test_uf_vira_maiuscula_e_tamanho_invalido_e_recusado(self):
        self.assertEqual(self.args().uf, "DF")
        with self.assertRaises(SystemExit):
            self.args("--tamanho", "gigante")


def csv_do_ponto(*numeros):
    """CSV fictício com os negócios de números dados (o mesmo número é o mesmo negócio)."""
    return csv_texto([linha(n, title=f"Negócio {n}", phone="(61) 3333-%04d" % n) for n in numeros])


class TestBuscaMedia(unittest.TestCase):
    """Busca média: 5 pontos, um job por ponto, pausa entre eles e junção sem repetir."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self._tmp.cleanup)
        self.banco = str(Path(self._tmp.name) / "leads.db")
        self.conn = banco.abrir(self.banco)
        self.addCleanup(self.conn.close)
        self.pausas, self.etapas = [], []
        # pontos vizinhos repetem negócios: 1..4, 3..6, 5..8, 7..10, 9..12 (12 únicos, 20 linhas)
        self.csvs = [csv_do_ponto(*range(a, a + 4)) for a in (1, 3, 5, 7, 9)]

    def rodar(self, motor, tamanho="media"):
        bid = buscar.iniciar_busca(self.conn, "padaria", "Cidade Teste", "DF", tamanho, False)
        resultado = None
        try:
            resultado = buscar.executar_busca(
                self.conn, bid, perfil_ficticio(), motor, GeoDeMentira(),
                lambda etapa, seg=None: self.etapas.append(etapa), dormir=self.pausas.append)
        finally:
            self.busca_id = bid
        return resultado

    def test_cinco_jobs_com_centro_e_quatro_pontos_ao_redor(self):
        motor = MotorDeMentira(csv=self.csvs)
        self.rodar(motor)
        self.assertEqual(len(motor.pedidos), 5)
        self.assertEqual([p["radius"] for p in motor.pedidos], [5000] * 5)
        self.assertEqual({p["depth"] for p in motor.pedidos}, {3})
        self.assertEqual({p["max_time"] for p in motor.pedidos}, {300})
        self.assertEqual({p["keywords"][0] for p in motor.pedidos}, {"padaria em Cidade Teste DF"})
        centro = (motor.pedidos[0]["lat"], motor.pedidos[0]["lon"])
        self.assertEqual(centro, ("-15.65", "-47.79"))
        self.assertEqual(len({(p["lat"], p["lon"]) for p in motor.pedidos}), 5)  # pontos diferentes

    def test_pausa_de_15_segundos_entre_os_pontos(self):
        self.rodar(MotorDeMentira(csv=self.csvs))
        self.assertEqual(self.pausas, [15, 15, 15, 15])  # 5 pontos, 4 pausas, nenhuma antes do primeiro

    def test_junta_sem_repetir(self):
        resultado = self.rodar(MotorDeMentira(csv=self.csvs))
        self.assertEqual(len(resultado["achados"]), 12)
        self.assertEqual(len(banco.todos_os_leads(self.conn)), 12)
        busca = banco.obter_busca(self.conn, self.busca_id)
        self.assertEqual((busca["status"], busca["total_leads"]), ("ok", 12))
        self.assertEqual(len(busca["parametros"]["pedidos"]), 5)
        self.assertEqual(busca["job_id"], "job1,job2,job3,job4,job5")

    def test_todos_os_negocios_ficam_ligados_a_busca(self):
        self.rodar(MotorDeMentira(csv=self.csvs))
        self.assertEqual(len(banco.ids_da_busca(self.conn, self.busca_id)), 12)

    def test_progresso_diz_em_que_ponto_esta(self):
        self.rodar(MotorDeMentira(csv=self.csvs))
        self.assertIn("Esperando o motor (ponto 1 de 5)", self.etapas)
        self.assertIn("Esperando o motor (ponto 5 de 5)", self.etapas)
        self.assertIn("Pausa entre os pontos (ponto 2 de 5)", self.etapas)

    def test_rapida_continua_sendo_um_job_sem_pausa_e_sem_texto_de_ponto(self):
        motor = MotorDeMentira()
        self.rodar(motor, "rapida")
        self.assertEqual((len(motor.pedidos), self.pausas), (1, []))
        self.assertEqual(motor.pedidos[0]["radius"], 10000)
        self.assertEqual(motor.pedidos[0]["depth"], 1)
        self.assertNotIn("ponto", " ".join(self.etapas))

    def test_falha_no_meio_guarda_o_que_ja_veio_e_avisa_onde_parou(self):
        motor = MotorDeMentira(csv=self.csvs, falha_a_partir_do_job=(3, m.ErroMotor("sem resposta")))
        with self.assertRaises(m.ErroMotor) as e:
            self.rodar(motor)
        self.assertIn("ponto 3 de 5", str(e.exception))
        self.assertIn("6 negócios", str(e.exception))   # pontos 1 e 2: 1..6
        self.assertIn("sem resposta", str(e.exception))
        busca = banco.obter_busca(self.conn, self.busca_id)
        self.assertEqual((busca["status"], busca["total_leads"]), ("erro", 6))
        self.assertIn("ponto 3 de 5", busca["erro"])
        leads = banco.todos_os_leads(self.conn)
        self.assertEqual(len(leads), 6)
        self.assertTrue(all(l["letra"] for l in leads))  # as notas dos salvos foram calculadas
        self.assertEqual(len(motor.pedidos), 3)          # não tentou os pontos 4 e 5

    def test_falha_no_primeiro_ponto_nao_inventa_resultado_parcial(self):
        motor = MotorDeMentira(csv=self.csvs, falha_a_partir_do_job=(1, m.ErroMotor("fora do ar")))
        with self.assertRaises(m.ErroMotor) as e:
            self.rodar(motor)
        self.assertEqual(str(e.exception), "fora do ar")
        self.assertEqual(banco.todos_os_leads(self.conn), [])

    def test_ampla_ainda_nao_existe(self):
        self.assertNotIn("ampla", m.TAMANHOS)
        self.assertEqual(m.TAMANHOS_EM_BREVE, ("ampla",))
        with self.assertRaises(SystemExit):
            buscar.ler_argumentos(["--categoria", "x", "--cidade", "y", "--uf", "DF", "--tamanho", "ampla"])


if __name__ == "__main__":
    unittest.main()
