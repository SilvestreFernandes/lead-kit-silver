"""Servidor de demonstração do painel: dados FICTICIOS, motor e mapas simulados, pasta temporaria.

Serve para ver o painel em cada estado sem Docker e sem tocar em dados/ de verdade.
As buscas daqui sao de mentira: o "motor" devolve leads fictícios depois de uma demora (--demora).

    python testes\\demo_painel.py --abrir                    (painel normal, com leads fictícios)
    python testes\\demo_painel.py --estado buscando --abrir  (uma busca média já em andamento)
    python testes\\demo_painel.py --estado zero_resultado    (a última busca não trouxe nada)
    python testes\\demo_painel.py --estado erro_cidade       (cidade não encontrada)
    python testes\\demo_painel.py --estado erro_no_meio      (a busca falha no ponto 3 de 5)
    python testes\\demo_painel.py --estado motor_desligado   (Docker ligado, motor desligado)
    python testes\\demo_painel.py --estado docker_parado     (Docker desligado)
    python testes\\demo_painel.py --estado perfil_ausente
    python testes\\demo_painel.py --estado perfil_invalido
    python testes\\demo_painel.py --estado sem_leads         (nenhuma busca feita ainda)
    python testes\\demo_painel.py --estado muitos            (650 leads, para testar "Mostrar mais")
    python testes\\demo_painel.py --estado regulado          (perfil de área regulada: aviso de conformidade)
    python testes\\demo_painel.py --estado tudo_excluido     (todos os leads ficam fora da lista)
    python testes\\demo_painel.py --demora 12                (segundos de cada ponto da busca; padrão 3)
    python testes\\demo_painel.py --porta 8790               (outra porta, para ver dois estados juntos)
"""
import argparse
import json
import shutil
import sys
import tempfile
import threading
import time
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from kit import banco, buscar, diagnostico, limpeza, servidor, validar_perfil  # noqa: E402
from kit import motor as motor_mod  # noqa: E402
from kit.geocodificar import CidadeNaoEncontrada  # noqa: E402
from testes.fixtures import (GeoDeMentira, MotorDeMentira, csv_texto, leads_em_massa, linha,  # noqa: E402
                             perfil_ficticio)

ESTADOS = ("normal", "motor_desligado", "docker_parado", "perfil_ausente", "perfil_invalido", "sem_leads",
           "buscando", "zero_resultado", "erro_cidade", "erro_no_meio", "muitos", "regulado", "tudo_excluido")


class MotorLento(MotorDeMentira):
    """Motor falso que demora `atraso` segundos em cada ponto, para dar tempo de ver o progresso."""

    def __init__(self, atraso=3.0, **kwargs):
        super().__init__(**kwargs)
        self.atraso = atraso

    def esperar(self, job_id, intervalo=5, limite=None, ao_esperar=None):
        inicio = time.monotonic()
        while time.monotonic() - inicio < self.atraso:
            time.sleep(0.25)
            if ao_esperar:
                ao_esperar(time.monotonic() - inicio)
        return super().esperar(job_id, intervalo, limite, None)


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


def csvs_da_media():
    """Cinco CSVs fictícios que se sobrepõem, como pontos vizinhos de uma busca média."""
    base = leads_em_massa(100)
    return [csv_texto(base[a:a + 28]) for a in (0, 18, 36, 54, 72)]


def semear_busca(conn, categoria, cidade, uf, tamanho, status="ok", total=0, novos=0, ja_existiam=0,
                 fora_da_lista=0, erro=None, erro_tipo=None, minutos_atras=40, duracao_s=75):
    """Grava uma busca já terminada, como se tivesse rodado antes."""
    bid = banco.criar_busca(conn, categoria, cidade, uf, tamanho, {}, False)
    inicio = datetime.now() - timedelta(minutes=minutos_atras)
    fim = inicio + timedelta(seconds=duracao_s)
    conn.execute("UPDATE buscas SET criada_em=? WHERE id=?", (inicio.isoformat(timespec="seconds"), bid))
    banco.atualizar_busca(conn, bid, status=status, total_leads=total, novos=novos, ja_existiam=ja_existiam,
                          fora_da_lista=fora_da_lista, erro=erro, erro_tipo=erro_tipo,
                          terminou_em=fim.isoformat(timespec="seconds"))
    return bid


def montar(estado, porta, atraso=3.0):
    pasta = Path(tempfile.mkdtemp(prefix="lead-kit-demo-"))
    dados = pasta / "dados"
    dados.mkdir()
    perfil = perfil_ficticio()
    if estado == "perfil_invalido":
        perfil["negocio"]["oferta"] = ""
        perfil["mensagens"]["whatsapp"] = "Oi {apelido}"
        (dados / "perfil.json").write_text(json.dumps(perfil), encoding="utf-8")
    elif estado != "perfil_ausente":
        perfil["negocio"].update({"nome": "Silvestre", "empresa": "BrandForge"})
        perfil["cliente"].update({"tipos": ["padaria", "restaurante", "academia", "clínica de estética"],
                                  "regioes": ["Brasília-DF", "Sobradinho-DF", "Todo o Brasil"]})
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
        fora = 5 if estado == "tudo_excluido" else (4 if estado != "muitos" else 41)
        inicio = datetime.now() - timedelta(minutes=90)
        banco.atualizar_busca(conn, bid, status="ok", total_leads=len(linhas), novos=len(linhas), ja_existiam=0,
                              fora_da_lista=fora,
                              terminou_em=(inicio + timedelta(seconds=44)).isoformat(timespec="seconds"))
        conn.execute("UPDATE buscas SET criada_em=? WHERE id=?", (inicio.isoformat(timespec="seconds"), bid))
        if estado == "normal":  # um lead ja acompanhado, e buscas antigas para o historico
            lid = conn.execute("SELECT id FROM leads WHERE nome = ?", ("Doces da Vovó",)).fetchone()[0]
            banco.atualizar_lead(conn, lid, status="contatado", anotacao="Pediu para ligar na segunda")
            semear_busca(conn, "restaurantes", "Brasília", "DF", "media", total=88, novos=88, fora_da_lista=9,
                         minutos_atras=3000, duracao_s=340)
            semear_busca(conn, "academia", "Sobradinho", "DF", "rapida", total=14, novos=11, ja_existiam=3,
                         fora_da_lista=2, minutos_atras=1500, duracao_s=48)
            semear_busca(conn, "padaria", "Brasília", "DF", "rapida", total=16, novos=5, ja_existiam=11,
                         fora_da_lista=1, minutos_atras=300, duracao_s=44)
        if estado == "zero_resultado":
            semear_busca(conn, "padaria artesanal", "Cidade Imaginária", "DF", "rapida", total=0, novos=0,
                         minutos_atras=2, duracao_s=41)
        if estado == "erro_cidade":
            semear_busca(conn, "padaria", "Brasilia Nova", "DF", "rapida", status="erro", total=0, novos=0,
                         erro="Não achei a cidade Brasilia Nova-DF. Confira o nome e a sigla do estado.",
                         erro_tipo="cidade", minutos_atras=2, duracao_s=3)
        if estado == "erro_no_meio":
            semear_busca(conn, "restaurantes", "Brasília", "DF", "media", status="erro", total=36, novos=30,
                         ja_existiam=6, fora_da_lista=3,
                         erro="A busca parou no ponto 3 de 5. Os 36 negócios dos pontos anteriores foram salvos. "
                              "Motivo: O motor não está respondendo.",
                         erro_tipo="parcial", minutos_atras=4, duracao_s=170)
        conn.commit()
        conn.close()

    motor = MotorLento(atraso=atraso, ligado=estado not in ("motor_desligado", "docker_parado"))
    if estado == "zero_resultado":
        motor.csv = csv_texto([])
    geo = GeoDeMentira(CidadeNaoEncontrada("Não achei a cidade X-DF. Confira o nome e a sigla do estado.")
                       if estado == "erro_cidade" else None)

    def diagnostico_da_demo(m):
        if m.no_ar():
            return None
        e = "docker_parado" if estado == "docker_parado" else "motor_parado"
        return {"estado": e, **diagnostico.DIAGNOSTICOS[e]}

    srv = servidor.Servidor(porta=porta, pasta_dados=dados, motor=motor, geo=geo,
                            dormir=lambda s: time.sleep(min(1.0, atraso)), diagnostico=diagnostico_da_demo)
    srv.pasta_temporaria = pasta  # quem sobe a demonstracao apaga isto ao terminar

    # Cada ponto da busca media devolve uma lista diferente, que se sobrepoe a do vizinho.
    original = motor.baixar_csv
    csvs = csvs_da_media()

    def baixar(job_id):
        numero = int(job_id.removeprefix("job"))
        if motor.pedidos[numero - 1]["depth"] == motor_mod.TAMANHOS["media"]["depth"]:
            return csvs[(numero - 1) % len(csvs)]
        return original(job_id)

    motor.baixar_csv = baixar
    if estado == "erro_no_meio":
        motor.falha_a_partir_do_job = (3, motor_mod.ErroMotor("O motor não está respondendo."))

    if estado == "buscando":  # uma busca media ja rodando quando a demonstracao abre
        perfil_ok, _, _ = validar_perfil.carregar(dados / "perfil.json")
        with srv.banco() as conn:
            bid = buscar.iniciar_busca(conn, "restaurantes", "Brasília", "DF", "media", False)
        srv.busca_ativa = bid
        threading.Thread(target=srv.trabalho_da_busca, args=(bid, perfil_ok), daemon=True).start()
    return srv


def main(argv=None):
    p = argparse.ArgumentParser(description="Painel de demonstração (dados fictícios).")
    p.add_argument("--estado", choices=ESTADOS, default="normal")
    p.add_argument("--porta", type=int, default=8788)
    p.add_argument("--demora", type=float, default=None, help="segundos que cada ponto da busca demora (padrão: 3)")
    p.add_argument("--abrir", action="store_true", help="abre o painel no navegador")
    args = p.parse_args(argv)
    atraso = args.demora if args.demora is not None else (10.0 if args.estado == "buscando" else 3.0)
    srv = montar(args.estado, args.porta, atraso)
    url = f"http://127.0.0.1:{srv.porta}"
    print(f"Demonstração ({args.estado}) em {url}  (Ctrl+C para parar)", flush=True)
    print("Dados 100% fictícios, numa pasta temporária. Nenhuma busca de verdade é feita.", flush=True)
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
