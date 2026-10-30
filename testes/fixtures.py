"""Dados FICTICIOS para os testes. Nenhum lead real entra aqui."""
import csv
import io
import json

COLUNAS = [
    "input_id", "link", "title", "category", "address", "open_hours", "popular_times",
    "website", "phone", "plus_code", "review_count", "review_rating", "reviews_per_rating",
    "latitude", "longitude", "cid", "status", "descriptions", "reviews_link", "thumbnail",
    "timezone", "price_range", "data_id", "street_view_url", "place_id", "images",
    "reservations", "order_online", "menu", "owner", "complete_address",
    "credit_cards_accepted", "about", "user_reviews", "user_reviews_extended", "emails",
]


def linha(n, **campos):
    """Uma linha ficticia com as 36 colunas. Os campos dados sobrescrevem o padrao."""
    base = {c: "" for c in COLUNAS}
    base.update({
        "input_id": "fake", "title": f"Negócio Fictício {n}", "category": "Padaria",
        "address": f"Rua Falsa {n}, Cidade Teste", "website": "https://exemplo.invalid/",
        "phone": "(61) 3333-0000", "review_count": "30", "review_rating": "3.8",
        "latitude": "-15.0", "longitude": "-47.0", "cid": f"cid{n}", "place_id": f"pid{n}",
        "status": "", "order_online": "[]", "reservations": "[]", "emails": "",
    })
    base.update(campos)
    return base


def leads_ficticios():
    return [
        linha(1, title="Pão Sem Site", website="", phone="(61) 99999-0001",
              review_count="80", review_rating="4.7"),
        linha(2, title="Só Rede Social", website="https://www.instagram.com/falso",
              phone="(61) 3333-0002", review_count="10", review_rating="3.5"),
        linha(3, title="Padaria Completa", website="https://completa.invalid",
              phone="+55 61 98888-0003", review_count="200", review_rating="4.5",
              order_online='[{"link":"https://x.invalid"}]'),
        linha(4, title="Sem Telefone", phone="", website=""),
        linha(5, title="Nota Péssima", review_rating="2.5", review_count="5"),
        linha(6, title="Café Rede", place_id="pid6a", cid="cid6a", address="Rua A"),
        linha(7, title="Café Rede - Filial Norte", place_id="pid6b", cid="cid6b", address="Rua B"),
        linha(8, title="CAFÉ REDE", place_id="pid6c", cid="cid6c", address="Rua C"),
        linha(9, title="Concorrente Fictício", website="https://www.concorrente.invalid/loja"),
        linha(10, title="Duplicado", place_id="pid_dup", cid="cid_dup"),
        linha(10, title="Duplicado", place_id="pid_dup", cid="cid_dup"),
        linha(11, title="Reserva", reservations='[{"x":1}]', category="Restaurante"),
    ]


def csv_texto(linhas=None, colunas=None):
    colunas = colunas or COLUNAS
    saida = io.StringIO()
    escritor = csv.DictWriter(saida, fieldnames=colunas, extrasaction="ignore")
    escritor.writeheader()
    for l in (linhas if linhas is not None else leads_ficticios()):
        escritor.writerow(l)
    return saida.getvalue()


def perfil_ficticio():
    return json.loads(json.dumps({
        "versao": 1,
        "negocio": {"nome": "Teste", "empresa": "Empresa Teste",
                    "oferta": "Sites para negócios locais", "atendimento": "remoto"},
        "cliente": {"tipos": ["padaria"], "porte": "pequeno", "regioes": ["Cidade Teste-DF"], "exemplo": ""},
        "pontuacao": {"regras": [
            {"id": "sem_site", "peso": 3}, {"id": "so_instagram", "peso": 2},
            {"id": "nota_alta", "peso": 2}, {"id": "muitas_avaliacoes", "peso": 1},
            {"id": "celular", "peso": 2}]},
        "exclusoes": ["franquia", "sem_telefone"],
        "exclusoes_concorrentes": [],
        "abordagem": {"canais": ["whatsapp"], "tom": "amigavel",
                      "oferta_entrada": "diagnóstico grátis", "volume_semana": "10-30"},
        "conformidade": {"restricoes": "nao"},
        "mensagens": {"whatsapp": "Oi, {nome}! Notei que {motivo}. Se não fizer sentido, é só avisar que não escrevo mais."},
    }))
