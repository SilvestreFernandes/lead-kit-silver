"""Gera planilhas .xlsx so com a biblioteca padrao (zipfile e XML escrito a mao).

Todo texto e gravado como texto puro (inlineStr), nunca como formula: um nome que comece com "="
aparece na celula exatamente como veio. Links viram hiperlinks de verdade, nao formulas HYPERLINK.
Recursos: cabecalho em destaque, largura de coluna ajustada, primeira linha congelada, filtro
ligado, cor na letra da nota, impressao em paisagem com o cabecalho repetido.
"""
import io
import re
import zipfile
from datetime import datetime, timezone
from urllib.parse import urlsplit
from xml.sax.saxutils import escape, quoteattr

LIMITE_TEXTO = 32000       # o Excel aceita 32767 caracteres por celula
LIMITE_URL = 2000          # o Excel aceita links de ate 2079 caracteres
PROIBIDOS_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")

# Indices em xl/styles.xml (cellXfs). Se mudar a ordem la, mude aqui.
ESTILOS = {"padrao": 0, "cabecalho": 1, "texto": 2, "quebra": 3, "inteiro": 4, "decimal": 5,
           "nota_a": 6, "nota_b": 7, "nota_c": 8, "link": 9, "centro": 10}

NS_PLANILHA = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL_DOC = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
TIPO_LINK = NS_REL_DOC + "/hyperlink"


class Coluna:
    def __init__(self, titulo, estilo="texto", largura_max=40, largura_fixa=None):
        self.titulo, self.estilo = titulo, estilo
        self.largura_max, self.largura_fixa = largura_max, largura_fixa


class Celula:
    """Valor (texto ou numero) com estilo e link opcionais."""

    def __init__(self, valor, estilo=None, link=None):
        self.valor, self.estilo, self.link = valor, estilo, link


def limpar_texto(texto):
    return PROIBIDOS_XML.sub("", str(texto))[:LIMITE_TEXTO]


def link_valido(url):
    """So http e https, e curto o bastante pro Excel. Nada de file:, javascript: e afins."""
    url = (url or "").strip()
    if not url or len(url) > LIMITE_URL:
        return None
    partes = urlsplit(url)
    return url if partes.scheme in ("http", "https") and partes.netloc else None


def letra_da_coluna(indice):
    """0 -> A, 25 -> Z, 26 -> AA."""
    nome = ""
    indice += 1
    while indice:
        indice, resto = divmod(indice - 1, 26)
        nome = chr(65 + resto) + nome
    return nome


def _largura(coluna, valores):
    if coluna.largura_fixa:
        return coluna.largura_fixa
    maior = len(coluna.titulo) + 3
    for v in valores:
        if isinstance(v, str) and v:
            maior = max(maior, max(len(linha) for linha in v.split("\n")) + 2)
    return min(maior, coluna.largura_max)


ESTILOS_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="{NS_PLANILHA}">
<numFmts count="1"><numFmt numFmtId="164" formatCode="0.0"/></numFmts>
<fonts count="6">
<font><sz val="11"/><color rgb="FF1F2933"/><name val="Calibri"/><family val="2"/></font>
<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/><family val="2"/></font>
<font><b/><sz val="11"/><color rgb="FF006100"/><name val="Calibri"/><family val="2"/></font>
<font><b/><sz val="11"/><color rgb="FF9C5700"/><name val="Calibri"/><family val="2"/></font>
<font><b/><sz val="11"/><color rgb="FF595959"/><name val="Calibri"/><family val="2"/></font>
<font><u/><sz val="11"/><color rgb="FF0563C1"/><name val="Calibri"/><family val="2"/></font>
</fonts>
<fills count="6">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF2F3640"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFC6EFCE"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFFEB9C"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFE7E6E6"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="2">
<border><left/><right/><top/><bottom/><diagonal/></border>
<border><left/><right/><top/><bottom style="thin"><color rgb="FFD9DDE3"/></bottom><diagonal/></border>
</borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="11">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="left" vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="1" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="top"/></xf>
<xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="top"/></xf>
<xf numFmtId="0" fontId="2" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="top"/></xf>
<xf numFmtId="0" fontId="3" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="top"/></xf>
<xf numFmtId="0" fontId="4" fillId="5" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="top"/></xf>
<xf numFmtId="0" fontId="5" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="top"/></xf>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


def _celula_xml(ref, valor, estilo):
    s = ESTILOS[estilo]
    if valor is None or valor == "":
        return f'<c r="{ref}" s="{s}"/>'
    if isinstance(valor, bool):
        valor = "sim" if valor else "não"
    if isinstance(valor, (int, float)):
        return f'<c r="{ref}" s="{s}"><v>{valor}</v></c>'
    return f'<c r="{ref}" s="{s}" t="inlineStr"><is><t xml:space="preserve">{escape(limpar_texto(valor))}</t></is></c>'


def gerar(colunas, linhas, nome_aba="Leads", titulo_documento="Lead Kit Silver"):
    """Devolve os bytes de um .xlsx. `linhas` e uma lista de listas (valor ou Celula)."""
    n_col = len(colunas)
    ultima = letra_da_coluna(n_col - 1)
    n_lin = len(linhas) + 1

    # Normaliza as celulas e junta os textos de cada coluna para ajustar a largura.
    grade, textos = [], [[] for _ in colunas]
    for linha in linhas:
        if len(linha) != n_col:
            raise ValueError("Linha com número de colunas diferente do cabeçalho.")
        celulas = [c if isinstance(c, Celula) else Celula(c) for c in linha]
        grade.append(celulas)
        for i, c in enumerate(celulas):
            textos[i].append(c.valor)

    cols_xml = "".join(
        f'<col min="{i + 1}" max="{i + 1}" width="{_largura(c, textos[i])}" customWidth="1"/>'
        for i, c in enumerate(colunas))

    linhas_xml = ['<row r="1" ht="30" customHeight="1">' + "".join(
        _celula_xml(f"{letra_da_coluna(i)}1", c.titulo, "cabecalho") for i, c in enumerate(colunas)) + "</row>"]
    links = []
    for n, celulas in enumerate(grade, start=2):
        partes = []
        for i, c in enumerate(celulas):
            ref = f"{letra_da_coluna(i)}{n}"
            url = link_valido(c.link) if c.link else None
            estilo = "link" if url else (c.estilo or colunas[i].estilo)
            partes.append(_celula_xml(ref, c.valor, estilo))
            if url:
                links.append((ref, url))
        linhas_xml.append(f'<row r="{n}">' + "".join(partes) + "</row>")

    hiperlinks_xml = ""
    rels_xml = ""
    if links:
        hiperlinks_xml = "<hyperlinks>" + "".join(
            f'<hyperlink ref="{ref}" r:id="rId{i}"/>' for i, (ref, _) in enumerate(links, 1)) + "</hyperlinks>"
        rels_xml = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="{NS_REL}">'
                    + "".join(f'<Relationship Id="rId{i}" Type="{TIPO_LINK}" Target={quoteattr(url)} TargetMode="External"/>'
                              for i, (_, url) in enumerate(links, 1)) + "</Relationships>")

    folha = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<worksheet xmlns="{NS_PLANILHA}" xmlns:r="{NS_REL_DOC}">'
        f'<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>'
        f'<dimension ref="A1:{ultima}{n_lin}"/>'
        f'<sheetViews><sheetView workbookViewId="0" showGridLines="0" tabSelected="1">'
        f'<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        f'<selection pane="bottomLeft" activeCell="A2" sqref="A2"/></sheetView></sheetViews>'
        f'<sheetFormatPr defaultRowHeight="15"/>'
        f'<cols>{cols_xml}</cols>'
        f'<sheetData>{"".join(linhas_xml)}</sheetData>'
        f'<autoFilter ref="A1:{ultima}{n_lin}"/>'
        f'{hiperlinks_xml}'
        f'<pageMargins left="0.4" right="0.4" top="0.6" bottom="0.6" header="0.3" footer="0.3"/>'
        f'<pageSetup paperSize="9" orientation="landscape" fitToWidth="1" fitToHeight="0"/>'
        f'</worksheet>')

    aba = quoteattr(nome_aba)
    aba_ref = "'" + nome_aba.replace("'", "''") + "'"
    pasta = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<workbook xmlns="{NS_PLANILHA}" xmlns:r="{NS_REL_DOC}">'
        f'<bookViews><workbookView xWindow="0" yWindow="0" windowWidth="28800" windowHeight="15000"/></bookViews>'
        f'<sheets><sheet name={aba} sheetId="1" r:id="rId1"/></sheets>'
        f'<definedNames>'
        f'<definedName name="_xlnm._FilterDatabase" localSheetId="0" hidden="1">{escape(aba_ref)}!$A$1:${ultima}${n_lin}</definedName>'
        f'<definedName name="_xlnm.Print_Titles" localSheetId="0">{escape(aba_ref)}!$1:$1</definedName>'
        f'</definedNames></workbook>')

    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    arquivos = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            '</Types>'),
        "_rels/.rels": (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="{NS_REL}">'
            f'<Relationship Id="rId1" Type="{NS_REL_DOC}/officeDocument" Target="xl/workbook.xml"/>'
            f'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            f'<Relationship Id="rId3" Type="{NS_REL_DOC}/extended-properties" Target="docProps/app.xml"/>'
            f'</Relationships>'),
        "docProps/core.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(titulo_documento)}</dc:title><dc:creator>Lead Kit Silver</dc:creator>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{agora}</dcterms:created></cp:coreProperties>'),
        "docProps/app.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            '<Application>Lead Kit Silver</Application></Properties>'),
        "xl/workbook.xml": pasta,
        "xl/_rels/workbook.xml.rels": (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="{NS_REL}">'
            f'<Relationship Id="rId1" Type="{NS_REL_DOC}/worksheet" Target="worksheets/sheet1.xml"/>'
            f'<Relationship Id="rId2" Type="{NS_REL_DOC}/styles" Target="styles.xml"/></Relationships>'),
        "xl/styles.xml": ESTILOS_XML,
        "xl/worksheets/sheet1.xml": folha,
    }
    if rels_xml:
        arquivos["xl/worksheets/_rels/sheet1.xml.rels"] = rels_xml

    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in arquivos.items():  # [Content_Types].xml precisa ser o primeiro
            z.writestr(nome, conteudo.encode("utf-8"))
    return saida.getvalue()
