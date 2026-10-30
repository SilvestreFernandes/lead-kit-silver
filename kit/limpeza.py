"""Le o CSV do motor e devolve leads limpos. So biblioteca padrao.

Os nomes das colunas foram conferidos na fase 0 com um CSV real (ver
docs/planejamento/fase0-verificacao-motor.md). Se faltar uma coluna usada aqui, para com
uma mensagem clara em vez de adivinhar.
"""
import csv
import io
import json
import re
import unicodedata
from urllib.parse import urlparse

COLUNAS_USADAS = [
    "title", "category", "address", "website", "phone", "review_count", "review_rating",
    "latitude", "longitude", "cid", "place_id", "link", "reservations", "order_online", "emails",
]

REDES_SOCIAIS = ("instagram.com", "facebook.com")


class ErroCSV(Exception):
    """O CSV do motor nao tem o formato esperado."""


def sem_acento(texto):
    base = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in base if not unicodedata.combining(c))


def normalizar_nome(texto):
    """Nome sem acento, minusculo, sem sufixo de filial (" - Algo") e sem pontuacao."""
    principal = (texto or "").split(" - ")[0]
    principal = sem_acento(principal).casefold()
    principal = re.sub(r"[^a-z0-9]+", " ", principal)
    return " ".join(principal.split())


def json_preenchido(texto):
    """True se o campo JSON traz alguma coisa. Vazio, [], {} e null contam como vazio."""
    texto = (texto or "").strip()
    if texto in ("", "[]", "{}", "null", '""'):
        return False
    try:
        valor = json.loads(texto)
    except json.JSONDecodeError:
        return True
    return valor not in (None, "", [], {})


def numero(texto):
    """Aceita '4.5' e '4,5'. Devolve None se nao for numero."""
    texto = (texto or "").strip().replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def inteiro(texto):
    valor = numero(re.sub(r"[.\s](?=\d{3}\b)", "", (texto or "").strip()))
    return int(valor) if valor is not None else None


def dominio(site):
    site = (site or "").strip()
    if not site:
        return ""
    if "//" not in site:
        site = "//" + site
    host = (urlparse(site).hostname or "").casefold()
    return host[4:] if host.startswith("www.") else host


def eh_rede_social(site):
    host = dominio(site)
    return any(host == r or host.endswith("." + r) for r in REDES_SOCIAIS)


def telefone_digitos(texto):
    """So os digitos, sem o 55 do Brasil quando vier na frente."""
    d = re.sub(r"\D", "", texto or "")
    if len(d) in (12, 13) and d.startswith("55"):
        d = d[2:]
    return d


def eh_celular(digitos):
    """DDD de 2 digitos e depois 9 digitos comecando em 9. E uma estimativa."""
    return len(digitos) == 11 and digitos[2] == "9"


def chave_do_lead(l):
    if l["place_id"]:
        return "p:" + l["place_id"]
    if l["cid"]:
        return "c:" + l["cid"]
    return "n:" + normalizar_nome(l["nome"]) + "|" + normalizar_nome(l["endereco"])


def limpar_linha(linha):
    digitos = telefone_digitos(linha.get("phone"))
    emails = [e.strip() for e in (linha.get("emails") or "").replace(";", ",").split(",") if e.strip()]
    lead = {
        "place_id": (linha.get("place_id") or "").strip(),
        "cid": (linha.get("cid") or "").strip(),
        "nome": (linha.get("title") or "").strip(),
        "categoria": (linha.get("category") or "").strip(),
        "endereco": (linha.get("address") or "").strip(),
        "site": (linha.get("website") or "").strip(),
        "telefone": (linha.get("phone") or "").strip(),
        "telefone_digitos": digitos,
        "celular": eh_celular(digitos),
        "avaliacoes": inteiro(linha.get("review_count")),
        "nota_maps": numero(linha.get("review_rating")),
        "delivery": json_preenchido(linha.get("order_online")),
        "reserva": json_preenchido(linha.get("reservations")),
        "emails": emails,
        "latitude": numero(linha.get("latitude")),
        "longitude": numero(linha.get("longitude")),
        "link": (linha.get("link") or "").strip(),
    }
    lead["nome_norm"] = normalizar_nome(lead["nome"])
    lead["chave"] = chave_do_lead(lead)
    return lead


def ler_csv(texto):
    """Texto do CSV -> (leads limpos sem duplicados, linhas ignoradas)."""
    leitor = csv.DictReader(io.StringIO(texto.lstrip("﻿")))
    faltam = [c for c in COLUNAS_USADAS if c not in (leitor.fieldnames or [])]
    if faltam:
        raise ErroCSV("O arquivo do motor não tem as colunas esperadas: " + ", ".join(faltam)
                      + ". A versão do motor pode ter mudado.")
    vistos, leads, ignoradas = set(), [], 0
    for linha in leitor:
        lead = limpar_linha(linha)
        if not lead["nome"]:
            ignoradas += 1
            continue
        if lead["chave"] in vistos:
            continue
        vistos.add(lead["chave"])
        leads.append(lead)
    return leads, ignoradas
