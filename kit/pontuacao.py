"""Nota dos leads. Tudo por regra e por codigo, nunca por IA: a mesma lista gera sempre a mesma nota.

A marcacao de "possivel rede" e calculada na hora, olhando todos os leads que o chamador passar.
Ela nunca e gravada no lead.
"""
import json
from collections import defaultdict
from pathlib import Path

from kit.limpeza import dominio, eh_rede_social, normalizar_nome

REGRAS = json.loads((Path(__file__).resolve().parent / "regras.json").read_text(encoding="utf-8"))


def soma_dos_pesos(perfil):
    return sum(r["peso"] for r in perfil["pontuacao"]["regras"])


def _teto(numerador, denominador):
    return -(-numerador // denominador)


def cortes(perfil):
    """Corte A e B. O perfil pode sobrescrever; senao, 70% e 40% da soma dos pesos, para cima."""
    pont = perfil["pontuacao"]
    if pont.get("corte_a") is not None and pont.get("corte_b") is not None:
        return pont["corte_a"], pont["corte_b"]
    soma = soma_dos_pesos(perfil)
    return (_teto(soma * round(REGRAS["cortes"]["a"] * 100), 100),
            _teto(soma * round(REGRAS["cortes"]["b"] * 100), 100))


def _acerto(regra_id, lead, cfg, peso, email_ligado):
    """Devolve os pontos que a regra rende neste lead (0 se nao vale)."""
    nota, avaliacoes = lead["nota_maps"], lead["avaliacoes"]
    if regra_id == "sem_site":
        return peso if not lead["site"] else 0
    if regra_id == "so_instagram":
        return peso if eh_rede_social(lead["site"]) else 0
    if regra_id == "nota_alta":
        if nota is None:
            return 0
        if nota >= cfg["nota_minima"]:
            return peso
        if nota >= cfg["nota_media"]:
            return min(cfg["peso_media"], peso)
        return 0
    if regra_id == "nota_baixa":
        return peso if nota is not None and nota < cfg["nota_maxima"] else 0
    if regra_id == "muitas_avaliacoes":
        return peso if avaliacoes is not None and avaliacoes >= cfg["minimo"] else 0
    if regra_id == "poucas_avaliacoes":
        return peso if avaliacoes is not None and avaliacoes < cfg["maximo"] else 0
    if regra_id == "celular":
        return peso if lead["celular"] else 0
    if regra_id == "delivery":
        return peso if lead["delivery"] else 0
    if regra_id == "reserva":
        return peso if lead["reserva"] else 0
    if regra_id == "sem_email":
        # Sem a opcao de e-mail ligada no job a coluna vem sempre vazia, entao a regra nao vale.
        return peso if email_ligado and not lead["emails"] else 0
    return 0


def pontuar(lead, perfil, email_ligado=False):
    """Devolve {nota, letra, motivos, motivo_principal}. Motivos como 'sem site (+3)'."""
    motivos, pontos = [], []
    # O lead vindo do banco sabe se a busca dele usou a opcao de e-mail; esse valor manda.
    email_ligado = lead.get("email_ligado", email_ligado)
    for regra in perfil["pontuacao"]["regras"]:
        cfg = REGRAS["regras"][regra["id"]]
        ganho = _acerto(regra["id"], lead, cfg, regra["peso"], email_ligado)
        if ganho > 0:
            motivos.append(f"{cfg['texto']} (+{ganho})")
            pontos.append((ganho, cfg["texto"]))
    total = sum(p for p, _ in pontos)
    corte_a, corte_b = cortes(perfil)
    letra = "A" if total >= corte_a else "B" if total >= corte_b else "C"
    principal = max(pontos, key=lambda p: p[0])[1] if pontos else ""
    return {"nota": total, "letra": letra, "motivos": motivos, "motivo_principal": principal}


def contar_redes(leads):
    """nome normalizado -> numero de enderecos (chaves) diferentes com esse nome."""
    grupos = defaultdict(set)
    for l in leads:
        if l["nome_norm"]:
            grupos[l["nome_norm"]].add(l["chave"])
    return {nome: len(chaves) for nome, chaves in grupos.items()}


def exclusao(lead, perfil, redes):
    """Devolve o motivo da exclusao em texto, ou None se o lead fica na lista."""
    ativas = set(perfil.get("exclusoes") or [])
    cfg = REGRAS["exclusoes"]
    if "sem_telefone" in ativas and not lead["telefone_digitos"]:
        return cfg["sem_telefone"]["texto"]
    if "nota_muito_baixa" in ativas and lead["nota_maps"] is not None \
            and lead["nota_maps"] < cfg["nota_muito_baixa"]["abaixo_de"]:
        return cfg["nota_muito_baixa"]["texto"]
    if "franquia" in ativas:
        n = redes.get(lead["nome_norm"], 0)
        if n >= cfg["franquia"]["minimo_enderecos"]:
            return f"{cfg['franquia']['texto']} (nome repetido em {n} endereços)"
    if "concorrente" in ativas:
        for item in perfil.get("exclusoes_concorrentes") or []:
            alvo = normalizar_nome(item)
            dom = dominio(item) if "." in item else ""
            if (alvo and alvo in lead["nome_norm"]) or (dom and dom == dominio(lead["site"])):
                return cfg["concorrente"]["texto"]
    if "categoria" in ativas:
        cat = normalizar_nome(lead["categoria"])
        for item in perfil.get("exclusoes_categorias") or []:
            if normalizar_nome(item) and normalizar_nome(item) in cat:
                return cfg["categoria"]["texto"]
    return None


def avaliar_todos(leads, perfil, email_ligado=False):
    """Pontua e marca exclusoes de uma lista de leads. Ordena por nota, da maior pra menor.

    As redes sao recalculadas aqui, sobre os leads recebidos, e nada disso e gravado nos leads.
    """
    redes = contar_redes(leads)
    saida = []
    for lead in leads:
        resultado = pontuar(lead, perfil, email_ligado)
        resultado["excluido_por"] = exclusao(lead, perfil, redes)
        resultado["lead"] = lead
        saida.append(resultado)
    saida.sort(key=lambda r: (r["excluido_por"] is not None, -r["nota"], r["lead"]["nome_norm"], r["lead"]["chave"]))
    return saida
