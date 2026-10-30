"""Servidor de demonstração do painel: dados FICTICIOS, motor e mapas simulados, pasta temporaria.

Serve para ver o painel em cada estado sem Docker e sem tocar em dados/ de verdade.

    python testes/demo_painel.py                       (painel normal, com leads fictícios)
    python testes/demo_painel.py --estado motor_desligado
    python testes/demo_painel.py --estado perfil_ausente
    python testes/demo_painel.py --estado perfil_invalido
    python testes/demo_painel.py --estado sem_leads        (nenhuma busca feita ainda)
    python testes/demo_painel.py --estado muitos           (650 leads, para testar "Mostrar mais")
    python testes/demo_painel.py --estado regulado         (perfil de area regulada: aviso de conformidade)
    python testes/demo_painel.py --estado tudo_excluido    (todos os leads ficam fora da lista)
    python testes/demo_painel.py --abrir                   (abre o painel no navegador)
    python testes/demo_painel.py --porta 8790
"""
import argparse
import json
import shutil
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from kit import banco, limpeza, servidor  # noqa: E402
from testes.fixtures import (GeoDeMentira, MotorDeMentira, csv_texto, leads_em_massa, linha,  # noqa: E402
                             perfil_ficticio)

ESTADOS = ("normal", "motor_desligado", "perfil_ausente", "perfil_invalido", "sem_leads", "busca_lenta",
           "muitos", "regulado", "tudo_excluido")


def leads_de_demonstracao():
    return [
        linha(1, title="Padaria Pão Quente", category="Padaria", address="Quadra 3 AE 5, Sobradinho - DF",
              website="", phone="(61) 99322-4592", review_count="312", review_rating="4.8"),
        linha(2, title="Café Estação", category="Cafeteria", address="CL 114, Asa Norte, Brasília - DF",
              website="https://www.instagram.com/cafeestacao.exemplo", phone="(61) 98402-5588",
              review_count="85", review_rating="4.6"),
        linha(3, title="Empório da Serra", category="Mercearia", address="Rua das Flores 45, Sobradinho - DF",
              website="https://emporio.exemplo.invalid", phone="(61) 3387-2235", review_count="40",
              review_rating="4.1"),
        linha(4, title="Doces da Vovó", category="Confeitaria", address="QD 09 CL 06, Sobradinho - DF",
              website="", phone="(61) 99839-7221", review_count="12", review_rating="3.7"),
        linha(5, title="Pizzaria Forno a Lenha", category="Pizzaria", address="Av. Principal 100, Brasília - DF",
              website="https://forno.exemplo.invalid", phone="(61) 3453-5030", review_count="900",
              review_rating="4.5", order_online='[{"link":"x"}]'),
        linha(6, title='<img src=x onerror=alert(1)> Teste de segurança', category="<b>Padaria</b>",
              address="Rua <script>alert(1)</script>, 1", website="javascript:alert(1)",
              phone="(61) 99111-0006", review_count="55", review_rating="4.7"),
        linha(7, title="Sem Telefone Fictício", category="Mercearia", address="Rua Sem Fone 7, Sobradinho - DF",
              website="", phone="", review_count="30", review_rating="4.2"),
        linha(8, title="Rede Fictícia - Asa Sul", category="Padaria", address="CLS 1, Asa Sul - DF",
              phone="(61) 3300-0001"),
        linha(9, title="Rede Fictícia - Asa Norte", category="Padaria", address="CLN 2, Asa Norte - DF",
              phone="(61) 3300-0002"),
        linha(10, title="Rede Fictícia - Sudoeste", category="Padaria", address="CLSW 3, Sudoeste - DF",
              phone="(61) 3300-0003"),
    ]


def montar(estado, porta):
    pasta = Path(tempfile.mkdtemp(prefix="lead-kit-demo-"))
    dados = pasta / "dados"
    dados.mkdir()
    if estado == "perfil_invalido":
        perfil = perfil_ficticio()
        perfil["negocio"]["oferta"] = ""
        perfil["mensagens"]["whatsapp"] = "Oi {apelido}"
        (dados / "perfil.json").write_text(json.dumps(perfil), encoding="utf-8")
    elif estado != "perfil_ausente":
        perfil = perfil_ficticio()
        perfil["negocio"].update({"nome": "Silvestre", "empresa": "BrandForge"})
        if estado == "regulado":
            perfil["conformidade"] = {"restricoes": "sim: advocacia (OAB)"}
        (dados / "perfil.json").write_text(json.dumps(perfil), encoding="utf-8")
    if estado not in ("sem_leads", "perfil_ausente"):
        conn = banco.abrir(str(dados / "leads.db"))
        bid = banco.criar_busca(conn, "padaria", "Brasília", "DF", "rapida", {}, False)
        if estado == "muitos":
            linhas = leads_de_demonstracao() + leads_em_massa(640)
        elif estado == "tudo_excluido":
            linhas = [linha(n, title=f"Sem Telefone Fictício {n}", phone="") for n in range(1, 6)]
        else:
            linhas = leads_de_demonstracao()
        banco.salvar_leads(conn, bid, limpeza.ler_csv(csv_texto(linhas))[0], "Brasília", "DF", False)
        banco.atualizar_busca(conn, bid, status="ok", total_leads=len(linhas))
        if estado == "normal":  # um lead ja acompanhado, para o painel mostrar status e anotacao
            lid = conn.execute("SELECT id FROM leads WHERE nome = ?", ("Doces da Vovó",)).fetchone()[0]
            banco.atualizar_lead(conn, lid, status="contatado", anotacao="Pediu para ligar na segunda")
        conn.close()
    motor = MotorDeMentira(ligado=estado != "motor_desligado")
    if estado == "busca_lenta":
        motor.segurar = threading.Event()  # a busca fica "esperando o motor" até alguem soltar
    srv = servidor.Servidor(porta=porta, pasta_dados=dados, motor=motor, geo=GeoDeMentira(),
                            dormir=lambda s: None)
    srv.pasta_temporaria = pasta  # quem sobe a demonstracao apaga isto ao terminar
    return srv


def main(argv=None):
    p = argparse.ArgumentParser(description="Painel de demonstração (dados fictícios).")
    p.add_argument("--estado", choices=ESTADOS, default="normal")
    p.add_argument("--porta", type=int, default=8788)
    p.add_argument("--abrir", action="store_true", help="abre o painel no navegador")
    args = p.parse_args(argv)
    srv = montar(args.estado, args.porta)
    url = f"http://127.0.0.1:{srv.porta}"
    print(f"Demonstração ({args.estado}) em {url}  (Ctrl+C para parar)", flush=True)
    print("Dados 100% fictícios, numa pasta temporária. Nada é buscado de verdade.", flush=True)
    if args.abrir:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        shutil.rmtree(srv.pasta_temporaria, ignore_errors=True)


if __name__ == "__main__":
    main()
