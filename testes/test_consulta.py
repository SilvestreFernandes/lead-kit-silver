import csv
import io
import unittest

from kit import banco, consulta, limpeza
from testes.fixtures import csv_texto, linha, perfil_ficticio


def montar(linhas=None):
    conn = banco.abrir()
    bid = banco.criar_busca(conn, "padaria", "Cidade Teste", "DF", "rapida", {}, False)
    leads = limpeza.ler_csv(csv_texto(linhas))[0]
    banco.salvar_leads(conn, bid, leads, "Cidade Teste", "DF", False)
    return conn, bid


def telefone_csv(telefone, **extra):
    l = limpeza.limpar_linha(linha(1, phone=telefone, **extra))
    return consulta.telefone_para_csv(l)


class TestFiltros(unittest.TestCase):
    def setUp(self):
        self.conn, self.bid = montar()
        self.addCleanup(self.conn.close)
        self.perfil = perfil_ficticio()
        self.todos = consulta.avaliar(self.conn, self.perfil)

    def nomes(self, **filtros):
        base = {"busca": None, "letras": None, "status": None, "texto": "", "excluidos": "nao"}
        base.update(filtros)
        return [r["lead"]["nome"] for r in consulta.filtrar(self.todos, base)]

    def test_padrao_esconde_excluidos(self):
        nomes = self.nomes()
        self.assertNotIn("Sem Telefone", nomes)
        self.assertNotIn("Café Rede", nomes)
        self.assertIn("Pão Sem Site", nomes)

    def test_so_excluidos_e_todos(self):
        self.assertEqual(set(self.nomes(excluidos="sim")),
                         {"Sem Telefone", "Café Rede", "Café Rede - Filial Norte", "CAFÉ REDE"})
        self.assertEqual(len(self.nomes(excluidos="todos")), 11)

    def test_por_letra(self):
        self.assertEqual(self.nomes(letras={"A"}), ["Pão Sem Site"])
        self.assertIn("Padaria Completa", self.nomes(letras={"B"}))

    def test_por_status(self):
        lid = next(r["lead"]["id"] for r in self.todos if r["lead"]["nome"] == "Reserva")
        banco.atualizar_lead(self.conn, lid, status="contatado")
        self.todos = consulta.avaliar(self.conn, self.perfil)
        self.assertEqual(self.nomes(status={"contatado"}), ["Reserva"])

    def test_texto_acha_nome_sem_acento_categoria_e_telefone(self):
        self.assertEqual(self.nomes(texto="pao sem"), ["Pão Sem Site"])
        self.assertEqual(self.nomes(texto="restaurante"), ["Reserva"])
        self.assertEqual(self.nomes(texto="99999-0001"), ["Pão Sem Site"])
        self.assertEqual(self.nomes(texto="zzz"), [])

    def test_por_busca(self):
        outra = banco.criar_busca(self.conn, "x", "C", "DF", "rapida", {}, False)
        banco.salvar_leads(self.conn, outra, limpeza.ler_csv(csv_texto())[0][:2], "C", "DF", False)
        ids = banco.ids_da_busca(self.conn, outra)
        base = {"busca": outra, "letras": None, "status": None, "texto": "", "excluidos": "todos"}
        self.assertEqual(len(consulta.filtrar(self.todos, base, ids)), 2)

    def test_ler_filtros_validos_e_invalidos(self):
        f = consulta.ler_filtros({"letra": ["a,b"], "status": ["novo"], "q": [" pao "], "busca": ["3"],
                                  "excluidos": ["todos"]})
        self.assertEqual((f["letras"], f["status"], f["texto"], f["busca"], f["excluidos"]),
                         ({"A", "B"}, {"novo"}, "pao", 3, "todos"))
        for ruim in ({"letra": ["Z"]}, {"status": ["vendido"]}, {"busca": ["x"]}, {"excluidos": ["talvez"]}):
            with self.assertRaises(consulta.FiltroInvalido):
                consulta.ler_filtros(ruim)

    def test_detalhe_traz_motivos_frase_e_mensagem(self):
        r = next(r for r in self.todos if r["lead"]["nome"] == "Pão Sem Site")
        d = consulta.detalhe(r, self.perfil)
        self.assertIn("sem site (+3)", d["motivos"])
        self.assertEqual(d["frase_do_motivo"], "não achei um site no perfil do Google Maps")
        self.assertIn("não achei um site", d["mensagens"]["whatsapp"]["texto"])
        self.assertEqual(d["mensagem_editada"], "")

    def test_resumo_nao_traz_dados_a_mais(self):
        r = self.todos[0]
        self.assertNotIn("emails", consulta.resumo(r))
        self.assertNotIn("mensagens", consulta.resumo(r))


class TestProtecaoDoCsv(unittest.TestCase):
    def test_proteger_marca_so_o_que_vira_formula(self):
        for perigoso in ("=1+1", "+55", "-5", "@soma", "\t=x", "\r=x"):
            self.assertEqual(consulta.proteger(perigoso), "'" + perigoso)
        for seguro in ("Padaria", "", "a=b", "(61) 3333-0000", "5-2"):
            self.assertEqual(consulta.proteger(seguro), seguro)
        self.assertEqual(consulta.proteger(None), "")

    # O que a protecao faz com telefones que comecam com +
    def test_telefone_com_mais_55_vira_formato_nacional_sem_mais(self):
        self.assertEqual(telefone_csv("+55 61 98888-0003"), "(61) 98888-0003")
        self.assertEqual(telefone_csv("+55 (61) 3387-2235"), "(61) 3387-2235")

    def test_telefone_nacional_nao_muda(self):
        self.assertEqual(telefone_csv("(61) 99322-4592"), "(61) 99322-4592")
        self.assertEqual(telefone_csv("(61) 3387-2235"), "(61) 3387-2235")

    def test_telefone_de_fora_do_brasil_nao_e_reformatado_e_ganha_apostrofo(self):
        # 11 digitos como um celular brasileiro, mas e dos EUA: nao pode virar "(12) 02555-0100"
        self.assertEqual(telefone_csv("+1 202 555 0100"), "'+1 202 555 0100")

    def test_telefone_estranho_so_ganha_protecao(self):
        self.assertEqual(telefone_csv("+55 61 123"), "'+55 61 123")
        self.assertEqual(telefone_csv("=cmd|' /C calc'!A0"), "'=cmd|' /C calc'!A0")
        self.assertEqual(telefone_csv(""), "")

    def test_nenhum_telefone_exportado_comeca_com_caractere_perigoso_sem_protecao(self):
        for tel in ("+55 61 98888-0003", "+1 202 555 0100", "+55 61 123", "(61) 3333-0000", "@x"):
            saida = telefone_csv(tel)
            self.assertFalse(saida.startswith(consulta.PERIGOSOS), saida)


class TestExportacao(unittest.TestCase):
    def setUp(self):
        self.conn, _ = montar([
            linha(1, title="=HYPERLINK(\"http://x.invalid\")", phone="+55 61 98888-0003",
                  review_count="80", review_rating="4.7", website=""),
            linha(2, title="Normal", phone="(61) 3333-0000", latitude="-15.5"),
        ])
        self.addCleanup(self.conn.close)
        self.perfil = perfil_ficticio()
        lid = next(l["id"] for l in banco.todos_os_leads(self.conn) if l["nome"] == "Normal")
        banco.atualizar_lead(self.conn, lid, anotacao="@ligar", mensagem_editada="-oi")

    def texto(self):
        return consulta.exportar_csv(consulta.avaliar(self.conn, self.perfil))

    def linhas(self):
        return list(csv.reader(io.StringIO(self.texto().lstrip("﻿"))))

    def test_bom_utf8_e_cabecalho(self):
        t = self.texto()
        self.assertTrue(t.startswith("﻿"))
        self.assertEqual(self.linhas()[0], consulta.CABECALHO)

    def test_formula_no_nome_e_neutralizada(self):
        nomes = [l[2] for l in self.linhas()[1:]]
        self.assertIn("'=HYPERLINK(\"http://x.invalid\")", nomes)

    def test_anotacao_e_mensagem_editada_protegidas(self):
        normal = next(l for l in self.linhas() if l[2] == "Normal")
        self.assertEqual((normal[16], normal[17]), ("'@ligar", "'-oi"))

    def test_telefone_mais_55_sai_sem_mais(self):
        tel = [l[7] for l in self.linhas()[1:]]
        self.assertIn("(61) 98888-0003", tel)
        self.assertFalse(any(t.startswith("+") for t in tel))

    def test_numeros_ficam_numeros(self):
        pao = next(l for l in self.linhas() if "HYPERLINK" in l[2])
        self.assertEqual((pao[11], pao[12]), ("80", "4.7"))

    def test_so_os_leads_passados_sao_exportados(self):
        todos = consulta.avaliar(self.conn, self.perfil)
        t = consulta.exportar_csv(todos[:1]).lstrip("﻿")
        self.assertEqual(len(list(csv.reader(io.StringIO(t)))), 2)


if __name__ == "__main__":
    unittest.main()
