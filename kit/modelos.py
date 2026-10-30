"""Troca os marcadores das mensagens de abordagem. Sem IA: so troca de texto.

Marcadores: {nome} {cidade} {categoria} {motivo} {meu_nome} {minha_empresa}.
{motivo} vem da frase da regra que mais pesou na nota (kit/regras.json), um fato que o dado comprova.
"""
import json
import re
from pathlib import Path

REGRAS = json.loads((Path(__file__).resolve().parent / "regras.json").read_text(encoding="utf-8"))

MARCADOR = re.compile(r"\{([a-z_]+)\}")

# PROVISORIO, ate a fase 4. Na fase 4 a IA escreve os modelos do jeito do usuario e eles ficam em
# perfil["mensagens"]. Enquanto o perfil nao tiver modelo para o canal, o kit usa este.
MODELOS_PROVISORIOS = {
    "whatsapp": ("Oi, tudo bem? Aqui é {meu_nome}, da {minha_empresa}. Vi a {nome}, em {cidade}, "
                 "e notei que {motivo}. Posso te mandar uma ideia rápida? "
                 "Se não fizer sentido, é só avisar que não escrevo mais."),
    "email": ("Assunto: Uma ideia para a {nome}\n\n"
              "Olá! Sou {meu_nome}, da {minha_empresa}. Vi a {nome}, em {cidade}, e notei que {motivo}. "
              "Posso enviar uma ideia rápida? Se não fizer sentido, é só avisar que não escrevo mais."),
}


def _virgula(numero):
    return f"{numero:g}".replace(".", ",") if numero is not None else ""


def _preencher(texto, dados):
    """Troca {marcador} pelos dados. Marcador desconhecido fica como esta, sem quebrar."""
    return MARCADOR.sub(lambda m: str(dados.get(m.group(1), m.group(0))), texto)


def frase_do_motivo(lead, regra_id):
    """A frase de {motivo}: um fato que o dado do lead comprova."""
    modelo = REGRAS["regras"][regra_id]["frase"] if regra_id else REGRAS["frase_sem_motivo"]
    return _preencher(modelo, {
        "nota_maps": _virgula(lead.get("nota_maps")),
        "avaliacoes": lead.get("avaliacoes") if lead.get("avaliacoes") is not None else "",
        "cidade": lead.get("cidade") or "",
    })


def preencher(modelo, lead, perfil, regra_id):
    dados = {
        "nome": lead["nome"],
        "cidade": lead.get("cidade") or "",
        "categoria": lead.get("categoria") or "",
        "motivo": frase_do_motivo(lead, regra_id),
        "meu_nome": (perfil.get("negocio") or {}).get("nome", ""),
        "minha_empresa": (perfil.get("negocio") or {}).get("empresa", ""),
    }
    return _preencher(modelo, dados)


def mensagens_do_lead(lead, perfil, regra_id):
    """{canal: {'texto': ..., 'padrao': True/False}} para os canais do perfil que tem modelo."""
    salvas = perfil.get("mensagens") or {}
    saida = {}
    for canal in (perfil.get("abordagem") or {}).get("canais") or []:
        if salvas.get(canal):
            saida[canal] = {"texto": preencher(salvas[canal], lead, perfil, regra_id), "padrao": False}
        elif canal in MODELOS_PROVISORIOS:
            saida[canal] = {"texto": preencher(MODELOS_PROVISORIOS[canal], lead, perfil, regra_id),
                            "padrao": True}
    return saida
