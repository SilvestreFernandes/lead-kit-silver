"""Monta o .zip do pacote que o comprador baixa. Ferramenta de quem constrói o kit, não vai dentro do pacote.

    python construcao/montar_pacote.py                 monta dist/<nome>-<versao>.zip
    python construcao/montar_pacote.py --completo      falha se ainda faltar alguma peça das instruções para a IA
    python construcao/montar_pacote.py --saida pasta   escolhe a pasta de saída

O que entra: LICENSE, CREDITS.md, docker-compose.yml, kit/ (código e painel), entrevista/ e, se existirem, os guias de
docs/. Tudo que está em pacote/ (CLAUDE.md e AGENTS.md do comprador, a skill, o prompt de instalação, iniciar.bat e
iniciar.sh) vai para a raiz do .zip, sem o prefixo "pacote/".

O que NUNCA entra: dados da pessoa (dados/, perfil.json, leads.db, CSV, .env), o planejamento, os testes, as ferramentas de
desenvolvimento (Impeccable em .claude/agents e .claude/skills/impeccable), prints, o PRODUCT.md e o CLAUDE.md de
desenvolvimento. Se algum arquivo proibido aparecer no meio do caminho, o script para.

O .zip é determinístico: mesma entrada, mesmo arquivo (mesma ordem e datas fixas), então dá para comparar dois pacotes.
"""
import argparse
import fnmatch
import hashlib
import re
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from kit import produto, servidor  # noqa: E402

DATA_FIXA = (2026, 1, 1, 0, 0, 0)

# O que vem da raiz do repositório: (caminho relativo, é pasta?)
ENTRAM = [("LICENSE", False), ("CREDITS.md", False), ("docker-compose.yml", False), ("kit", True), ("entrevista", True)]
GUIAS_OPCIONAIS = ["docs/guia-de-uso.md", "docs/abordagem-responsavel.md"]
PASTA_DO_COMPRADOR = "pacote"

# Nunca entram no .zip, de onde quer que venham.
PROIBIDOS = [
    "dados/*", "*/dados/*", "*.csv", "*perfil.json", "*perfil.anterior.json", "*leads.db*", "*.env", "*.db", "*.sqlite*",
    "*/__pycache__/*", "*.pyc", ".git/*", ".claude/agents/*", ".claude/skills/impeccable/*", ".impeccable/*",
    "prints/*", "PRODUCT.md", "testes/*", "docs/planejamento/*", "docs/design/*", "construcao/*", "dist/*",
    ".playwright-mcp/*", "ferramentas/*", "instalacao.json", "*/instalacao.json",
]

# Peças que o pacote final precisa ter (caminhos dentro do .zip). Enquanto faltarem, o script avisa.
PECAS_DAS_INSTRUCOES = [
    "CLAUDE.md", "AGENTS.md", ".claude/skills/lead-kit/SKILL.md", "INSTALAR.md", "iniciar.bat", "iniciar.sh",
]
# Sem estas o pacote não serve nem para ensaio.
INDISPENSAVEIS = [
    "LICENSE", "CREDITS.md", "docker-compose.yml", "kit/servidor.py", "kit/motor.py", "kit/validar_perfil.py",
    "kit/painel/index.html", "kit/painel/fontes/LICENCA-IBM-Plex.txt", "entrevista/esquema.json",
]


def proibido(caminho_no_zip):
    p = caminho_no_zip.replace("\\", "/")
    return any(fnmatch.fnmatch(p, padrao) or fnmatch.fnmatch("/" + p, "*/" + padrao.lstrip("*/")) for padrao in PROIBIDOS)


def _arquivos_de(pasta):
    for p in sorted(pasta.rglob("*")):
        if p.is_file():
            yield p


def coletar(raiz=RAIZ):
    """[(caminho dentro do .zip, caminho no disco)], já na ordem final."""
    itens = {}
    for relativo, eh_pasta in ENTRAM:
        origem = raiz / relativo
        if not origem.exists():
            continue
        for p in (_arquivos_de(origem) if eh_pasta else [origem]):
            itens[p.relative_to(raiz).as_posix()] = p
    for guia in GUIAS_OPCIONAIS:
        if (raiz / guia).is_file():
            itens[guia] = raiz / guia
    pacote = raiz / PASTA_DO_COMPRADOR
    if pacote.is_dir():
        for p in _arquivos_de(pacote):
            itens[p.relative_to(pacote).as_posix()] = p  # a raiz do .zip é a pasta pacote/
    # lixo de execução nunca entra, mas não é erro (o Python cria __pycache__ sozinho)
    return [(nome, itens[nome]) for nome in sorted(itens)
            if "__pycache__" not in nome and not nome.endswith(".pyc")]


def verificar(itens):
    """Devolve (erros, avisos)."""
    nomes = [n for n, _ in itens]
    erros = [f"arquivo proibido no pacote: {n}" for n in nomes if proibido(n)]
    erros += [f"falta no pacote: {n}" for n in INDISPENSAVEIS if n not in nomes]
    avisos = [f"ainda falta: {n}" for n in PECAS_DAS_INSTRUCOES if n not in nomes]
    return erros, avisos


def nome_do_arquivo():
    slug = re.sub(r"[^a-z0-9]+", "-", produto.NOME.lower()).strip("-")
    return f"{slug}-{servidor.VERSAO}.zip"


def montar(destino_pasta, completo=False, raiz=RAIZ):
    itens = coletar(raiz)
    erros, avisos = verificar(itens)
    if completo:
        erros += avisos
        avisos = []
    if erros:
        return None, erros, avisos
    destino_pasta = Path(destino_pasta)
    destino_pasta.mkdir(parents=True, exist_ok=True)
    destino = destino_pasta / nome_do_arquivo()
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, origem in itens:
            info = zipfile.ZipInfo(nome, DATA_FIXA)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, origem.read_bytes())
    return destino, erros, avisos


def main(argv=None):
    p = argparse.ArgumentParser(description="Monta o .zip do pacote do comprador.")
    p.add_argument("--saida", default=str(RAIZ / "dist"))
    p.add_argument("--completo", action="store_true", help="falha se faltar alguma peça das instruções para a IA")
    args = p.parse_args(argv)
    destino, erros, avisos = montar(args.saida, completo=args.completo)
    for a in avisos:
        print("Aviso:", a)
    if erros:
        for e in erros:
            print("Erro:", e)
        return 1
    dados = destino.read_bytes()
    with zipfile.ZipFile(destino) as z:
        total = len(z.namelist())
    print(f"Pacote: {destino}")
    print(f"Arquivos: {total}  Tamanho: {len(dados) / 1024:.0f} KB  SHA-256: {hashlib.sha256(dados).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
