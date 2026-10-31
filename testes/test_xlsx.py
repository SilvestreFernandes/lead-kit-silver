"""Testes da exportacao .xlsx: estrutura, estilos, texto puro e links. Sem Excel: le o zip e o XML."""
import io
import unittest
import xml.etree.ElementTree as ET
import zipfile

from kit import banco, consulta, limpeza, xlsx
from testes.fixtures import csv_texto, linha, perfil_ficticio

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "rel": "http://schemas.openxmlformats.org/package/2006/relationships"}


class Planilha:
    """Leitor minimo: abre o zip, confere que todo XML e bem formado e devolve as celulas."""

    def __init__(self, dados):
        self.zip = zipfile.ZipFile(io.BytesIO(dados))
        self.xml = {n: ET.fromstring(self.zip.read(n)) for n in self.zip.namelist()}
        self.folha = self.xml["xl/worksheets/sheet1.xml"]

    def celulas(self):
        """{'A1': (valor, estilo, tipo)}"""
        saida = {}
        for c in self.folha.iterfind(".//m:c", NS):
            t = c.find("m:is/m:t", NS)
            v = c.find("m:v", NS)
            valor = t.text if t is not None else (v.text if v is not None else None)
            saida[c.get("r")] = (valor, int(c.get("s")), c.get("t"))
        return saida

    def linha(self, n):
        return [(c.get("r"), c) for c in self.folha.iterfind(f".//m:row[@r='{n}']/m:c", NS)]

    def cabecalho(self):
        return [self.celulas()[ref][0] for ref, _ in self.linha(1)]

    def valor(self, coluna_titulo, n):
        cab = self.cabecalho()
        i = cab.index(coluna_titulo)
        return self.celulas()[f"{xlsx.letra_da_coluna(i)}{n}"]

    def links(self):
        rels = self.xml.get("xl/worksheets/_rels/sheet1.xml.rels")
        alvo = {r.get("Id"): r.get("Target") for r in rels} if rels is not None else {}
        return {h.get("ref"): alvo[h.get("{%s}id" % NS["r"])]
                for h in self.folha.iterfind(".//m:hyperlink", NS)}


def montar(linhas=None, editar=None):
    conn = banco.abrir()
    bid = banco.criar_busca(conn, "padaria", "Cidade Teste", "DF", "rapida", {}, False)
    banco.salvar_leads(conn, bid, limpeza.ler_csv(csv_texto(linhas))[0], "Cidade Teste", "DF", False)
    if editar:
        editar(conn)
    perfil = perfil_ficticio()
    avaliados = consulta.avaliar(conn, perfil)
    conn.close()
    return avaliados, perfil


def exportar(linhas=None, editar=None, excluidos=False):
    avaliados, perfil = montar(linhas, editar)
    if not excluidos:
        avaliados = [r for r in avaliados if not r["excluido_por"]]
    return Planilha(consulta.exportar_xlsx(avaliados, perfil)), avaliados


class TestGeradorBasico(unittest.TestCase):
    def test_pacote_tem_as_partes_obrigatorias_e_o_primeiro_arquivo_e_o_de_tipos(self):
        dados = xlsx.gerar([xlsx.Coluna("A")], [["x"]])
        z = zipfile.ZipFile(io.BytesIO(dados))
        self.assertEqual(z.namelist()[0], "[Content_Types].xml")
        for parte in ("_rels/.rels", "xl/workbook.xml", "xl/_rels/workbook.xml.rels", "xl/styles.xml",
                      "xl/worksheets/sheet1.xml", "docProps/core.xml", "docProps/app.xml"):
            self.assertIn(parte, z.namelist())
        self.assertIsNone(z.testzip())

    def test_todo_xml_e_bem_formado(self):
        p = Planilha(xlsx.gerar([xlsx.Coluna("A")], [["x"]]))
        self.assertTrue(p.xml)

    def test_estilos_referenciados_existem(self):
        p, _ = exportar()
        total = len(p.xml["xl/styles.xml"].find("m:cellXfs", NS))
        usados = {estilo for _, estilo, _ in p.celulas().values()}
        self.assertTrue(usados)
        self.assertLess(max(usados), total)
        self.assertEqual(total, len(xlsx.ESTILOS))

    def test_letra_da_coluna(self):
        self.assertEqual([xlsx.letra_da_coluna(i) for i in (0, 25, 26, 27, 51, 52)],
                         ["A", "Z", "AA", "AB", "AZ", "BA"])

    def test_linha_com_numero_errado_de_colunas(self):
        with self.assertRaises(ValueError):
            xlsx.gerar([xlsx.Coluna("A"), xlsx.Coluna("B")], [["so um"]])

    def test_planilha_vazia_continua_valida(self):
        p = Planilha(xlsx.gerar([xlsx.Coluna("A"), xlsx.Coluna("B")], []))
        self.assertEqual(p.folha.find("m:autoFilter", NS).get("ref"), "A1:B1")


class TestAparenciaDeRelatorio(unittest.TestCase):
    def setUp(self):
        self.p, self.avaliados = exportar()

    def test_cabecalho_em_portugues_na_ordem_pedida(self):
        self.assertEqual(self.p.cabecalho(), [
            "Negócio", "Nota", "Pontos", "Motivos", "Categoria", "Telefone", "WhatsApp", "Site",
            "Endereço", "Avaliação no Maps", "Nº de avaliações", "Status", "Anotação", "Mensagem"])

    def test_cabecalho_em_destaque(self):
        estilos = {self.p.celulas()[ref][1] for ref, _ in self.p.linha(1)}
        self.assertEqual(estilos, {xlsx.ESTILOS["cabecalho"]})
        fonte_id = int(self.p.xml["xl/styles.xml"].find("m:cellXfs", NS)[1].get("fontId"))
        fonte = self.p.xml["xl/styles.xml"].find("m:fonts", NS)[fonte_id]
        self.assertIsNotNone(fonte.find("m:b", NS))
        self.assertEqual(self.p.folha.find(".//m:row[@r='1']", NS).get("customHeight"), "1")

    def test_primeira_linha_congelada(self):
        pane = self.p.folha.find(".//m:pane", NS)
        self.assertEqual((pane.get("ySplit"), pane.get("state"), pane.get("topLeftCell")),
                         ("1", "frozen", "A2"))

    def test_filtro_ligado_cobrindo_todos_os_dados(self):
        n = len(self.avaliados) + 1
        ultima = xlsx.letra_da_coluna(len(self.p.cabecalho()) - 1)
        self.assertEqual(self.p.folha.find("m:autoFilter", NS).get("ref"), f"A1:{ultima}{n}")
        nomes = {d.get("name"): d.text for d in self.p.xml["xl/workbook.xml"].iterfind(".//m:definedName", NS)}
        self.assertEqual(nomes["_xlnm._FilterDatabase"], f"'Leads'!$A$1:${ultima}${n}")
        self.assertEqual(nomes["_xlnm.Print_Titles"], "'Leads'!$1:$1")

    def test_largura_de_coluna_ajustada_e_limitada(self):
        larguras = [float(c.get("width")) for c in self.p.folha.iterfind(".//m:col", NS)]
        self.assertEqual(len(larguras), len(self.p.cabecalho()))
        self.assertTrue(all(8 <= w <= 64 for w in larguras), larguras)
        cab = self.p.cabecalho()
        self.assertEqual(larguras[cab.index("Mensagem")], 64)  # texto longo bate no limite

    def test_titulo_cabe_inteiro_com_o_botao_do_filtro(self):
        """No Google Planilhas o botao do filtro come espaco do titulo: 'Nota' virava 'Not a'."""
        cab = self.p.cabecalho()
        larguras = [float(c.get("width")) for c in self.p.folha.iterfind(".//m:col", NS)]
        for titulo, largura in zip(cab, larguras):
            self.assertGreaterEqual(largura, xlsx.largura_minima_do_titulo(titulo), titulo)
            for palavra in titulo.split():
                self.assertGreaterEqual(largura, len(palavra) + xlsx.FOLGA_DO_FILTRO, (titulo, palavra))
        self.assertGreaterEqual(larguras[cab.index("Nota")], len("Nota") + 12)
        self.assertGreaterEqual(larguras[cab.index("Pontos")], len("Pontos") + 12)
        self.assertGreaterEqual(larguras[cab.index("Status")], len("Status") + 12)

    def test_site_aparece_curto_e_o_link_continua_inteiro(self):
        self.assertEqual(consulta.site_para_exibir("https://www.exemplo.invalid/"), "exemplo.invalid")
        self.assertEqual(consulta.site_para_exibir("http://loja.invalid/menu?a=1"), "loja.invalid/menu?a=1")
        p, _ = exportar([linha(1, title="Com Site", website="https://www.bom.invalid/menu/", phone="(61) 3333-0001")], excluidos=True)
        col = xlsx.letra_da_coluna(p.cabecalho().index("Site"))
        self.assertEqual(p.valor("Site", 2)[0], "bom.invalid/menu")
        self.assertEqual(p.links()[f"{col}2"], "https://www.bom.invalid/menu/")

    def test_site_nao_quebra_linha_e_a_coluna_tem_cerca_de_30(self):
        """URL sem espaco nao quebra no Google Planilhas: a celula corta o texto e o link completo fica."""
        xfs = self.p.xml["xl/styles.xml"].findall(".//m:cellXfs/m:xf", NS)
        self.assertIsNone(xfs[xlsx.ESTILOS["link"]].find("m:alignment", NS).get("wrapText"))
        cab = self.p.cabecalho()
        larguras = [float(c.get("width")) for c in self.p.folha.iterfind(".//m:col", NS)]
        self.assertLessEqual(larguras[cab.index("Site")], 30)

    def test_cor_na_letra_da_nota(self):
        notas = {}
        for n in range(2, len(self.avaliados) + 2):
            letra, estilo, _ = self.p.valor("Nota", n)
            notas.setdefault(letra, set()).add(estilo)
        self.assertEqual(notas["A"], {xlsx.ESTILOS["nota_a"]})
        self.assertEqual(notas["B"], {xlsx.ESTILOS["nota_b"]})
        self.assertEqual(notas["C"], {xlsx.ESTILOS["nota_c"]})
        estilos = self.p.xml["xl/styles.xml"]
        fills = {k: int(estilos.find("m:cellXfs", NS)[xlsx.ESTILOS[k]].get("fillId"))
                 for k in ("nota_a", "nota_b", "nota_c")}
        self.assertEqual(len(set(fills.values())), 3)  # tres cores diferentes

    def test_avaliacao_e_numeros_sao_numeros_de_verdade(self):
        letra, pts_estilo, tipo = self.p.valor("Pontos", 2)
        self.assertIsNone(tipo)  # sem t="inlineStr": e numero
        self.assertEqual(self.p.valor("Avaliação no Maps", 2)[1], xlsx.ESTILOS["decimal"])
        self.assertEqual(self.p.valor("Nº de avaliações", 2)[1], xlsx.ESTILOS["inteiro"])

    def test_orientacao_paisagem_ajustada_a_largura(self):
        s = self.p.folha.find("m:pageSetup", NS)
        self.assertEqual((s.get("orientation"), s.get("fitToWidth"), s.get("fitToHeight")),
                         ("landscape", "1", "0"))
        self.assertEqual(self.p.folha.find(".//m:sheetView", NS).get("showGridLines"), "0")

    def test_primeiro_lead_e_o_melhor(self):
        self.assertEqual(self.p.valor("Negócio", 2)[0], "Pão Sem Site")
        self.assertEqual(self.p.valor("Nota", 2)[0], "A")
        self.assertIn("sem site (+3)", self.p.valor("Motivos", 2)[0])

    def test_coluna_de_exclusao_so_aparece_quando_ha_excluidos(self):
        self.assertNotIn("Excluído por", self.p.cabecalho())
        com, _ = exportar(excluidos=True)
        self.assertIn("Excluído por", com.cabecalho())
        motivos = [com.valor("Excluído por", n)[0] for n in range(2, 13)]
        self.assertIn("sem telefone", motivos)


class TestTextoPuroSemFormulas(unittest.TestCase):
    def test_nenhuma_formula_no_arquivo(self):
        perigosos = [
            linha(1, title='=HYPERLINK("http://x.invalid","clique")', phone="+55 61 98888-0001"),
            linha(2, title="+1+1", address="-2+3", category="@SOMA(A1)", website=""),
            linha(3, title="\t=cmd", phone="=1+1"),
        ]
        p, _ = exportar(perigosos, excluidos=True)
        for nome, raiz in p.xml.items():
            textos = ET.tostring(raiz, encoding="unicode")
            self.assertNotIn("<f>", textos, nome)
            self.assertNotIn("<f ", textos, nome)
        celulas = p.celulas()
        nomes = {v for v, _, t in celulas.values()}
        self.assertIn('=HYPERLINK("http://x.invalid","clique")', nomes)  # texto, sem apostrofo
        self.assertIn("+1+1", nomes)
        self.assertIn("@SOMA(A1)", nomes)
        nome_cel = next(c for c in celulas.values() if c[0] == '=HYPERLINK("http://x.invalid","clique")')
        self.assertEqual(nome_cel[2], "inlineStr")

    def test_anotacao_e_mensagem_editada_com_formula_ficam_como_texto(self):
        def editar(conn):
            lid = conn.execute("SELECT id FROM leads WHERE nome='Pão Sem Site'").fetchone()[0]
            banco.atualizar_lead(conn, lid, anotacao="=A1+B1", mensagem_editada="-oi {nome}")
        p, _ = exportar(editar=editar)
        self.assertEqual(p.valor("Anotação", 2)[0], "=A1+B1")
        self.assertEqual(p.valor("Mensagem", 2)[0], "-oi {nome}")

    def test_caracteres_especiais_de_xml_sobrevivem(self):
        p, _ = exportar([linha(1, title='Café & "Bolos" <Gourmet> \'D\'Ouro\'', phone="(61) 99999-0001")])
        self.assertEqual(p.valor("Negócio", 2)[0], 'Café & "Bolos" <Gourmet> \'D\'Ouro\'')

    def test_caracteres_de_controle_sao_removidos(self):
        p, _ = exportar([linha(1, title="Pa\x00da\x0bria\x1f Boa")])
        self.assertEqual(p.valor("Negócio", 2)[0], "Padaria Boa")

    def test_texto_enorme_e_cortado_no_limite_do_excel(self):
        p, _ = exportar([linha(1, address="x" * 40000)])
        self.assertEqual(len(p.valor("Endereço", 2)[0]), xlsx.LIMITE_TEXTO)
        self.assertLess(xlsx.LIMITE_TEXTO, 32767)

    def test_telefone_com_mais_sai_sem_apostrofo(self):
        p, _ = exportar([linha(1, phone="+55 61 98888-0003"), linha(2, phone="+1 202 555 0100")], excluidos=True)
        fones = {p.valor("Telefone", n)[0] for n in (2, 3)}
        self.assertEqual(fones, {"(61) 98888-0003", "+1 202 555 0100"})


class TestLinks(unittest.TestCase):
    def test_whatsapp_clicavel_so_para_celular(self):
        p, _ = exportar([
            linha(1, title="Celular", phone="(61) 99999-0001", website=""),
            linha(2, title="Fixo", phone="(61) 3333-0002", website=""),
        ])
        links = p.links()
        cab = p.cabecalho()
        col = xlsx.letra_da_coluna(cab.index("WhatsApp"))
        nomes = {p.valor("Negócio", n)[0]: n for n in (2, 3)}
        url = links[f"{col}{nomes['Celular']}"]
        self.assertTrue(url.startswith("https://wa.me/5561999990001?text="))
        self.assertNotIn(f"{col}{nomes['Fixo']}", links)
        self.assertEqual(p.valor("WhatsApp", nomes["Celular"])[0], "Abrir WhatsApp")
        self.assertEqual(p.valor("WhatsApp", nomes["Celular"])[1], xlsx.ESTILOS["link"])
        self.assertIsNone(p.valor("WhatsApp", nomes["Fixo"])[0])

    def test_link_leva_a_mensagem_codificada(self):
        p, _ = exportar([linha(1, title="Pão & Cia", phone="(61) 99999-0001", website="")])
        url = next(iter(p.links().values()))
        self.assertIn("Pão%20%26%20Cia".replace("ã", "%C3%A3"), url)
        self.assertNotIn(" ", url)
        self.assertNotIn("{", url)

    def test_link_whatsapp_funcao(self):
        celular = limpeza.limpar_linha(linha(1, phone="+55 61 98888-0003"))
        fixo = limpeza.limpar_linha(linha(1, phone="(61) 3333-0000"))
        longe = limpeza.limpar_linha(linha(1, phone="+1 202 555 0100"))
        self.assertEqual(consulta.link_whatsapp(celular), "https://wa.me/5561988880003")
        self.assertEqual(consulta.link_whatsapp(celular, "oi"), "https://wa.me/5561988880003?text=oi")
        self.assertIsNone(consulta.link_whatsapp(fixo, "oi"))
        self.assertIsNone(consulta.link_whatsapp(longe, "oi"))

    def test_mensagem_muito_longa_deixa_o_link_sem_texto(self):
        celular = limpeza.limpar_linha(linha(1, phone="(61) 99999-0001"))
        self.assertEqual(consulta.link_whatsapp(celular, "ã" * 400), "https://wa.me/5561999990001")

    def test_site_vira_link_so_se_for_http(self):
        p, _ = exportar([
            linha(1, title="Bom", website="https://bom.invalid/menu?a=1&b=2", phone="(61) 3333-0001"),
            linha(2, title="Ruim", website="javascript:alert(1)", phone="(61) 3333-0002"),
            linha(3, title="Arquivo", website="file:///C:/Windows/win.ini", phone="(61) 3333-0003"),
        ], excluidos=True)
        links = p.links()
        col = xlsx.letra_da_coluna(p.cabecalho().index("Site"))
        por_nome = {p.valor("Negócio", n)[0]: n for n in (2, 3, 4)}
        self.assertEqual(links[f"{col}{por_nome['Bom']}"], "https://bom.invalid/menu?a=1&b=2")
        self.assertNotIn(f"{col}{por_nome['Ruim']}", links)
        self.assertNotIn(f"{col}{por_nome['Arquivo']}", links)
        self.assertEqual(p.valor("Site", por_nome["Ruim"])[0], "javascript:alert(1)")  # aparece como texto

    def test_nenhum_alvo_de_link_e_perigoso(self):
        p, _ = exportar()
        for alvo in p.links().values():
            self.assertTrue(alvo.startswith(("https://", "http://")), alvo)
            self.assertLessEqual(len(alvo), xlsx.LIMITE_URL)

    def test_links_como_hiperlinks_de_verdade_e_externos(self):
        p, _ = exportar([linha(1, phone="(61) 99999-0001")])
        rels = p.xml["xl/worksheets/_rels/sheet1.xml.rels"]
        for r in rels:
            self.assertEqual(r.get("TargetMode"), "External")
            self.assertTrue(r.get("Type").endswith("/hyperlink"))

    def test_url_longa_demais_e_descartada(self):
        self.assertIsNone(xlsx.link_valido("https://x.invalid/" + "a" * 3000))
        self.assertIsNone(xlsx.link_valido(""))
        self.assertIsNone(xlsx.link_valido("ftp://x.invalid"))
        self.assertEqual(xlsx.link_valido(" https://x.invalid "), "https://x.invalid")


class TestMensagemNaPlanilha(unittest.TestCase):
    def test_mensagem_do_modelo_preenchida(self):
        p, _ = exportar()
        msg = p.valor("Mensagem", 2)[0]
        self.assertIn("Notei que não achei um site no perfil do Google Maps.", msg)
        self.assertNotIn("{", msg)

    def test_mensagem_editada_vale_mais_que_o_modelo(self):
        def editar(conn):
            lid = conn.execute("SELECT id FROM leads WHERE nome='Pão Sem Site'").fetchone()[0]
            banco.atualizar_lead(conn, lid, mensagem_editada="Minha versão")
        p, _ = exportar(editar=editar)
        self.assertEqual(p.valor("Mensagem", 2)[0], "Minha versão")
        self.assertIn("Minha%20vers", next(iter(p.links().values())))


if __name__ == "__main__":
    unittest.main()
