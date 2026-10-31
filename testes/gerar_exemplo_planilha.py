"""Gera dados/exemplo-relatorio.xlsx com leads FICTICIOS, usando o codigo atual do kit.

    python testes/gerar_exemplo_planilha.py

Serve para ver como a planilha fica no Excel e no Google Planilhas depois de mudar o exportador.
Nao le o seu banco de leads: so usa os negocios de demonstracao.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from kit import xlsx  # noqa: E402
from testes import test_xlsx  # noqa: E402
from testes.demo_painel import leads_de_demonstracao  # noqa: E402
from kit import consulta  # noqa: E402


def main():
    avaliados, perfil = test_xlsx.montar(leads_de_demonstracao())
    destino = RAIZ / "dados" / "exemplo-relatorio.xlsx"
    destino.parent.mkdir(exist_ok=True)
    destino.write_bytes(consulta.exportar_xlsx(avaliados, perfil))
    print(f"Gerado: {destino}")
    print(f"Codigo usado: {Path(consulta.__file__).resolve()} (folga do filtro: {xlsx.FOLGA_DO_FILTRO})")


if __name__ == "__main__":
    main()
