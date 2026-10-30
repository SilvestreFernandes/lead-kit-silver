"""Valida o perfil.json. Sem IA: so regras fixas. Mensagens em portugues simples."""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ESQUEMA = json.loads((RAIZ / "entrevista" / "esquema.json").read_text(encoding="utf-8"))
REGRAS = json.loads((RAIZ / "kit" / "regras.json").read_text(encoding="utf-8"))

MARCADOR = re.compile(r"\{([^{}]*)\}")
SAIDA = re.compile(
    r"(n[ãa]o escrevo mais|n[ãa]o (te )?(escrevo|envio|mando)|se n[ãa]o fizer sentido"
    r"|[ée] s[óo] avisar|pode pedir pra eu parar|parar de receber)", re.I)


def _pegar(perfil, caminho):
    valor = perfil
    for parte in caminho.split("."):
        if not isinstance(valor, dict) or parte not in valor:
            return None
        valor = valor[parte]
    return valor


def _achar_sensiveis(valor, achados, trilha=""):
    if isinstance(valor, dict):
        for chave, v in valor.items():
            if str(chave).lower() in ESQUEMA["campos_sensiveis"]:
                achados.append(f"{trilha}{chave}")
            _achar_sensiveis(v, achados, f"{trilha}{chave}.")
    elif isinstance(valor, list):
        for i, v in enumerate(valor):
            _achar_sensiveis(v, achados, f"{trilha}{i}.")


def _remover_sensiveis(valor):
    if isinstance(valor, dict):
        for chave in [k for k in valor if str(k).lower() in ESQUEMA["campos_sensiveis"]]:
            del valor[chave]
        for v in valor.values():
            _remover_sensiveis(v)
    elif isinstance(valor, list):
        for v in valor:
            _remover_sensiveis(v)


def validar(perfil):
    """Devolve (perfil_corrigido, erros, avisos). Erros impedem o uso; avisos foram ajustados."""
    erros, avisos = [], []
    if not isinstance(perfil, dict):
        return {}, ["O perfil não é um objeto JSON. Refaça a entrevista."], []
    perfil = json.loads(json.dumps(perfil))

    if perfil.get("versao") != ESQUEMA["versao_atual"]:
        erros.append(f"Versão do perfil desconhecida ({perfil.get('versao')!r}). Refaça a entrevista.")

    for caminho in ESQUEMA["obrigatorios"]:
        if _pegar(perfil, caminho) in (None, "", []):
            erros.append(f"Falta preencher: {caminho}.")

    if _pegar(perfil, "cliente.porte") not in (None, "", *ESQUEMA["portes"]):
        erros.append("O porte do cliente precisa ser: " + ", ".join(ESQUEMA["portes"]) + ".")
    if _pegar(perfil, "abordagem.tom") not in (None, "", *ESQUEMA["tons"]):
        erros.append("O tom precisa ser: " + ", ".join(ESQUEMA["tons"]) + ".")
    for canal in _pegar(perfil, "abordagem.canais") or []:
        if canal not in ESQUEMA["canais"]:
            erros.append(f"Canal desconhecido: {canal}.")

    pont = perfil.setdefault("pontuacao", {})
    boas = []
    for regra in pont.get("regras") or []:
        rid = regra.get("id") if isinstance(regra, dict) else None
        if rid not in REGRAS["regras"]:
            avisos.append(f"A regra {rid!r} não existe e foi removida.")
            continue
        peso = regra.get("peso")
        if isinstance(peso, bool) or not isinstance(peso, int):
            avisos.append(f"O peso da regra {rid} não era um número inteiro e foi trocado pelo padrão.")
            peso = REGRAS["regras"][rid]["peso"]
        elif not ESQUEMA["peso_minimo"] <= peso <= ESQUEMA["peso_maximo"]:
            ajustado = min(max(peso, ESQUEMA["peso_minimo"]), ESQUEMA["peso_maximo"])
            avisos.append(f"O peso da regra {rid} ficou fora de 0 a 5 e foi ajustado para {ajustado}.")
            peso = ajustado
        boas.append({"id": rid, "peso": peso})
    pont["regras"] = boas

    a, b = pont.get("corte_a"), pont.get("corte_b")
    if (a is None) != (b is None) or (a is not None and not a > b):
        avisos.append("Os cortes A e B estavam errados (A precisa ser maior que B). Foram recalculados.")
        pont.pop("corte_a", None)
        pont.pop("corte_b", None)

    for nome, modelo in (perfil.get("mensagens") or {}).items():
        for marcador in MARCADOR.findall(modelo):
            if marcador not in ESQUEMA["marcadores"]:
                erros.append(f"A mensagem de {nome} usa o marcador inválido {{{marcador}}}.")
        if not SAIDA.search(modelo):
            erros.append(f"A mensagem de {nome} precisa de uma saída clara, por exemplo "
                         "\"se não fizer sentido, é só avisar que não escrevo mais\".")

    sensiveis = []
    _achar_sensiveis(perfil, sensiveis)
    for caminho in sensiveis:
        avisos.append(f"O campo {caminho} parece dado sensível e foi removido.")
    if sensiveis:
        _remover_sensiveis(perfil)

    perfil.setdefault("exclusoes_concorrentes", [])
    return perfil, erros, avisos


def carregar(caminho):
    """Le o arquivo e valida. Devolve (perfil, erros, avisos)."""
    caminho = Path(caminho)
    if not caminho.exists():
        return {}, [f"Não achei o perfil em {caminho}. Rode a entrevista na sua IA."], []
    try:
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {}, [f"O perfil não é um JSON válido (linha {e.lineno}). Corrija ou refaça a entrevista."], []
    return validar(bruto)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    caminho = argv[0] if argv else RAIZ / "dados" / "perfil.json"
    _, erros, avisos = carregar(caminho)
    for a in avisos:
        print("Aviso:", a)
    for e in erros:
        print("Erro:", e)
    if not erros:
        print("Perfil válido.")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
