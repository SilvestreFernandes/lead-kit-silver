"""Gera dados/exemplo-relatorio.xlsx com negocios FICTICIOS, usando o codigo atual do kit.

    python testes/gerar_exemplo_planilha.py

E a planilha de amostra do produto: 9 padarias imaginarias de Brasilia, com notas A, B e C e nenhum negocio
fora da lista. Nao le o seu banco de leads. Dados de teste de seguranca ficam so nos testes.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from kit import banco, consulta, limpeza, xlsx  # noqa: E402
from testes.fixtures import csv_texto, linha, perfil_ficticio  # noqa: E402


def leads_de_exemplo():
    """Nove padarias imaginarias de Brasilia. Nomes, enderecos e telefones nao existem."""
    return [
        linha(1, title="Padaria Flor do Trigo", category="Padaria", address="CLN 405 Bloco B, Asa Norte, Brasília - DF",
              website="", phone="(61) 98140-0101", review_count="214", review_rating="4.8"),
        linha(2, title="Panificadora Bom Gosto", category="Padaria", address="CRS 506 Bloco A, Asa Sul, Brasília - DF",
              website="https://www.instagram.com/padariabomgosto.exemplo", phone="(61) 98140-0102",
              review_count="96", review_rating="4.6"),
        linha(3, title="Pão & Prosa", category="Padaria", address="SQN 312 Bloco D, Asa Norte, Brasília - DF",
              website="", phone="(61) 98140-0103", review_count="38", review_rating="4.0"),
        linha(4, title="Sabor Mineiro Pães e Quitandas", category="Padaria", address="CLSW 103 Bloco C, Sudoeste, Brasília - DF",
              website="https://www.instagram.com/sabormineiro.exemplo", phone="(61) 3340-0104",
              review_count="120", review_rating="4.7"),
        linha(5, title="Padaria Esquina do Sabor", category="Padaria", address="SQS 215 Bloco G, Asa Sul, Brasília - DF",
              website="https://esquinadosabor.example", phone="(61) 98140-0105", review_count="150", review_rating="4.5"),
        linha(6, title="Doceria Santa Clara", category="Padaria", address="CLN 210 Bloco B, Asa Norte, Brasília - DF",
              website="https://santaclara.example", phone="(61) 3340-0106", review_count="70", review_rating="4.4"),
        linha(7, title="Padaria Ponto Quente", category="Padaria", address="SQN 108 Bloco A, Asa Norte, Brasília - DF",
              website="https://pontoquente.example", phone="(61) 3340-0107", review_count="310", review_rating="4.5"),
        linha(8, title="Confeitaria Doce Manhã", category="Confeitaria", address="CRN 707 Bloco E, Asa Norte, Brasília - DF",
              website="https://docemanha.example", phone="(61) 3340-0108", review_count="22", review_rating="3.9"),
        linha(9, title="Padaria Central do Plano", category="Padaria", address="CLS 308 Bloco C, Asa Sul, Brasília - DF",
              website="https://centraldoplano.example", phone="(61) 98140-0109", review_count="18", review_rating="3.8"),
    ]


def perfil_de_exemplo():
    perfil = perfil_ficticio()
    perfil["negocio"].update({"nome": "Ana", "empresa": "Estúdio Exemplo",
                              "oferta": "Sites e automações para negócios locais"})
    perfil["cliente"].update({"tipos": ["padaria"], "regioes": ["Brasília-DF"]})
    perfil["mensagens"] = {"whatsapp": (
        "Oi, tudo bem? Aqui é {meu_nome}, da {minha_empresa}. Vi {nome}, em {cidade}, e notei que {motivo}. "
        "Posso te mandar uma ideia rápida? Se não fizer sentido, é só avisar que não escrevo mais.")}
    return perfil


def avaliar_exemplo():
    conn = banco.abrir()
    try:
        bid = banco.criar_busca(conn, "padaria", "Brasília", "DF", "rapida", {}, False)
        banco.salvar_leads(conn, bid, limpeza.ler_csv(csv_texto(leads_de_exemplo()))[0], "Brasília", "DF", False)
        perfil = perfil_de_exemplo()
        return consulta.avaliar(conn, perfil), perfil
    finally:
        conn.close()


def main():
    avaliados, perfil = avaliar_exemplo()
    destino = RAIZ / "dados" / "exemplo-relatorio.xlsx"
    destino.parent.mkdir(exist_ok=True)
    destino.write_bytes(consulta.exportar_xlsx(avaliados, perfil))
    print(f"Gerado: {destino}")
    print(f"Codigo usado: {Path(consulta.__file__).resolve()} (folga do filtro: {xlsx.FOLGA_DO_FILTRO})")


if __name__ == "__main__":
    main()
