"""Faz uma busca de leads pelo terminal: motor, limpeza, nota e lista.

Uso (com o motor ligado por `docker compose up -d`):
    python kit/buscar.py --categoria padaria --cidade Sobradinho --uf DF
"""
import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from kit import banco, limpeza, motor as motor_mod, pontuacao, validar_perfil  # noqa: E402
from kit.geocodificar import ErroGeocodificacao, Geocodificador  # noqa: E402

DADOS = RAIZ / "dados"


def _tabela(resultados, saida, limite):
    saida(f"{'Nota':<5}{'Pts':>4}  {'Negócio':<34}{'Telefone':<18}Por quê")
    for r in resultados[:limite]:
        l = r["lead"]
        motivos = ", ".join(r["motivos"]) or "nenhuma regra do seu perfil bateu"
        saida(f"{r['letra']:<5}{r['nota']:>4}  {l['nome'][:32]:<34}{(l['telefone'] or '-')[:16]:<18}{motivos}")
    if len(resultados) > limite:
        saida(f"... e mais {len(resultados) - limite}. Use --limite para ver mais.")


def executar(args, motor, geo, saida=print):
    """Roda a busca inteira. Devolve 0 se deu certo e 1 se deu erro (com mensagem em portugues)."""
    perfil, erros, avisos = validar_perfil.carregar(args.perfil)
    for a in avisos:
        saida(f"Aviso: {a}")
    if erros:
        for e in erros:
            saida(f"Erro: {e}")
        return 1
    if not motor.no_ar():
        saida("O motor de busca não está ligado. Ligue com: docker compose up -d "
              "(espere uns 20 segundos e tente de novo).")
        return 1

    Path(args.banco).parent.mkdir(parents=True, exist_ok=True)
    conn = banco.abrir(args.banco)
    busca_id = None
    try:
        saida(f"Procurando '{args.categoria}' em {args.cidade}-{args.uf} (busca {args.tamanho})...")
        lat, lon = geo.buscar(args.cidade, args.uf)
        palavra = f"{args.categoria} em {args.cidade} {args.uf}"
        pedido = motor.montar_pedido(palavra, lat, lon, args.tamanho, args.email)
        busca_id = banco.criar_busca(conn, args.categoria, args.cidade, args.uf, args.tamanho,
                                     pedido, args.email)
        job = motor.criar_job(pedido)
        banco.atualizar_busca(conn, busca_id, job_id=job, status="working")
        saida("Busca enviada ao motor. A primeira vez pode demorar. Não feche esta janela.")
        motor.esperar(job, ao_esperar=lambda s: saida(f"  esperando o motor... {int(s)} s"))
        achados, ignoradas = limpeza.ler_csv(motor.baixar_csv(job))
        banco.salvar_leads(conn, busca_id, achados, args.cidade, args.uf, args.email)
        banco.atualizar_busca(conn, busca_id, status="ok", total_leads=len(achados))

        # Avalia o banco inteiro: "possivel rede" depende dos leads de todas as buscas.
        todos = banco.todos_os_leads(conn)
        avaliados = pontuacao.avaliar_todos(todos, perfil, args.email)
        banco.gravar_notas(conn, {r["lead"]["chave"]: r for r in avaliados})
        desta = {l["chave"] for l in achados}
        mostrar = [r for r in avaliados if r["lead"]["chave"] in desta]
    except (motor_mod.ErroMotor, limpeza.ErroCSV, ErroGeocodificacao) as e:
        if busca_id is not None:
            banco.atualizar_busca(conn, busca_id, status="erro", erro=str(e))
        saida(f"Erro: {e}")
        return 1
    finally:
        conn.close()

    ficam = [r for r in mostrar if r["excluido_por"] is None]
    fora = [r for r in mostrar if r["excluido_por"] is not None]
    saida("")
    saida(f"Achei {len(achados)} negócios: {len(ficam)} na lista e {len(fora)} excluídos pelo seu perfil.")
    if ignoradas:
        saida(f"({ignoradas} linhas sem nome foram ignoradas.)")
    saida("")
    _tabela(ficam, saida, args.limite)
    if fora:
        saida("")
        saida("Excluídos:")
        for r in fora:
            saida(f"  {r['lead']['nome'][:40]:<42}{r['excluido_por']}")
    saida("")
    saida(f"Tudo foi salvo em {args.banco}.")
    return 0


def ler_argumentos(argv=None):
    p = argparse.ArgumentParser(description="Busca leads no Google Maps pelo motor local.")
    p.add_argument("--categoria", required=True, help='tipo de negócio, por exemplo "padaria"')
    p.add_argument("--cidade", required=True)
    p.add_argument("--uf", required=True, help="sigla do estado, por exemplo DF")
    p.add_argument("--tamanho", choices=sorted(motor_mod.TAMANHOS), default="rapida")
    p.add_argument("--email", action="store_true", help="busca e-mails também (fica mais lenta)")
    p.add_argument("--limite", type=int, default=20, help="quantos leads mostrar")
    p.add_argument("--perfil", default=str(DADOS / "perfil.json"))
    p.add_argument("--banco", default=str(DADOS / "leads.db"))
    p.add_argument("--motor", default=motor_mod.URL_PADRAO)
    args = p.parse_args(argv)
    args.uf = args.uf.strip().upper()
    return args


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = ler_argumentos(argv)
    try:
        motor = motor_mod.Motor(args.motor)
    except motor_mod.ErroMotor as e:
        print(f"Erro: {e}")
        return 1
    geo = Geocodificador(arquivo_cache=DADOS / "cache_geocodificacao.json")
    return executar(args, motor, geo)


if __name__ == "__main__":
    sys.exit(main())
