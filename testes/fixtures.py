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


# ---------- dubles de motor e de geocodificacao (nenhuma rede de verdade) ----------

class MotorDeMentira:
    """Motor falso. `montar_pedido` e do motor de verdade; o resto nao abre rede."""

    def __init__(self, csv=None, ligado=True, falha=None, segurar=None, falha_a_partir_do_job=None):
        """`csv` pode ser um texto (todo job devolve ele) ou uma lista (job N devolve o N-esimo)."""
        from kit import motor as motor_mod
        self._real = motor_mod.Motor("http://127.0.0.1:8080", dormir=lambda s: None)
        self.csv = csv if csv is not None else csv_texto()
        self.falha_a_partir_do_job = falha_a_partir_do_job
        self.ligado, self.falha, self.segurar = ligado, falha, segurar
        self.pedidos = []

    def montar_pedido(self, *args, **kwargs):
        return self._real.montar_pedido(*args, **kwargs)

    def no_ar(self):
        return self.ligado

    def criar_job(self, pedido):
        self.pedidos.append(pedido)
        return f"job{len(self.pedidos)}"

    def esperar(self, job_id, intervalo=5, limite=None, ao_esperar=None):
        if ao_esperar:
            ao_esperar(5)
        if self.segurar is not None:  # deixa o teste olhar a busca "no meio"
            self.segurar.wait(10)
        numero = int(job_id.removeprefix("job"))
        if self.falha_a_partir_do_job and numero >= self.falha_a_partir_do_job[0]:
            raise self.falha_a_partir_do_job[1]
        if self.falha:
            raise self.falha
        return "ok"

    def baixar_csv(self, job_id):
        if isinstance(self.csv, list):
            return self.csv[min(int(job_id.removeprefix("job")), len(self.csv)) - 1]
        return self.csv


class GeoDeMentira:
    def __init__(self, erro=None):
        self.erro, self.chamadas = erro, []

    def buscar(self, cidade, uf):
        self.chamadas.append((cidade, uf))
        if self.erro:
            raise self.erro
        return (-15.65, -47.79)


def leads_em_massa(quantidade, semente=7):
    """Leads FICTICIOS e reproduziveis, com sites, telefones, notas e categorias variados.

    A cada 97 leads entram 3 unidades de uma mesma rede ficticia (para a marca de "possivel rede")
    e a cada 41 um lead sem telefone (excluido).
    """
    import random
    sorteio = random.Random(semente)
    categorias = ["Padaria", "Restaurante", "Cafeteria", "Academia", "Clínica de estética", "Salão de beleza",
                  "Mercearia", "Pizzaria", "Oficina mecânica", "Pet shop"]
    linhas = []
    n = 0
    while len(linhas) < quantidade:
        n += 1
        if n % 97 == 0:
            for unidade in ("Centro", "Norte", "Sul"):
                if len(linhas) < quantidade:
                    linhas.append(linha(10_000 + len(linhas), title=f"Rede Fictícia - {unidade}",
                                        category="Padaria", address=f"Rua {unidade} {n}, Cidade Teste",
                                        phone=f"(61) 3300-{n % 10000:04d}"))
            continue
        sorteado = sorteio.random()
        site = "" if sorteado < 0.35 else ("https://www.instagram.com/exemplo%d" % n if sorteado < 0.55
                                           else "https://site%d.exemplo.invalid" % n)
        if n % 41 == 0:
            telefone = ""
        elif sorteio.random() < 0.6:
            telefone = "(61) 9%04d-%04d" % (sorteio.randrange(10000), sorteio.randrange(10000))
        else:
            telefone = "(61) 3%03d-%04d" % (sorteio.randrange(1000), sorteio.randrange(10000))
        linhas.append(linha(
            10_000 + len(linhas), title=f"Negócio Fictício {n:04d}", category=sorteio.choice(categorias),
            address=f"Rua Exemplo {n}, Bairro {n % 17}, Cidade Teste - DF", website=site, phone=telefone,
            review_count=str(sorteio.randrange(0, 900)), review_rating=f"{sorteio.uniform(3.0, 5.0):.1f}"))
    return linhas
