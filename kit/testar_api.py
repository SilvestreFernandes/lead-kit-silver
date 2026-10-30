"""Testa a API do servidor local pelo terminal, sem curl e sem JSON escapado.

Com o servidor ligado (`python kit/servidor.py`), em outro terminal:
    python kit/testar_api.py estado
    python kit/testar_api.py buscar --categoria padaria --cidade Sobradinho --uf DF
    python kit/testar_api.py leads --busca 1
    python kit/testar_api.py lead 3
    python kit/testar_api.py marcar 3 --status contatado --anotacao "ligar terça"
    python kit/testar_api.py reavaliar
    python kit/testar_api.py exportar --arquivo leads.csv

O token vem da própria página inicial do servidor, como no painel.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PORTA_PADRAO = 8787


class ErroDaApi(Exception):
    pass


class Cliente:
    def __init__(self, porta=PORTA_PADRAO):
        self.base = f"http://127.0.0.1:{porta}"
        self._token = None

    def _abrir(self, req):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            corpo = e.read().decode("utf-8", "replace")
            try:
                dados = json.loads(corpo)
                mensagem = dados.get("erro", corpo)
                for item in dados.get("erros", []):
                    mensagem += "\n  - " + item
            except json.JSONDecodeError:
                mensagem = corpo[:200]
            raise ErroDaApi(f"O servidor respondeu {e.code}: {mensagem}")
        except (urllib.error.URLError, OSError):
            raise ErroDaApi("Não consegui falar com o servidor. Ligue ele com: python kit/servidor.py")

    @property
    def token(self):
        if self._token is None:
            pagina = self._abrir(urllib.request.Request(self.base + "/")).decode("utf-8")
            achou = re.search(r'name="token" content="([^"]+)"', pagina)
            if not achou:
                raise ErroDaApi("Não achei o token na página inicial do servidor.")
            self._token = achou.group(1)
        return self._token

    def ler(self, caminho, consulta=None):
        url = self.base + caminho
        if consulta:
            url += "?" + urllib.parse.urlencode({k: v for k, v in consulta.items() if v is not None})
        return json.loads(self._abrir(urllib.request.Request(url)))

    def baixar(self, caminho, consulta=None):
        url = self.base + caminho
        if consulta:
            url += "?" + urllib.parse.urlencode({k: v for k, v in consulta.items() if v is not None})
        return self._abrir(urllib.request.Request(url, headers={"X-Token": self.token}))

    def escrever(self, metodo, caminho, corpo):
        req = urllib.request.Request(
            self.base + caminho, data=json.dumps(corpo).encode("utf-8"), method=metodo,
            headers={"Content-Type": "application/json", "X-Token": self.token})
        return json.loads(self._abrir(req))


def mostrar_leads(leads, saida=print):
    saida(f"{'Nota':<5}{'Pts':>4}  {'Negócio':<34}{'Telefone':<18}Por quê")
    for l in leads:
        motivos = ", ".join(l["motivos"]) or "nenhuma regra do seu perfil bateu"
        if l["excluido_por"]:
            motivos = f"EXCLUÍDO: {l['excluido_por']}"
        saida(f"{l['letra']:<5}{l['nota']:>4}  {l['nome'][:32]:<34}{(l['telefone'] or '-')[:16]:<18}{motivos}")


def comando_estado(c, a, saida):
    d = c.ler("/api/estado")
    saida(f"Versão do kit: {d['versao_kit']}")
    saida(f"Motor de busca: {'ligado' if d['motor_no_ar'] else 'DESLIGADO (docker compose up -d)'}")
    p = d["perfil"]
    saida(f"Perfil: {'válido' if p['valido'] else 'NÃO válido' if p['existe'] else 'não existe'}")
    for e in p["erros"]:
        saida(f"  - {e}")
    saida(f"Busca em andamento: {d['busca_em_andamento'] or 'nenhuma'}")


def comando_buscar(c, a, saida):
    criada = c.escrever("POST", "/api/buscas", {
        "categoria": a.categoria, "cidade": a.cidade, "uf": a.uf, "tamanho": a.tamanho, "email": a.email})
    busca_id = criada["id"]
    saida(f"Busca {busca_id} criada. A primeira vez pode demorar. Não feche esta janela.")
    ultima, inicio = None, time.time()
    while True:
        d = c.ler(f"/api/buscas/{busca_id}")
        if d["status"] in ("ok", "erro"):
            break
        if d["etapa"] != ultima:
            saida(f"  {d['etapa'] or 'começando'}...")
            ultima = d["etapa"]
        if time.time() - inicio > 1500:
            raise ErroDaApi("A busca passou de 25 minutos. Veja a janela do servidor.")
        time.sleep(2)
    if d["status"] == "erro":
        raise ErroDaApi(f"A busca deu erro: {d['erro']}")
    saida(f"Busca {busca_id} terminou: {d['total_leads']} negócios.")
    saida("")
    leads = c.ler("/api/leads", {"busca": busca_id, "limite": a.limite})
    mostrar_leads(leads["leads"], saida)
    if leads["total"] > len(leads["leads"]):
        saida(f"... e mais {leads['total'] - len(leads['leads'])}. Use: leads --busca {busca_id} --limite 100")


def comando_leads(c, a, saida):
    d = c.ler("/api/leads", {"busca": a.busca, "letra": a.letra, "status": a.status, "q": a.q,
                             "excluidos": a.excluidos, "limite": a.limite})
    saida(f"{d['total']} leads (mostrando {len(d['leads'])}).")
    mostrar_leads(d["leads"], saida)


def comando_lead(c, a, saida):
    d = c.ler(f"/api/leads/{a.id}")
    saida(f"{d['nome']}  [{d['letra']}, {d['nota']} pontos]  status: {d['status']}")
    saida(f"Endereço: {d['endereco']}")
    saida(f"Telefone: {d['telefone'] or '-'}   Site: {d['site'] or '-'}")
    saida("Motivos: " + (", ".join(d["motivos"]) or "nenhum"))
    if d["excluido_por"]:
        saida("Excluído por: " + d["excluido_por"])
    for canal, m in d["mensagens"].items():
        rotulo = " (modelo provisório do kit)" if m["padrao"] else ""
        saida(f"\nMensagem de {canal}{rotulo}:\n{m['texto']}")


def comando_marcar(c, a, saida):
    corpo = {k: v for k, v in (("status", a.status), ("anotacao", a.anotacao)) if v is not None}
    d = c.escrever("PATCH", f"/api/leads/{a.id}", corpo)
    saida(f"Lead {d['id']}: status {d['status']}, anotação {d['anotacao']!r}")


def comando_reavaliar(c, a, saida):
    d = c.escrever("POST", "/api/leads/reavaliar", {})
    saida(f"{d['leads']} leads reavaliados: {d['por_letra']}")


def comando_exportar(c, a, saida):
    dados = c.baixar("/api/exportar", {"letra": a.letra, "excluidos": a.excluidos})
    with open(a.arquivo, "wb") as f:
        f.write(dados)
    saida(f"Salvei {len(dados)} bytes em {a.arquivo}")


def montar_parser():
    p = argparse.ArgumentParser(description="Testa a API do servidor local.")
    p.add_argument("--porta", type=int, default=PORTA_PADRAO)
    sub = p.add_subparsers(dest="comando", required=True)
    sub.add_parser("estado").set_defaults(f=comando_estado)
    b = sub.add_parser("buscar")
    b.add_argument("--categoria", required=True)
    b.add_argument("--cidade", required=True)
    b.add_argument("--uf", required=True)
    b.add_argument("--tamanho", default="rapida")
    b.add_argument("--email", action="store_true")
    b.add_argument("--limite", type=int, default=20)
    b.set_defaults(f=comando_buscar)
    l = sub.add_parser("leads")
    l.add_argument("--busca", type=int)
    l.add_argument("--letra")
    l.add_argument("--status")
    l.add_argument("--q")
    l.add_argument("--excluidos", default="nao")
    l.add_argument("--limite", type=int, default=20)
    l.set_defaults(f=comando_leads)
    um = sub.add_parser("lead")
    um.add_argument("id", type=int)
    um.set_defaults(f=comando_lead)
    m = sub.add_parser("marcar")
    m.add_argument("id", type=int)
    m.add_argument("--status")
    m.add_argument("--anotacao")
    m.set_defaults(f=comando_marcar)
    sub.add_parser("reavaliar").set_defaults(f=comando_reavaliar)
    e = sub.add_parser("exportar")
    e.add_argument("--arquivo", default="leads.csv")
    e.add_argument("--letra")
    e.add_argument("--excluidos", default="nao")
    e.set_defaults(f=comando_exportar)
    return p


def main(argv=None, saida=print):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = montar_parser().parse_args(argv)
    try:
        args.f(Cliente(args.porta), args, saida)
    except ErroDaApi as e:
        saida(f"Erro: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
