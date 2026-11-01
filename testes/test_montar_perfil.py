"""Das respostas da entrevista ao perfil: os três perfis de teste, a conferência de cada resposta e a gravação segura."""
import contextlib
import copy
import io
import json
import random
import tempfile
import unittest
from datetime import date
from pathlib import Path

from kit import montar_perfil, validar_perfil
from testes.fixtures import linha
from testes.perfis import leads

PASTA_PERFIS = Path(__file__).resolve().parent / "perfis"
NOMES = ("agencia_de_sites", "fornecedor_b2b", "contabilidade_regulada")


def respostas(nome):
    return json.loads((PASTA_PERFIS / f"{nome}.json").read_text(encoding="utf-8"))


def nomes_na_ordem(avaliados):
    return [r["lead"]["nome"] for r in avaliados]


def rodar(*argv):
    """Roda a linha de comando e devolve (código, saída em JSON)."""
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        codigo = montar_perfil.main(list(argv))
    return codigo, json.loads(saida.getvalue())


class TestOsTresPerfisDeTeste(unittest.TestCase):
    def test_cada_perfil_passa_na_validacao_de_primeira(self):
        for nome in NOMES:
            with self.subTest(nome):
                perfil, erros, avisos = montar_perfil.montar(respostas(nome), hoje=date(2026, 11, 1))
                self.assertEqual(erros, [])
                self.assertEqual(perfil["criado_em"], "2026-11-01")
                # o mesmo validador do painel não acha nada a corrigir nem a avisar
                corrigido, erros2, avisos2 = validar_perfil.validar(perfil)
                self.assertEqual((erros2, avisos2), ([], []))
                self.assertEqual(corrigido, perfil)

    def test_agencia_de_sites(self):
        perfil, erros, avisos = montar_perfil.montar(respostas("agencia_de_sites"))
        self.assertEqual((erros, avisos), ([], []))
        self.assertEqual(perfil["negocio"], {"nome": "Ana Souza", "empresa": "Estúdio Exemplo",
                                             "oferta": "Sites e automações com IA para negócios locais", "atendimento": "remoto"})
        self.assertEqual(perfil["cliente"]["regioes"], ["Brasília-DF", "Sobradinho-DF"])
        self.assertEqual([r["id"] for r in perfil["pontuacao"]["regras"]], ["sem_site", "so_instagram", "nota_alta", "muitas_avaliacoes"])
        self.assertEqual([r["peso"] for r in perfil["pontuacao"]["regras"]], [3, 2, 2, 1])  # os pesos padrão do kit
        self.assertEqual(perfil["exclusoes"], ["sem_telefone", "franquia"])
        self.assertEqual(perfil["abordagem"], {"canais": ["whatsapp"], "tom": "amigavel", "oferta_entrada": "diagnóstico grátis",
                                               "volume_semana": "10-30"})
        self.assertEqual(perfil["conformidade"]["restricoes"], "nao")
        self.assertEqual(perfil["mensagens"], {})  # os modelos de mensagem vêm no passo seguinte da fase 4

    def test_fornecedor_b2b_desdobra_a_pergunta_6(self):
        perfil, erros, avisos = montar_perfil.montar(respostas("fornecedor_b2b"))
        self.assertEqual(erros, [])
        self.assertEqual(perfil["exclusoes"], ["sem_telefone", "concorrente", "categoria"])
        self.assertEqual(perfil["exclusoes_concorrentes"], ["Embalagens Rivais", "rival.exemplo.invalid"])
        self.assertEqual(perfil["exclusoes_categorias"], ["igreja", "escola"])
        self.assertEqual([r["id"] for r in perfil["pontuacao"]["regras"]], ["nota_alta", "muitas_avaliacoes", "delivery"])
        self.assertEqual(perfil["abordagem"]["canais"], ["whatsapp", "email"])
        self.assertEqual(len(avisos), 1)
        self.assertIn("não vira regra", avisos[0])  # "outra resposta" da pergunta 5 só fica anotada

    def test_profissional_regulado(self):
        perfil, erros, avisos = montar_perfil.montar(respostas("contabilidade_regulada"))
        self.assertEqual(erros, [])
        self.assertEqual(perfil["conformidade"]["restricoes"], "sim: conselho de contabilidade (CRC)")
        self.assertEqual(perfil["cliente"]["regioes"], ["Brasília-DF"])  # "Brasília - DF" foi arrumado
        self.assertEqual(perfil["negocio"]["empresa"], "")
        self.assertTrue(any("só o seu nome" in a for a in avisos))
        self.assertEqual(perfil["abordagem"]["tom"], "formal")

    def test_a_mesma_busca_gera_listas_em_ordem_diferente_para_cada_perfil(self):
        listas = {}
        for nome in NOMES:
            perfil, erros, _ = montar_perfil.montar(respostas(nome))
            self.assertEqual(erros, [])
            listas[nome] = nomes_na_ordem(leads.avaliar(perfil))
            self.assertEqual(len(listas[nome]), 10)
        self.assertEqual(sorted(listas["agencia_de_sites"]), sorted(listas["fornecedor_b2b"]))  # os mesmos 10 negócios
        for a in NOMES:
            for b in NOMES:
                if a < b:
                    self.assertNotEqual(listas[a], listas[b], f"{a} e {b} ordenaram igual")
                    self.assertNotEqual(listas[a][:3], listas[b][:3], f"{a} e {b} têm o mesmo topo")

    def test_agencia_leads_sem_site_ficam_no_topo_com_nota_a(self):
        perfil, _, _ = montar_perfil.montar(respostas("agencia_de_sites"))
        avaliados = leads.avaliar(perfil)
        topo = avaliados[0]
        self.assertEqual((topo["lead"]["nome"], topo["letra"]), ("Padaria Sem Site Movimentada", "A"))
        self.assertFalse(topo["lead"]["site"])
        sem_site_ou_rede = {r["lead"]["nome"] for r in avaliados[:4]}
        self.assertEqual(sem_site_ou_rede, {"Padaria Sem Site Movimentada", "Barbearia Novinha", "Oficina Instagram Famosa",
                                            "Salão Sem Site e Pouca Gente"})

    def test_fornecedor_nota_alta_e_muitas_avaliacoes_pesam_mais_e_site_nao_importa(self):
        perfil, _, _ = montar_perfil.montar(respostas("fornecedor_b2b"))
        self.assertNotIn("sem_site", [r["id"] for r in perfil["pontuacao"]["regras"]])
        avaliados = leads.avaliar(perfil)
        topo = {r["lead"]["nome"] for r in avaliados[:2]}
        self.assertEqual(topo, {"Pizzaria Tradicional", "Restaurante Delivery Famoso"})
        self.assertTrue(all(r["lead"]["site"] for r in avaliados[:2]))  # os dois do topo têm site próprio
        por_nome = {r["lead"]["nome"]: r for r in avaliados}
        self.assertGreater(por_nome["Pizzaria Tradicional"]["nota"], por_nome["Padaria Sem Site Movimentada"]["nota"])

    def test_fornecedor_exclui_concorrente_e_categoria_da_lista(self):
        perfil, _, _ = montar_perfil.montar(respostas("fornecedor_b2b"))
        extras = [linha(11, title="Embalagens Rivais Centro", category="Embalagens", website="", phone="(61) 3340-0211"),
                  linha(12, title="Igreja Central", category="Igreja", website="", phone="(61) 3340-0212"),
                  linha(13, title="Loja de rival.exemplo.invalid", category="Loja", website="https://rival.exemplo.invalid", phone="(61) 3340-0213")]
        avaliados = {r["lead"]["nome"]: r for r in leads.avaliar(perfil, extras)}
        self.assertEqual(avaliados["Embalagens Rivais Centro"]["excluido_por"], "concorrente da sua lista")
        self.assertEqual(avaliados["Igreja Central"]["excluido_por"], "categoria que você quer evitar")
        self.assertEqual(avaliados["Loja de rival.exemplo.invalid"]["excluido_por"], "concorrente da sua lista")

    def test_regulado_tem_o_aviso_de_conformidade_e_um_lead_a(self):
        perfil, _, _ = montar_perfil.montar(respostas("contabilidade_regulada"))
        self.assertTrue(perfil["conformidade"]["restricoes"].startswith("sim"))  # o painel mostra o aviso fixo por isso
        avaliados = leads.avaliar(perfil)
        self.assertEqual((avaliados[0]["lead"]["nome"], avaliados[0]["letra"]), ("Loja de Roupas Instagram", "A"))

    def test_refazer_guarda_o_perfil_anterior(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as pasta:
            pasta = Path(pasta)
            (pasta / "respostas.json").write_text(json.dumps(respostas("agencia_de_sites")), encoding="utf-8")
            self.assertEqual(rodar("montar", "--pasta-dados", str(pasta))[0], 0)
            antigo = (pasta / "perfil.json").read_text(encoding="utf-8")
            novas = respostas("fornecedor_b2b")
            (pasta / "respostas.json").write_text(json.dumps(novas), encoding="utf-8")
            self.assertEqual(rodar("montar", "--pasta-dados", str(pasta), "--refazer")[0], 0)
            self.assertEqual((pasta / "perfil.anterior.json").read_text(encoding="utf-8"), antigo)
            self.assertEqual(json.loads((pasta / "perfil.json").read_text(encoding="utf-8"))["negocio"]["nome"], "Carlos Lima")


class TestEntrevistadorDeMentira(unittest.TestCase):
    """Faz o papel da IA: grava uma resposta por vez e pergunta o que falta, como o roteiro manda."""

    def test_responder_uma_a_uma_em_ordem(self):
        for nome in NOMES:
            with self.subTest(nome), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as pasta:
                pasta = Path(pasta)
                todas = respostas(nome)
                gravadas = {"versao": 1}
                ordem_esperada = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12]
                for n in range(1, 13):
                    codigo, antes = rodar("estado", "--pasta-dados", str(pasta))
                    self.assertEqual(codigo, 0)
                    if n != 7:
                        self.assertEqual(antes["proxima"], n)
                        self.assertEqual(antes["faltam"], [x for x in ordem_esperada if x >= n])
                    gravadas[str(n)] = todas[str(n)]
                    (pasta / "respostas.json").write_text(json.dumps(gravadas), encoding="utf-8")
                _, fim = rodar("estado", "--pasta-dados", str(pasta))
                self.assertEqual((fim["faltam"], fim["proxima"], fim["erros"]), ([], None, []))
                codigo, resumo = rodar("resumo", "--pasta-dados", str(pasta))
                self.assertEqual(codigo, 0)
                self.assertFalse((pasta / "perfil.json").exists())  # o resumo nunca grava o perfil
                self.assertIn("confirmo", resumo["proximo_passo"])
                self.assertEqual(rodar("montar", "--pasta-dados", str(pasta))[0], 0)
                perfil, erros, avisos = validar_perfil.carregar(pasta / "perfil.json")
                self.assertEqual((erros, avisos), ([], []))

    def test_responder_fora_de_ordem_chega_ao_mesmo_perfil(self):
        todas = respostas("fornecedor_b2b")
        esperado, _, _ = montar_perfil.montar(todas, hoje=date(2026, 11, 1))
        chaves = [str(n) for n in range(1, 13)]
        for semente in range(5):
            embaralhadas = random.Random(semente).sample(chaves, len(chaves))
            parcial = {"versao": 1}
            for k in embaralhadas:
                parcial[k] = todas[k]
            perfil, erros, _ = montar_perfil.montar(parcial, hoje=date(2026, 11, 1))
            self.assertEqual(erros, [])
            self.assertEqual(perfil, esperado)

    def test_pergunta_7_e_a_unica_que_pode_ficar_sem_resposta(self):
        todas = respostas("agencia_de_sites")
        sem7 = {k: v for k, v in todas.items() if k != "7"}
        perfil, erros, _ = montar_perfil.montar(sem7)
        self.assertEqual((erros, perfil["cliente"]["exemplo"]), ([], ""))
        for numero in (1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12):
            faltando = {k: v for k, v in todas.items() if k != str(numero)}
            _, erros, _ = montar_perfil.montar(faltando)
            self.assertTrue(erros and f"pergunta {numero}" in erros[0], (numero, erros))


class TestConferenciaDeCadaResposta(unittest.TestCase):
    def erros_de(self, **mudancas):
        r = respostas("agencia_de_sites")
        for k, v in mudancas.items():
            r[k.removeprefix("p")] = v
        return montar_perfil.montar(r)

    def test_cada_resposta_ruim_diz_a_pergunta_e_o_que_fazer(self):
        casos = [
            ({"p1": ""}, "Pergunta 1"), ({"p1": "x" * 301}, "Pergunta 1"), ({"p1": 5}, "Pergunta 1"),
            ({"p2": {"nome": "", "empresa": "x"}}, "Pergunta 2"), ({"p2": "só o nome"}, "Pergunta 2"),
            ({"p3": {"tipos": [], "porte": "pequeno"}}, "Pergunta 3"), ({"p3": {"tipos": ["padaria"], "porte": "gigante"}}, "Pergunta 3"),
            ({"p4": {"regioes": ["Brasília"], "atendimento": "remoto"}}, "Pergunta 4"),
            ({"p4": {"regioes": ["Brasília-ZZ"], "atendimento": "remoto"}}, "Pergunta 4"),
            ({"p4": {"regioes": ["Brasília-DF"], "atendimento": "voando"}}, "Pergunta 4"),
            ({"p5": {"regras": []}}, "Pergunta 5"), ({"p5": {"regras": ["nao_existe"]}}, "Pergunta 5"), ({"p5": ["sem_site"]}, "Pergunta 5"),
            ({"p6": {"evitar": ["concorrente"], "concorrentes": []}}, "Pergunta 6"),
            ({"p6": {"evitar": ["categoria"], "categorias": []}}, "Pergunta 6"),
            ({"p6": {"evitar": [], "concorrentes": ["Fulano"]}}, "Pergunta 6"),
            ({"p6": {"evitar": ["nao_existe"]}}, "Pergunta 6"),
            ({"p8": []}, "Pergunta 8"), ({"p8": ["pombo"]}, "Pergunta 8"), ({"p9": "gritando"}, "Pergunta 9"),
            ({"p10": ""}, "Pergunta 10"), ({"p10": "x" * 121}, "Pergunta 10"), ({"p11": "muitos"}, "Pergunta 11"),
            ({"p12": {"resposta": "sim", "detalhe": ""}}, "Pergunta 12"), ({"p12": {"resposta": "talvez"}}, "Pergunta 12"),
        ]
        for mudanca, esperado in casos:
            with self.subTest(mudanca):
                perfil, erros, _ = self.erros_de(**mudanca)
                self.assertEqual(perfil, {}, "um perfil com erro nunca é montado")
                self.assertTrue(erros)
                self.assertTrue(any(e.startswith(esperado) for e in erros), erros)
                for e in erros:
                    self.assertNotIn("—", e)
                    self.assertNotIn("–", e)

    def test_documento_e_cartao_nao_entram_no_perfil(self):
        for texto in ("Meu CPF é 123.456.789-09", "cartão 4111 1111 1111 1111", "pague no 4111-1111-1111-1111"):
            perfil, erros, _ = self.erros_de(p1=texto)
            self.assertEqual(perfil, {})
            self.assertIn("documento ou um número de cartão", erros[0])
        perfil, erros, _ = self.erros_de(p1="Atendo pelo (61) 99999-0001 e pelo 61999990001")
        self.assertEqual(erros, [])  # telefone não é documento

    def test_regioes_escritas_de_varios_jeitos(self):
        for escrito, esperado in (("brasília - df", "Brasília-DF"), ("Brasília/df", "Brasília-DF"), ("Brasília,DF", "Brasília-DF"),
                                  ("  Sobradinho -  df ", "Sobradinho-DF"), ("todo o brasil", "Todo o Brasil"),
                                  ("Embu-Guaçu - SP", "Embu-Guaçu-SP"), ("são josé dos campos/sp", "São José dos Campos-SP"),
                                  ("EMBU-GUAÇU, sp", "Embu-Guaçu-SP"), ("Rio de Janeiro - RJ", "Rio de Janeiro-RJ"),
                                  ("sTa. Maria - RS", "sTa. Maria-RS")):
            self.assertEqual(montar_perfil.normalizar_regiao(escrito), esperado, escrito)
        for ruim in ("Brasília", "", "-DF", "Brasília-XX", "DF"):
            self.assertIsNone(montar_perfil.normalizar_regiao(ruim), ruim)
        perfil, erros, _ = self.erros_de(p4={"regioes": ["brasília - df", "Brasília-DF", "BRASÍLIA/DF"], "atendimento": "ambos"})
        self.assertEqual((erros, perfil["cliente"]["regioes"]), ([], ["Brasília-DF"]))  # o mesmo lugar escrito de três jeitos vira um só

    def test_nada_marcado_em_evitar_e_valido(self):
        perfil, erros, _ = self.erros_de(p6={"evitar": []})
        self.assertEqual((erros, perfil["exclusoes"]), ([], []))

    def test_texto_com_caractere_de_controle_e_espacos_a_mais_fica_limpo(self):
        perfil, erros, _ = self.erros_de(p1="  Sites \x00 e\t\tautomações \n para negócios  ")
        self.assertEqual(erros, [])
        self.assertEqual(perfil["negocio"]["oferta"], "Sites e automações para negócios")

    def test_a_lista_pode_chegar_como_texto_separado_por_virgula(self):
        perfil, erros, _ = self.erros_de(p3={"tipos": "padaria, academia , padaria", "porte": "pequeno"})
        self.assertEqual((erros, perfil["cliente"]["tipos"]), ([], ["padaria", "academia"]))

    def test_chave_desconhecida_vira_aviso_no_estado_e_nao_atrapalha(self):
        r = respostas("agencia_de_sites")
        r["13"] = "uma pergunta que não existe"
        estado = montar_perfil.estado(r)
        self.assertTrue(any("\"13\"" in a for a in estado["avisos"]))
        self.assertEqual(montar_perfil.montar(r)[1], [])

    def test_estado_aponta_o_erro_de_uma_resposta_ja_gravada(self):
        r = {"versao": 1, "1": "Sites", "3": {"tipos": ["padaria"], "porte": "gigante"}}
        estado = montar_perfil.estado(r)
        self.assertEqual(estado["respondidas"], [1, 3])
        self.assertEqual(estado["proxima"], 2)
        self.assertTrue(any(e.startswith("Pergunta 3") for e in estado["erros"]))

    def test_as_respostas_nao_sao_alteradas_pelo_script(self):
        r = respostas("fornecedor_b2b")
        copia = copy.deepcopy(r)
        montar_perfil.montar(r)
        montar_perfil.estado(r)
        self.assertEqual(r, copia)


class TestGravacaoELinhaDeComando(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self._tmp.cleanup)
        self.pasta = Path(self._tmp.name)

    def gravar_respostas(self, nome="agencia_de_sites"):
        (self.pasta / "respostas.json").write_text(json.dumps(respostas(nome), ensure_ascii=False), encoding="utf-8")

    def test_sem_respostas_o_estado_diz_que_falta_tudo(self):
        codigo, saida = rodar("estado", "--pasta-dados", str(self.pasta))
        self.assertEqual((codigo, saida["proxima"], saida["respondidas"]), (0, 1, []))
        self.assertEqual(saida["faltam"], [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12])

    def test_montar_incompleto_nao_grava_nada_e_diz_o_que_falta(self):
        (self.pasta / "respostas.json").write_text(json.dumps({"1": "Sites"}), encoding="utf-8")
        codigo, saida = rodar("montar", "--pasta-dados", str(self.pasta))
        self.assertEqual(codigo, 1)
        self.assertFalse(saida["ok"])
        self.assertIn("Ainda faltam respostas", saida["erros"][0])
        self.assertEqual(saida["faltam"][0], 2)
        self.assertFalse((self.pasta / "perfil.json").exists())

    def test_arquivo_de_respostas_quebrado_diz_a_linha(self):
        (self.pasta / "respostas.json").write_text('{"1": "x",\n "2": ', encoding="utf-8")
        codigo, saida = rodar("estado", "--pasta-dados", str(self.pasta))
        self.assertEqual(codigo, 1)
        self.assertIn("não é um JSON válido", saida["erros"][0])

    def test_montar_grava_o_perfil_inteiro_e_sem_arquivo_temporario(self):
        self.gravar_respostas()
        codigo, saida = rodar("montar", "--pasta-dados", str(self.pasta))
        self.assertEqual((codigo, saida["ok"]), (0, True))
        self.assertEqual(sorted(p.name for p in self.pasta.iterdir()), ["perfil.json", "respostas.json"])
        perfil = json.loads((self.pasta / "perfil.json").read_text(encoding="utf-8"))
        self.assertEqual(perfil["versao"], 1)

    def test_nao_troca_um_perfil_que_ja_existe_sem_pedir_para_refazer(self):
        self.gravar_respostas()
        rodar("montar", "--pasta-dados", str(self.pasta))
        antes = (self.pasta / "perfil.json").read_bytes()
        self.gravar_respostas("fornecedor_b2b")
        codigo, saida = rodar("montar", "--pasta-dados", str(self.pasta))
        self.assertEqual((codigo, saida["ok"]), (1, False))
        self.assertIn("refazer perfil", saida["mensagem"])
        self.assertEqual((self.pasta / "perfil.json").read_bytes(), antes)
        self.assertFalse((self.pasta / "perfil.anterior.json").exists())

    def test_o_perfil_montado_entra_no_painel(self):
        """O servidor aceita exatamente o que o script gravou."""
        import http.client
        import threading
        from kit import servidor
        from testes.fixtures import GeoDeMentira, MotorDeMentira
        self.gravar_respostas("contabilidade_regulada")
        rodar("montar", "--pasta-dados", str(self.pasta))
        perfil = json.loads((self.pasta / "perfil.json").read_text(encoding="utf-8"))
        pasta_servidor = self.pasta / "servidor"
        srv = servidor.Servidor(porta=0, pasta_dados=pasta_servidor, motor=MotorDeMentira(), geo=GeoDeMentira(), token="t")
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
        self.addCleanup(lambda: (srv.shutdown(), srv.server_close()))
        con = http.client.HTTPConnection("127.0.0.1", srv.porta, timeout=10)
        con.request("PUT", "/api/perfil", json.dumps(perfil), {"Content-Type": "application/json", "X-Token": "t"})
        resposta = con.getresponse()
        self.assertEqual(resposta.status, 200, resposta.read())


class TestResumo(unittest.TestCase):
    def test_o_resumo_diz_tudo_que_foi_respondido(self):
        for nome in NOMES:
            with self.subTest(nome):
                r = respostas(nome)
                perfil, _, _ = montar_perfil.montar(r)
                texto = montar_perfil.resumo(perfil)
                for trecho in (r["1"], r["2"]["nome"], r["10"]):
                    self.assertIn(trecho, texto)
                for tipo in r["3"]["tipos"]:
                    self.assertIn(tipo, texto)
                self.assertIn("pontos", texto)
                self.assertNotIn("—", texto)
                self.assertNotIn("–", texto)
                self.assertNotIn("None", texto)
                self.assertNotIn("{", texto)

    def test_resumo_de_cada_caso_especial(self):
        b2b, _, _ = montar_perfil.montar(respostas("fornecedor_b2b"))
        texto = montar_perfil.resumo(b2b)
        self.assertIn("concorrentes (Embalagens Rivais e rival.exemplo.invalid)", texto)
        self.assertIn("categorias (igreja e escola)", texto)
        self.assertIn("WhatsApp e e-mail", texto)
        self.assertIn("Porte: qualquer", texto)
        reg, _, _ = montar_perfil.montar(respostas("contabilidade_regulada"))
        texto = montar_perfil.resumo(reg)
        self.assertIn("conselho de contabilidade (CRC)", texto)
        self.assertIn("o painel vai mostrar um aviso", texto)
        self.assertNotIn("da empresa", texto)  # sem empresa, o resumo não inventa uma
        self.assertNotIn("..", texto)
        ag, _, _ = montar_perfil.montar(respostas("agencia_de_sites"))
        self.assertNotIn("..", montar_perfil.resumo(ag))
        self.assertIn("não tem regras de publicidade", montar_perfil.resumo(ag))


if __name__ == "__main__":
    unittest.main()
