"""Monta o perfil.json a partir das respostas da entrevista (dados/respostas.json). Sem IA: só regras fixas.

    python kit/montar_perfil.py estado     o que já foi respondido, o que falta e o que está errado
    python kit/montar_perfil.py resumo     o resumo em português para a pessoa conferir antes do "confirmo"
    python kit/montar_perfil.py montar     confere, monta e grava dados/perfil.json (use --refazer para trocar um perfil)

A IA grava cada resposta em dados/respostas.json logo depois de ouvi-la (formato em entrevista/perguntas.md). Este script
transforma isso em perfil.json, confere com o mesmo validador que o painel usa e nunca grava um perfil com erro.
Todas as saídas são JSON em UTF-8, para a IA repassar a mensagem em português à pessoa.
"""
import argparse
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from kit import validar_perfil  # noqa: E402
from kit.servidor import UFS  # noqa: E402

ESQUEMA = validar_perfil.ESQUEMA
REGRAS = validar_perfil.REGRAS

OBRIGATORIAS = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12]  # a 7 é opcional
LIMITE_OFERTA = 300
LIMITE_NOME = 80
LIMITE_ITEM = 200
LIMITE_ENTRADA = 120
LIMITE_LISTA = 40

DOCUMENTO = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{1,7}\b")
CONTROLE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
REGIAO = re.compile(r"^(.+?)\s*[-,/]\s*([A-Za-z]{2})$")

# Texto que a pessoa lê para cada opção que vira regra ou exclusão (vem de kit/regras.json).
TEXTO_REGRA = {rid: cfg["texto"] for rid, cfg in REGRAS["regras"].items()}
TEXTO_EXCLUSAO = {eid: cfg["texto"] for eid, cfg in REGRAS["exclusoes"].items()}
ROTULO_CANAL = {"whatsapp": "WhatsApp", "email": "e-mail", "ligacao": "ligação", "visita": "visita"}
ROTULO_TOM = {"amigavel": "amigável", "direto": "direto", "formal": "formal"}
ROTULO_PORTE = {"pequeno": "pequeno", "medio": "médio", "grande": "grande", "qualquer": "qualquer"}
ROTULO_ATENDIMENTO = {"presencial": "atendimento presencial", "remoto": "atendimento remoto", "ambos": "atendimento presencial e remoto"}
ROTULO_VOLUME = {v["id"]: v["texto"].lower() for v in ESQUEMA["volumes_semana"]}


class Resposta:
    """Resultado de ler uma resposta: o valor limpo, ou o que está errado."""

    def __init__(self):
        self.erros, self.avisos = [], []


# ---------------------------------------------------------------- limpeza de cada tipo de resposta

def _texto(valor, numero, rotulo, maximo, obrigatorio, saida):
    if valor is None or valor == "":
        if obrigatorio:
            saida.erros.append(f"Pergunta {numero}: falta {rotulo}.")
        return ""
    if not isinstance(valor, str):
        saida.erros.append(f"Pergunta {numero}: {rotulo} precisa ser um texto.")
        return ""
    limpo = re.sub(r"\s+", " ", CONTROLE.sub(" ", valor)).strip()
    if DOCUMENTO.search(limpo):
        saida.erros.append(f"Pergunta {numero}: isso parece um documento ou um número de cartão. O perfil não guarda isso; "
                           "tire e responda de novo.")
        return ""
    if len(limpo) > maximo:
        saida.erros.append(f"Pergunta {numero}: {rotulo} está grande demais (o limite é {maximo} caracteres).")
        return ""
    if not limpo and obrigatorio:
        saida.erros.append(f"Pergunta {numero}: falta {rotulo}.")
    return limpo


def _lista_de_textos(valor, numero, rotulo, obrigatoria, saida, maximo=LIMITE_ITEM):
    if valor is None or valor == []:
        if obrigatoria:
            saida.erros.append(f"Pergunta {numero}: falta {rotulo}.")
        return []
    if isinstance(valor, str):  # a IA pode ter gravado "a, b": aceita e separa
        valor = [p for p in valor.split(",")]
    if not isinstance(valor, list):
        saida.erros.append(f"Pergunta {numero}: {rotulo} precisa ser uma lista.")
        return []
    antes = len(saida.erros)
    itens, vistos = [], set()
    for bruto in valor[:LIMITE_LISTA]:
        item = _texto(bruto, numero, rotulo, maximo, False, saida)
        if item and item.casefold() not in vistos:
            vistos.add(item.casefold())
            itens.append(item)
    if obrigatoria and not itens and len(saida.erros) == antes:
        saida.erros.append(f"Pergunta {numero}: falta {rotulo}.")
    return itens


def _um_de(valor, numero, rotulo, permitidos, saida, obrigatoria=True):
    if valor in (None, ""):
        if obrigatoria:
            saida.erros.append(f"Pergunta {numero}: falta {rotulo}.")
        return ""
    if valor not in permitidos:
        saida.erros.append(f"Pergunta {numero}: {rotulo} precisa ser um destes: {', '.join(permitidos)}.")
        return ""
    return valor


def _varios_de(valor, numero, rotulo, permitidos, saida, obrigatoria=True):
    if valor in (None, []):
        if obrigatoria:
            saida.erros.append(f"Pergunta {numero}: escolha pelo menos {rotulo}.")
        return []
    if not isinstance(valor, list):
        saida.erros.append(f"Pergunta {numero}: {rotulo} precisa ser uma lista.")
        return []
    ruins = [v for v in valor if v not in permitidos]
    if ruins:
        saida.erros.append(f"Pergunta {numero}: opção desconhecida ({', '.join(map(str, ruins))}). As opções são: {', '.join(permitidos)}.")
    return [v for v in permitidos if v in valor]  # sempre na mesma ordem do kit, sem repetir


PALAVRAS_MIUDAS = {"de", "da", "do", "das", "dos", "e"}


def _capitalizar(cidade):
    """Só mexe quando está tudo em minúsculas ou tudo em maiúsculas: 'são josé dos campos' vira 'São José dos Campos'."""
    if cidade != cidade.lower() and cidade != cidade.upper():
        return cidade
    palavras = []
    for i, palavra in enumerate(cidade.lower().split(" ")):
        if i and palavra in PALAVRAS_MIUDAS:
            palavras.append(palavra)
        else:
            palavras.append("-".join(parte[:1].upper() + parte[1:] for parte in palavra.split("-")))
    return " ".join(palavras)


def normalizar_regiao(texto):
    """'brasília - df', 'Brasília/DF' e 'Brasília,DF' viram 'Brasília-DF'. 'Todo o Brasil' fica como está. Senão, None."""
    texto = re.sub(r"\s+", " ", texto or "").strip()
    if texto.casefold() == "todo o brasil":
        return "Todo o Brasil"
    achou = REGIAO.match(texto)
    if not achou:
        return None
    cidade, uf = _capitalizar(achou.group(1).strip()), achou.group(2).upper()
    return f"{cidade}-{uf}" if uf in UFS and cidade else None


# ---------------------------------------------------------------- uma função por pergunta

def _p1(resp, saida):
    return _texto(resp.get("1"), 1, "o que você vende", LIMITE_OFERTA, True, saida)


def _p2(resp, saida):
    bruto = resp.get("2")
    if not isinstance(bruto, dict):
        saida.erros.append("Pergunta 2: falta o seu nome (e a empresa, se tiver).")
        return {"nome": "", "empresa": ""}
    nome = _texto(bruto.get("nome"), 2, "o seu nome", LIMITE_NOME, True, saida)
    empresa = _texto(bruto.get("empresa"), 2, "o nome da empresa", LIMITE_NOME, False, saida)
    if nome and not empresa:
        saida.avisos.append("Você não tem empresa: as mensagens vão usar só o seu nome.")
    return {"nome": nome, "empresa": empresa}


def _p3(resp, saida):
    bruto = resp.get("3")
    if not isinstance(bruto, dict):
        saida.erros.append("Pergunta 3: faltam os tipos de negócio e o porte.")
        return {"tipos": [], "porte": ""}
    tipos = _lista_de_textos(bruto.get("tipos"), 3, "os tipos de negócio que você quer atender", True, saida)
    porte = _um_de(bruto.get("porte"), 3, "o porte", ESQUEMA["portes"], saida)
    return {"tipos": tipos, "porte": porte}


def _p4(resp, saida):
    bruto = resp.get("4")
    if not isinstance(bruto, dict):
        saida.erros.append("Pergunta 4: faltam as regiões e como você atende.")
        return {"regioes": [], "atendimento": ""}
    candidatas = _lista_de_textos(bruto.get("regioes"), 4, "onde você atende", True, saida)
    regioes = []
    for c in candidatas:
        norma = normalizar_regiao(c)
        if norma is None:
            saida.erros.append(f"Pergunta 4: não entendi \"{c}\". Escreva como Cidade-UF, por exemplo Brasília-DF, "
                               "ou \"Todo o Brasil\".")
        elif norma not in regioes:
            regioes.append(norma)
    atendimento = _um_de(bruto.get("atendimento"), 4, "como você atende", ESQUEMA["atendimentos"], saida)
    return {"regioes": regioes, "atendimento": atendimento}


def _p5(resp, saida):
    bruto = resp.get("5")
    if not isinstance(bruto, dict):
        saida.erros.append("Pergunta 5: escolha pelo menos uma coisa que faz um negócio ser um bom lead.")
        return []
    regras = _varios_de(bruto.get("regras"), 5, "uma coisa que faz um negócio ser um bom lead", list(REGRAS["regras"]), saida)
    if str(bruto.get("outro") or "").strip():
        saida.avisos.append("Pergunta 5: a resposta \"outra\" ficou anotada, mas não vira regra: o painel só dá nota por "
                            "coisas que o Google Maps mostra.")
    return regras


def _p6(resp, saida):
    bruto = resp.get("6")
    if bruto is None:
        saida.erros.append("Pergunta 6: falta responder o que você quer evitar (pode ser nada).")
        return {"evitar": [], "concorrentes": [], "categorias": []}
    if not isinstance(bruto, dict):
        saida.erros.append("Pergunta 6: a resposta precisa de \"evitar\" e, se for o caso, \"concorrentes\" e \"categorias\".")
        return {"evitar": [], "concorrentes": [], "categorias": []}
    evitar = _varios_de(bruto.get("evitar"), 6, "uma opção", list(REGRAS["exclusoes"]), saida, obrigatoria=False)
    concorrentes = _lista_de_textos(bruto.get("concorrentes"), 6, "os concorrentes", False, saida)
    categorias = _lista_de_textos(bruto.get("categorias"), 6, "as categorias a evitar", False, saida)
    if "concorrente" in evitar and not concorrentes:
        saida.erros.append("Pergunta 6: você marcou \"concorrentes\". Quais são? Escreva os nomes ou os sites.")
    if "categoria" in evitar and not categorias:
        saida.erros.append("Pergunta 6: você marcou \"categorias específicas\". Quais categorias devo evitar?")
    if concorrentes and "concorrente" not in evitar:
        saida.erros.append("Pergunta 6: há uma lista de concorrentes, mas \"concorrentes\" não está marcado em \"evitar\".")
    if categorias and "categoria" not in evitar:
        saida.erros.append("Pergunta 6: há uma lista de categorias, mas \"categoria\" não está marcado em \"evitar\".")
    if str(bruto.get("outro") or "").strip():
        saida.avisos.append("Pergunta 6: a resposta \"outra\" ficou anotada, mas não vira regra.")
    return {"evitar": evitar, "concorrentes": concorrentes, "categorias": categorias}


def _p7(resp, saida):
    return _texto(resp.get("7"), 7, "o melhor cliente", LIMITE_OFERTA, False, saida)


def _p8(resp, saida):
    return _varios_de(resp.get("8"), 8, "um jeito de abordar", ESQUEMA["canais"], saida)


def _p9(resp, saida):
    return _um_de(resp.get("9"), 9, "o tom das mensagens", ESQUEMA["tons"], saida)


def _p10(resp, saida):
    return _texto(resp.get("10"), 10, "a oferta de entrada", LIMITE_ENTRADA, True, saida)


def _p11(resp, saida):
    return _um_de(resp.get("11"), 11, "quantos contatos por semana", [v["id"] for v in ESQUEMA["volumes_semana"]], saida)


def _p12(resp, saida):
    bruto = resp.get("12")
    if not isinstance(bruto, dict):
        saida.erros.append("Pergunta 12: falta dizer se a sua área tem regras de publicidade ou de abordagem.")
        return "nao"
    escolha = _um_de(bruto.get("resposta"), 12, "a resposta", ["nao", "sim", "nao sei"], saida)
    detalhe = _texto(bruto.get("detalhe"), 12, "qual é a regra", LIMITE_ITEM, False, saida)
    if escolha == "sim":
        if not detalhe:
            saida.erros.append("Pergunta 12: você disse que sim. Qual é a regra ou o órgão? (por exemplo OAB)")
            return "sim"
        return f"sim: {detalhe}"
    return escolha or "nao"


PERGUNTAS = {1: _p1, 2: _p2, 3: _p3, 4: _p4, 5: _p5, 6: _p6, 7: _p7, 8: _p8, 9: _p9, 10: _p10, 11: _p11, 12: _p12}


# ---------------------------------------------------------------- montar o perfil

def carregar_respostas(caminho):
    """(respostas, erros). Arquivo que não existe vale como nenhuma resposta ainda."""
    caminho = Path(caminho)
    if not caminho.exists():
        return {}, []
    try:
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {}, [f"O arquivo de respostas não é um JSON válido (linha {e.lineno}). Corrija ou refaça a entrevista."]
    if not isinstance(bruto, dict):
        return {}, ["O arquivo de respostas precisa ser um objeto JSON."]
    return bruto, []


def _respondida(resp, numero):
    valor = resp.get(str(numero))
    return valor not in (None, "", [], {})


def estado(resp):
    """O que falta e o que está errado, pergunta por pergunta. `proxima` é a primeira que falta."""
    faltam = [n for n in OBRIGATORIAS if not _respondida(resp, n)]
    problemas = []
    for n in range(1, 13):
        if not _respondida(resp, n):
            continue
        saida = Resposta()
        PERGUNTAS[n](resp, saida)
        problemas += [e for e in saida.erros]
    desconhecidas = [k for k in resp if k != "versao" and not (k.isdigit() and 1 <= int(k) <= 12)]
    avisos = [f"A chave \"{k}\" não é de nenhuma pergunta e foi ignorada." for k in desconhecidas]
    return {"respondidas": [n for n in range(1, 13) if _respondida(resp, n)], "faltam": faltam,
            "proxima": faltam[0] if faltam else None, "erros": problemas, "avisos": avisos}


def montar(resp, hoje=None):
    """(perfil, erros, avisos). O perfil só vale se `erros` estiver vazio."""
    saida = Resposta()
    faltando = [n for n in OBRIGATORIAS if not _respondida(resp, n)]
    if faltando:
        saida.erros.append("Ainda faltam respostas: " + ", ".join(f"pergunta {n}" for n in faltando) + ".")
    dados = {n: PERGUNTAS[n](resp, saida) for n in PERGUNTAS if _respondida(resp, n) or n in OBRIGATORIAS}
    if saida.erros:
        return {}, _sem_repetir(saida.erros), _sem_repetir(saida.avisos)
    evitar = dados[6]["evitar"]
    perfil = {
        "versao": ESQUEMA["versao_atual"],
        "criado_em": (hoje or date.today()).isoformat(),
        "negocio": {**dados[2], "oferta": dados[1], "atendimento": dados[4]["atendimento"]},
        "cliente": {"tipos": dados[3]["tipos"], "porte": dados[3]["porte"], "regioes": dados[4]["regioes"],
                    "exemplo": dados.get(7, "")},
        "pontuacao": {"regras": [{"id": rid, "peso": REGRAS["regras"][rid]["peso"]} for rid in dados[5]]},
        "exclusoes": evitar,
        "exclusoes_concorrentes": dados[6]["concorrentes"],
        "exclusoes_categorias": dados[6]["categorias"],
        "abordagem": {"canais": dados[8], "tom": dados[9], "oferta_entrada": dados[10], "volume_semana": dados[11]},
        "conformidade": {"restricoes": dados[12]},
        "mensagens": {},
    }
    perfil, erros, avisos = validar_perfil.validar(perfil)
    return perfil, _sem_repetir(erros), _sem_repetir(saida.avisos + avisos)


def _sem_repetir(itens):
    return list(dict.fromkeys(itens))


def _lista_em_texto(itens):
    itens = list(itens)
    if len(itens) <= 1:
        return "".join(itens)
    return ", ".join(itens[:-1]) + " e " + itens[-1]


def resumo(perfil):
    """O resumo da entrevista, em linguagem natural, para a pessoa conferir antes do \"confirmo\"."""
    neg, cli, ab = perfil["negocio"], perfil["cliente"], perfil["abordagem"]
    regras = [f"{TEXTO_REGRA[r['id']]} ({r['peso']} {'ponto' if r['peso'] == 1 else 'pontos'})" for r in perfil["pontuacao"]["regras"]]
    evitar = [TEXTO_EXCLUSAO[e] for e in perfil["exclusoes"] if e not in ("concorrente", "categoria")]
    if "concorrente" in perfil["exclusoes"]:
        evitar.append("concorrentes (" + _lista_em_texto(perfil["exclusoes_concorrentes"]) + ")")
    if "categoria" in perfil["exclusoes"]:
        evitar.append("categorias (" + _lista_em_texto(perfil["exclusoes_categorias"]) + ")")
    area = perfil["conformidade"]["restricoes"]
    if area == "nao":
        area_texto = "não tem regras de publicidade ou de abordagem"
    elif area == "nao sei":
        area_texto = "você não sabe se tem regras de publicidade ou de abordagem (o painel vai mostrar um aviso)"
    else:
        area_texto = "tem regras de publicidade ou de abordagem: " + area.removeprefix("sim: ").removeprefix("sim") + " (o painel vai mostrar um aviso)"
    linhas = [
        f"Você vende: {neg['oferta']}",
        f"Seu nome: {neg['nome']}" + (f", da empresa {neg['empresa']}." if neg.get("empresa") else "."),
        f"Seu cliente ideal: {_lista_em_texto(cli['tipos'])}. Porte: {ROTULO_PORTE.get(cli['porte'], cli['porte'])}.",
        f"Você atende em {_lista_em_texto(cli['regioes'])}, com {ROTULO_ATENDIMENTO.get(neg['atendimento'], neg['atendimento'])}.",
        "Um negócio ganha pontos por: " + (_lista_em_texto(regras) or "nenhuma regra") + ".",
        "Você quer evitar: " + (_lista_em_texto(evitar) or "nada") + ".",
        f"Você prefere abordar por {_lista_em_texto(ROTULO_CANAL.get(c, c) for c in ab['canais'])}, em tom {ROTULO_TOM.get(ab['tom'], ab['tom'])}.",
        f"Sua oferta de entrada é: {ab['oferta_entrada']}.",
        f"Você consegue fazer {ROTULO_VOLUME.get(ab['volume_semana'], ab['volume_semana'])} contatos por semana.",
        f"Sua área {area_texto}.",
    ]
    if cli.get("exemplo"):
        linhas.insert(4, f"Seu melhor cliente até hoje: {cli['exemplo'].rstrip('.')}.")
    return "\n".join(f"- {l}" for l in linhas)


def gravar_perfil(perfil, caminho, refazer=False):
    """Grava com segurança. Devolve (ok, mensagem). Com `refazer`, o perfil antigo vira perfil.anterior.json."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.exists():
        if not refazer:
            return False, ("Já existe um perfil. Para trocar por este, peça \"refazer perfil\": o antigo fica guardado "
                           "como perfil.anterior.json.")
        shutil.copy2(caminho, caminho.with_name("perfil.anterior.json"))
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_text(json.dumps(perfil, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporario, caminho)
    return True, "Perfil gravado."


# ---------------------------------------------------------------- linha de comando

def _imprimir(dados):
    print(json.dumps(dados, ensure_ascii=False, indent=2))


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Monta o perfil.json a partir das respostas da entrevista.")
    p.add_argument("comando", choices=["estado", "resumo", "montar"])
    p.add_argument("--pasta-dados", default=str(RAIZ / "dados"))
    p.add_argument("--refazer", action="store_true", help="troca um perfil que já existe (o antigo fica guardado)")
    args = p.parse_args(argv)
    pasta = Path(args.pasta_dados)
    resp, erros_arquivo = carregar_respostas(pasta / "respostas.json")
    if erros_arquivo:
        _imprimir({"ok": False, "erros": erros_arquivo})
        return 1
    if args.comando == "estado":
        _imprimir({"ok": True, **estado(resp)})
        return 0
    perfil, erros, avisos = montar(resp)
    if erros:
        _imprimir({"ok": False, "erros": erros, "avisos": avisos, "faltam": estado(resp)["faltam"]})
        return 1
    if args.comando == "resumo":
        _imprimir({"ok": True, "resumo": resumo(perfil), "avisos": avisos,
                   "proximo_passo": "Mostre o resumo e só rode \"montar\" depois de a pessoa dizer \"confirmo\"."})
        return 0
    ok, mensagem = gravar_perfil(perfil, pasta / "perfil.json", refazer=args.refazer)
    _imprimir({"ok": ok, "mensagem": mensagem, "avisos": avisos, "perfil": str(pasta / "perfil.json")})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
