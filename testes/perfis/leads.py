"""Uma mesma busca, fictícia, usada para comparar como cada perfil de teste ordena os leads."""
from kit import banco, consulta, limpeza
from testes.fixtures import csv_texto, linha


def linhas_da_busca():
    """Dez negócios imaginários de Brasília. Cada um agrada mais a um perfil do que aos outros."""
    return [
        linha(1, title="Padaria Sem Site Movimentada", category="Padaria", website="", phone="(61) 98140-0201",
              review_rating="4.7", review_count="300"),
        linha(2, title="Restaurante Delivery Famoso", category="Restaurante", website="https://delivery.example",
              phone="(61) 3340-0202", review_rating="4.8", review_count="900", order_online='[{"link":"x"}]'),
        linha(3, title="Cafeteria Só Instagram", category="Cafeteria", website="https://www.instagram.com/cafe.exemplo",
              phone="(61) 98140-0203", review_rating="4.2", review_count="40"),
        linha(4, title="Barbearia Novinha", category="Barbearia", website="", phone="(61) 98140-0204",
              review_rating="4.9", review_count="8"),
        linha(5, title="Pizzaria Tradicional", category="Pizzaria", website="https://pizza.example", phone="(61) 3340-0205",
              review_rating="4.6", review_count="650", order_online='[{"link":"x"}]'),
        linha(6, title="Loja de Roupas Instagram", category="Loja de roupas", website="https://www.instagram.com/roupas.exemplo",
              phone="(61) 98140-0206", review_rating="3.8", review_count="12"),
        linha(7, title="Mercadinho do Bairro", category="Mercearia", website="https://mercadinho.example",
              phone="(61) 3340-0207", review_rating="4.0", review_count="20"),
        linha(8, title="Salão Sem Site e Pouca Gente", category="Salão de beleza", website="", phone="(61) 98140-0208",
              review_rating="4.4", review_count="14"),
        linha(9, title="Academia Grande", category="Academia", website="https://academia.example", phone="(61) 3340-0209",
              review_rating="4.5", review_count="120"),
        linha(10, title="Oficina Instagram Famosa", category="Oficina", website="https://www.instagram.com/oficina.exemplo",
                  phone="(61) 98140-0210", review_rating="4.7", review_count="200"),
    ]


def avaliar(perfil, extras=()):
    """Os leads da busca (mais os `extras`, se houver), avaliados por este perfil, na ordem em que o painel os mostra."""
    conn = banco.abrir()
    try:
        bid = banco.criar_busca(conn, "negocios", "Brasília", "DF", "rapida", {}, False)
        linhas = linhas_da_busca() + list(extras)
        banco.salvar_leads(conn, bid, limpeza.ler_csv(csv_texto(linhas))[0], "Brasília", "DF", False)
        return consulta.avaliar(conn, perfil)
    finally:
        conn.close()
