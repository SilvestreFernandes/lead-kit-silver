"""SQLite dos leads e das buscas (dados/leads.db). So biblioteca padrao.

O mesmo negocio achado em buscas diferentes vira um lead so (chave = place_id, cid ou nome+endereco).
Status, anotacao e mensagem editada sobrevivem a novas buscas. A marcacao de "possivel rede" nao
fica aqui: e recalculada na hora pelo modulo pontuacao.

Uma conexao por thread: cada requisicao do servidor e a thread da busca chamam abrir() e fecham a
sua. Nunca compartilhe uma conexao entre threads.
"""
import json
import sqlite3
from datetime import datetime

ESQUEMA = """
CREATE TABLE IF NOT EXISTS buscas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    criada_em TEXT NOT NULL,
    categoria TEXT NOT NULL,
    cidade TEXT NOT NULL,
    uf TEXT NOT NULL,
    tamanho TEXT NOT NULL,
    parametros TEXT NOT NULL,
    email_ligado INTEGER NOT NULL DEFAULT 0,
    job_id TEXT,
    status TEXT NOT NULL DEFAULT 'criada',
    erro TEXT,
    total_leads INTEGER
);
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL UNIQUE,
    place_id TEXT, cid TEXT,
    nome TEXT NOT NULL, nome_norm TEXT NOT NULL,
    categoria TEXT, endereco TEXT, cidade TEXT, uf TEXT,
    site TEXT, telefone TEXT, telefone_digitos TEXT, celular INTEGER,
    avaliacoes INTEGER, nota_maps REAL,
    delivery INTEGER, reserva INTEGER, emails TEXT,
    latitude REAL, longitude REAL, link TEXT,
    email_ligado INTEGER NOT NULL DEFAULT 0,
    nota INTEGER, letra TEXT, motivos TEXT,
    status TEXT NOT NULL DEFAULT 'novo',
    anotacao TEXT NOT NULL DEFAULT '',
    mensagem_editada TEXT NOT NULL DEFAULT '',
    criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS leads_busca (
    busca_id INTEGER NOT NULL REFERENCES buscas(id),
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    PRIMARY KEY (busca_id, lead_id)
);
"""

STATUS_LEAD = ("novo", "contatado", "respondeu", "fechado", "descartado")
STATUS_BUSCA_ABERTOS = ("criada", "working")


def agora():
    return datetime.now().isoformat(timespec="seconds")


def abrir(caminho=":memory:"):
    conn = sqlite3.connect(caminho, timeout=10)
    conn.row_factory = sqlite3.Row
    if str(caminho) != ":memory:":
        conn.execute("PRAGMA journal_mode=WAL")  # leitura nao trava enquanto a busca grava
    conn.execute("PRAGMA busy_timeout=10000")
    conn.executescript(ESQUEMA)
    return conn


def criar_busca(conn, categoria, cidade, uf, tamanho, parametros, email_ligado):
    cur = conn.execute(
        "INSERT INTO buscas (criada_em, categoria, cidade, uf, tamanho, parametros, email_ligado)"
        " VALUES (?,?,?,?,?,?,?)",
        (agora(), categoria, cidade, uf, tamanho, json.dumps(parametros), int(email_ligado)))
    conn.commit()
    return cur.lastrowid


def atualizar_busca(conn, busca_id, **campos):
    permitidos = {"job_id", "status", "erro", "total_leads", "parametros"}
    if not campos or set(campos) - permitidos:
        raise ValueError("campo de busca invalido")
    if "parametros" in campos:
        campos["parametros"] = json.dumps(campos["parametros"])
    sql = ", ".join(f"{c} = ?" for c in campos)
    conn.execute(f"UPDATE buscas SET {sql} WHERE id = ?", (*campos.values(), busca_id))
    conn.commit()


def _busca(linha):
    d = dict(linha)
    d["email_ligado"] = bool(d["email_ligado"])
    d["parametros"] = json.loads(d["parametros"])
    return d


def obter_busca(conn, busca_id):
    linha = conn.execute("SELECT * FROM buscas WHERE id = ?", (busca_id,)).fetchone()
    return _busca(linha) if linha else None


def listar_buscas(conn):
    return [_busca(r) for r in conn.execute("SELECT * FROM buscas ORDER BY id DESC")]


def interromper_buscas_abertas(conn):
    """No inicio do servidor: busca que ficou 'rodando' de uma execucao anterior nao esta rodando."""
    cur = conn.execute(
        "UPDATE buscas SET status='erro', erro=? WHERE status IN ('criada','working')",
        ("Interrompida: o kit foi fechado durante a busca. Faça a busca de novo.",))
    conn.commit()
    return cur.rowcount


def salvar_leads(conn, busca_id, leads, cidade, uf, email_ligado):
    """Grava (ou atualiza) os leads limpos e liga todos a esta busca. Nao mexe em status nem anotacao."""
    for l in leads:
        conn.execute(
            """INSERT INTO leads (chave, place_id, cid, nome, nome_norm, categoria, endereco, cidade, uf,
                   site, telefone, telefone_digitos, celular, avaliacoes, nota_maps, delivery, reserva,
                   emails, latitude, longitude, link, email_ligado, criado_em, atualizado_em)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(chave) DO UPDATE SET
                   nome=excluded.nome, nome_norm=excluded.nome_norm, categoria=excluded.categoria,
                   endereco=excluded.endereco, site=excluded.site, telefone=excluded.telefone,
                   telefone_digitos=excluded.telefone_digitos, celular=excluded.celular,
                   avaliacoes=excluded.avaliacoes, nota_maps=excluded.nota_maps,
                   delivery=excluded.delivery, reserva=excluded.reserva, emails=excluded.emails,
                   latitude=excluded.latitude, longitude=excluded.longitude, link=excluded.link,
                   email_ligado=excluded.email_ligado, atualizado_em=excluded.atualizado_em""",
            (l["chave"], l["place_id"], l["cid"], l["nome"], l["nome_norm"], l["categoria"],
             l["endereco"], cidade, uf, l["site"], l["telefone"], l["telefone_digitos"],
             int(l["celular"]), l["avaliacoes"], l["nota_maps"], int(l["delivery"]), int(l["reserva"]),
             json.dumps(l["emails"]), l["latitude"], l["longitude"], l["link"], int(email_ligado),
             agora(), agora()))
        conn.execute(
            "INSERT OR IGNORE INTO leads_busca (busca_id, lead_id)"
            " SELECT ?, id FROM leads WHERE chave = ?", (busca_id, l["chave"]))
    conn.commit()


def _para_lead(linha):
    """Linha do banco -> o mesmo formato de lead limpo que o modulo limpeza produz."""
    d = dict(linha)
    for campo in ("celular", "delivery", "reserva", "email_ligado"):
        d[campo] = bool(d[campo])
    d["emails"] = json.loads(d["emails"] or "[]")
    d["motivos"] = json.loads(d["motivos"]) if d["motivos"] else []
    return d


def todos_os_leads(conn):
    return [_para_lead(r) for r in conn.execute("SELECT * FROM leads ORDER BY id")]


def obter_lead(conn, lead_id):
    linha = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    return _para_lead(linha) if linha else None


def ids_da_busca(conn, busca_id):
    return {r[0] for r in conn.execute("SELECT lead_id FROM leads_busca WHERE busca_id = ?", (busca_id,))}


def leads_da_busca(conn, busca_id):
    linhas = conn.execute(
        "SELECT l.* FROM leads l JOIN leads_busca b ON b.lead_id = l.id WHERE b.busca_id = ?"
        " ORDER BY l.id", (busca_id,))
    return [_para_lead(r) for r in linhas]


def gravar_notas(conn, notas):
    """notas: {chave: {'nota':..., 'letra':..., 'motivos': [...]}}. A exclusao nunca e gravada."""
    for chave, r in notas.items():
        conn.execute("UPDATE leads SET nota=?, letra=?, motivos=?, atualizado_em=? WHERE chave=?",
                     (r["nota"], r["letra"], json.dumps(r["motivos"], ensure_ascii=False), agora(), chave))
    conn.commit()


def atualizar_lead(conn, lead_id, status=None, anotacao=None, mensagem_editada=None):
    """Muda so os campos dados. Devolve False se o lead nao existe."""
    if status is not None and status not in STATUS_LEAD:
        raise ValueError("status invalido: " + str(status))
    campos = {k: v for k, v in (("status", status), ("anotacao", anotacao),
                                ("mensagem_editada", mensagem_editada)) if v is not None}
    if not campos:
        return obter_lead(conn, lead_id) is not None
    sql = ", ".join(f"{c} = ?" for c in campos)
    cur = conn.execute(f"UPDATE leads SET {sql}, atualizado_em = ? WHERE id = ?",
                       (*campos.values(), agora(), lead_id))
    conn.commit()
    return cur.rowcount == 1
