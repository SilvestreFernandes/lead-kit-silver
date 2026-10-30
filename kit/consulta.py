"""Consulta de leads: avalia com o perfil de agora, filtra, resume e exporta.

Nota, letra, motivos e "possivel rede" sao calculados na hora a partir do perfil atual, sobre todos
os leads do banco. Assim mudar o perfil muda o resultado sem precisar regravar nada.
"""
import csv
import io

from kit import banco, modelos, pontuacao
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


def telefone_para_csv(lead):
    """Telefone brasileiro vira '(DD) NNNNN-NNNN', que nao comeca com '+' e nao vira formula.

    O '+55' ja foi tirado dos digitos na limpeza. Numero que comeca com '+' e nao e '+55' (de fora do
    Brasil) ou que nao tem 10 ou 11 digitos nao e reformatado: vai como veio, so com a protecao.
    """
    original = (lead["telefone"] or "").strip()
    d = lead["telefone_digitos"]
    estrangeiro = original.startswith("+") and not original.startswith("+55")
    if not estrangeiro and len(d) in (10, 11):
        return f"({d[:2]}) {d[2:-4]}-{d[-4:]}"
    return proteger(original)


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
