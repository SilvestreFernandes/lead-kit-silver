"""Servidor de demonstração do painel: dados FICTICIOS, motor e mapas simulados, pasta temporaria.

Serve para ver o painel em cada estado sem Docker e sem tocar em dados/ de verdade.

    python testes/demo_painel.py                       (painel normal, com leads fictícios)
    python testes/demo_painel.py --estado motor_desligado
    python testes/demo_painel.py --estado perfil_ausente
    python testes/demo_painel.py --estado perfil_invalido
    python testes/demo_painel.py --estado sem_leads
    python testes/demo_painel.py --porta 8790
"""
import argparse
import json
import sys
import tempfile
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from kit import banco, limpeza, servidor  # noqa: E402
from testes.fixtures import GeoDeMentira, MotorDeMentira, csv_texto, linha, perfil_ficticio  # noqa: E402

ESTADOS = ("normal", "motor_desligado", "perfil_ausente", "perfil_invalido", "sem_leads", "busca_lenta")


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
              address="Rua <script>alert(1)</script>, 1", website="", phone="(61) 99111-0006",
              review_count="55", review_rating="4.7"),
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
        (dados / "perfil.json").write_text(json.dumps(perfil), encoding="utf-8")
    if estado not in ("sem_leads", "perfil_ausente"):
        conn = banco.abrir(str(dados / "leads.db"))
        bid = banco.criar_busca(conn, "padaria", "Brasília", "DF", "rapida", {}, False)
        banco.salvar_leads(conn, bid, limpeza.ler_csv(csv_texto(leads_de_demonstracao()))[0],
                           "Brasília", "DF", False)
        conn.close()
    motor = MotorDeMentira(ligado=estado != "motor_desligado")
    if estado == "busca_lenta":
        motor.segurar = threading.Event()  # a busca fica "esperando o motor" até alguem soltar
    return servidor.Servidor(porta=porta, pasta_dados=dados, motor=motor, geo=GeoDeMentira(),
                             dormir=lambda s: None)


def main(argv=None):
    p = argparse.ArgumentParser(description="Painel de demonstração (dados fictícios).")
    p.add_argument("--estado", choices=ESTADOS, default="normal")
    p.add_argument("--porta", type=int, default=8788)
    args = p.parse_args(argv)
    srv = montar(args.estado, args.porta)
    print(f"Demonstração ({args.estado}) em http://127.0.0.1:{srv.porta}  (Ctrl+C para parar)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
