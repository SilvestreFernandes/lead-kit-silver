"""Consulta de leads: avalia com o perfil de agora, filtra, resume e exporta.

Nota, letra, motivos e "possivel rede" sao calculados na hora a partir do perfil atual, sobre todos
os leads do banco. Assim mudar o perfil muda o resultado sem precisar regravar nada.
"""
import csv
import io
from urllib.parse import quote

from kit import banco, modelos, pontuacao, xlsx
from kit.limpeza import normalizar_nome

FILTROS_EXCLUIDOS = ("nao", "sim", "todos")
LETRAS = ("A", "B", "C")


class FiltroInvalido(ValueError):
    """Um filtro da consulta veio com valor que nao existe. A mensagem ja esta em portugues."""


def avaliar(conn, perfil):
    """Todos os leads do banco avaliados pelo perfil, na ordem de pontuacao.avaliar_todos."""
    return pontuacao.avaliar_todos(banco.todos_os_leads(conn), perfil)


def ler_filtros(consulta):
    """Converte a query string (dict nome -> lista) em filtros. Levanta FiltroInvalido."""
    def um(nome, padrao=None):
        valores = consulta.get(nome)
        return valores[0] if valores else padrao

    filtros = {"busca": None, "letras": None, "status": None, "texto": "", "excluidos": "nao"}
    if um("busca") not in (None, ""):
        try:
            filtros["busca"] = int(um("busca"))
        except ValueError:
            raise FiltroInvalido("O filtro 'busca' precisa ser um número.")
    if um("letra"):
        letras = {x.strip().upper() for x in um("letra").split(",") if x.strip()}
        if not letras <= set(LETRAS):
            raise FiltroInvalido("O filtro 'letra' aceita só A, B e C.")
        filtros["letras"] = letras
    if um("status"):
        status = {x.strip() for x in um("status").split(",") if x.strip()}
        if not status <= set(banco.STATUS_LEAD):
            raise FiltroInvalido("O filtro 'status' aceita só: " + ", ".join(banco.STATUS_LEAD) + ".")
        filtros["status"] = status
    filtros["texto"] = (um("q") or "").strip()[:100]
    excluidos = um("excluidos", "nao")
    if excluidos not in FILTROS_EXCLUIDOS:
        raise FiltroInvalido("O filtro 'excluidos' aceita só: " + ", ".join(FILTROS_EXCLUIDOS) + ".")
    filtros["excluidos"] = excluidos
    return filtros


def filtrar(avaliados, filtros, ids_da_busca=None):
    texto = normalizar_nome(filtros["texto"])
    digitos = "".join(c for c in filtros["texto"] if c.isdigit())
    saida = []
    for r in avaliados:
        l = r["lead"]
        if ids_da_busca is not None and l["id"] not in ids_da_busca:
            continue
        if filtros["excluidos"] == "nao" and r["excluido_por"]:
            continue
        if filtros["excluidos"] == "sim" and not r["excluido_por"]:
            continue
        if filtros["letras"] and r["letra"] not in filtros["letras"]:
            continue
        if filtros["status"] and l["status"] not in filtros["status"]:
            continue
        if texto or digitos:
            acha = bool(texto) and any(texto in normalizar_nome(l[c] or "")
                                       for c in ("nome", "categoria", "endereco"))
            acha = acha or (len(digitos) >= 3 and digitos in l["telefone_digitos"])
            if not acha:
                continue
        saida.append(r)
    return saida


def contar_por_letra(avaliados):
    contagem = {letra: 0 for letra in LETRAS}
    for r in avaliados:
        contagem[r["letra"]] += 1
    return contagem


def resumo(r):
    l = r["lead"]
    return {
        "id": l["id"], "nome": l["nome"], "categoria": l["categoria"], "endereco": l["endereco"],
        "cidade": l["cidade"], "uf": l["uf"], "telefone": l["telefone"], "celular": l["celular"],
        "site": l["site"], "avaliacoes": l["avaliacoes"], "nota_maps": l["nota_maps"],
        "nota": r["nota"], "letra": r["letra"], "motivos": r["motivos"],
        "excluido_por": r["excluido_por"], "status": l["status"], "anotacao": l["anotacao"],
    }


def detalhe(r, perfil):
    l = r["lead"]
    d = resumo(r)
    d.update({
        "emails": l["emails"], "link": l["link"], "latitude": l["latitude"], "longitude": l["longitude"],
        "delivery": l["delivery"], "reserva": l["reserva"], "email_ligado": l["email_ligado"],
        "motivo_principal": r["motivo_principal"],
        "frase_do_motivo": modelos.frase_do_motivo(l, r["motivo_principal_id"]),
        "mensagens": modelos.mensagens_do_lead(l, perfil, r["motivo_principal_id"]),
        "mensagem_editada": l["mensagem_editada"],
    })
    return d


# ---------- exportacao em CSV ----------

CABECALHO = ["Nota", "Pontos", "Negócio", "Categoria", "Endereço", "Cidade", "UF", "Telefone",
             "Celular provável", "Site", "E-mails", "Avaliações", "Nota no Maps", "Motivos",
             "Excluído por", "Status", "Anotação", "Mensagem editada", "Link"]

PERIGOSOS = ("=", "+", "-", "@", "\t", "\r")


def proteger(texto):
    """Planilha trata texto que comeca com = + - @ como formula. Um apostrofo na frente evita isso."""
    texto = texto or ""
    return "'" + texto if texto.startswith(PERIGOSOS) else texto


def _telefone_nacional(lead):
    """'(DD) NNNNN-NNNN' para telefone brasileiro, ou None se nao der pra reformatar com seguranca.

    O '+55' ja foi tirado dos digitos na limpeza. Numero que comeca com '+' e nao e '+55' (de fora do
    Brasil) ou que nao tem 10 ou 11 digitos nao e reformatado.
    """
    original = (lead["telefone"] or "").strip()
    d = lead["telefone_digitos"]
    estrangeiro = original.startswith("+") and not original.startswith("+55")
    if not estrangeiro and len(d) in (10, 11):
        return f"({d[:2]}) {d[2:-4]}-{d[-4:]}"
    return None


def telefone_para_csv(lead):
    """No CSV o telefone nunca comeca com '+': ou e reformatado, ou ganha o apostrofo de protecao."""
    return _telefone_nacional(lead) or proteger((lead["telefone"] or "").strip())


def telefone_para_planilha(lead):
    """Na planilha .xlsx o texto e gravado como texto puro, entao nao precisa de apostrofo."""
    return _telefone_nacional(lead) or (lead["telefone"] or "").strip()


def exportar_csv(avaliados):
    """Texto do CSV em UTF-8 com BOM (abre certo no Excel). Colunas numericas ficam como numero."""
    saida = io.StringIO()
    escritor = csv.writer(saida, lineterminator="\r\n")
    escritor.writerow(CABECALHO)
    for r in avaliados:
        l = r["lead"]
        escritor.writerow([
            r["letra"], r["nota"], proteger(l["nome"]), proteger(l["categoria"]), proteger(l["endereco"]),
            proteger(l["cidade"]), l["uf"], telefone_para_csv(l), "sim" if l["celular"] else "não",
            proteger(l["site"]), proteger(", ".join(l["emails"])),
            "" if l["avaliacoes"] is None else l["avaliacoes"],
            "" if l["nota_maps"] is None else l["nota_maps"],
            proteger("; ".join(r["motivos"])), proteger(r["excluido_por"] or ""), l["status"],
            proteger(l["anotacao"]), proteger(l["mensagem_editada"]), proteger(l["link"]),
        ])
    return "﻿" + saida.getvalue()


# ---------- exportacao em .xlsx ----------

LIMITE_LINK_COM_MENSAGEM = 1800


def link_whatsapp(lead, mensagem=""):
    """Link wa.me so para telefone que parece celular (estimativa). A mensagem vai pre-preenchida."""
    d = lead["telefone_digitos"]
    if not lead["celular"] or len(d) != 11:
        return None
    url = f"https://wa.me/55{d}"
    if mensagem:
        com_texto = url + "?text=" + quote(mensagem, safe="")
        if len(com_texto) <= LIMITE_LINK_COM_MENSAGEM:
            return com_texto
    return url


def mensagem_para_exportar(r, perfil):
    """A mensagem editada, se houver; senao a do WhatsApp (ou do primeiro canal com modelo)."""
    l = r["lead"]
    if l["mensagem_editada"]:
        return l["mensagem_editada"]
    mensagens = modelos.mensagens_do_lead(l, perfil, r["motivo_principal_id"])
    if "whatsapp" in mensagens:
        return mensagens["whatsapp"]["texto"]
    return next(iter(mensagens.values()))["texto"] if mensagens else ""


def exportar_xlsx(avaliados, perfil):
    """Bytes de uma planilha .xlsx pronta para mostrar a um cliente."""
    mostrar_exclusao = any(r["excluido_por"] for r in avaliados)
    colunas = [
        xlsx.Coluna("Negócio", "texto", 38),
        xlsx.Coluna("Nota", "centro", largura_fixa=8),
        xlsx.Coluna("Pontos", "inteiro", largura_fixa=9),
        xlsx.Coluna("Motivos", "quebra", 46),
    ]
    if mostrar_exclusao:
        colunas.append(xlsx.Coluna("Excluído por", "quebra", 30))
    colunas += [
        xlsx.Coluna("Categoria", "texto", 24),
        xlsx.Coluna("Telefone", "texto", 18),
        xlsx.Coluna("WhatsApp", "texto", largura_fixa=18),
        xlsx.Coluna("Site", "texto", 34),
        xlsx.Coluna("Endereço", "quebra", 44),
        xlsx.Coluna("Avaliação no Maps", "decimal", largura_fixa=12),
        xlsx.Coluna("Nº de avaliações", "inteiro", largura_fixa=13),
        xlsx.Coluna("Status", "centro", largura_fixa=13),
        xlsx.Coluna("Anotação", "quebra", 32),
        xlsx.Coluna("Mensagem", "quebra", 64),
    ]
    linhas = []
    for r in avaliados:
        l = r["lead"]
        mensagem = mensagem_para_exportar(r, perfil)
        zap = link_whatsapp(l, mensagem)
        linha = [l["nome"], xlsx.Celula(r["letra"], "nota_" + r["letra"].lower()), r["nota"],
                 "; ".join(r["motivos"])]
        if mostrar_exclusao:
            linha.append(r["excluido_por"] or "")
        linha += [
            l["categoria"], telefone_para_planilha(l),
            xlsx.Celula("Abrir WhatsApp", link=zap) if zap else "",
            xlsx.Celula(l["site"], link=l["site"]) if l["site"] else "",
            l["endereco"], l["nota_maps"], l["avaliacoes"], l["status"], l["anotacao"], mensagem,
        ]
        linhas.append(linha)
    return xlsx.gerar(colunas, linhas, nome_aba="Leads", titulo_documento="Lead Kit Silver: leads")
