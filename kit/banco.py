"""SQLite dos leads e das buscas (dados/leads.db). So biblioteca padrao.

O mesmo negocio achado em buscas diferentes vira um lead so (chave = place_id, cid ou nome+endereco).
Status, anotacao e mensagem editada sobrevivem a novas buscas. A marcacao de "possivel rede" nao
fica aqui: e recalculada na hora pelo modulo pontuacao.
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
    chave TEXT PRIMARY KEY,
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
    chave TEXT NOT NULL REFERENCES leads(chave),
    PRIMARY KEY (busca_id, chave)
);
"""

STATUS_LEAD = ("novo", "contatado", "respondeu", "fechado", "descartado")


def agora():
    return datetime.now().isoformat(timespec="seconds")


def abrir(caminho=":memory:"):
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
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
    permitidos = {"job_id", "status", "erro", "total_leads"}
    if not campos or set(campos) - permitidos:
        raise ValueError("campo de busca invalido")
    sql = ", ".join(f"{c} = ?" for c in campos)
    conn.execute(f"UPDATE buscas SET {sql} WHERE id = ?", (*campos.values(), busca_id))
    conn.commit()


def obter_busca(conn, busca_id):
    linha = conn.execute("SELECT * FROM buscas WHERE id = ?", (busca_id,)).fetchone()
    return dict(linha) if linha else None


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
        conn.execute("INSERT OR IGNORE INTO leads_busca (busca_id, chave) VALUES (?,?)",
                     (busca_id, l["chave"]))
    conn.commit()


def _para_lead(linha):
    """Linha do banco -> o mesmo formato de lead limpo que o modulo limpeza produz."""
    d = dict(linha)
    for campo in ("celular", "delivery", "reserva"):
        d[campo] = bool(d[campo])
    d["emails"] = json.loads(d["emails"] or "[]")
    d["motivos"] = json.loads(d["motivos"]) if d["motivos"] else []
    return d


def todos_os_leads(conn):
    return [_para_lead(r) for r in conn.execute("SELECT * FROM leads ORDER BY chave")]


def leads_da_busca(conn, busca_id):
    linhas = conn.execute(
        "SELECT l.* FROM leads l JOIN leads_busca b ON b.chave = l.chave WHERE b.busca_id = ?"
        " ORDER BY l.chave", (busca_id,))
    return [_para_lead(r) for r in linhas]


def gravar_notas(conn, notas):
    """notas: {chave: {'nota':..., 'letra':..., 'motivos': [...]}}. A exclusao nunca e gravada."""
    for chave, r in notas.items():
        conn.execute("UPDATE leads SET nota=?, letra=?, motivos=?, atualizado_em=? WHERE chave=?",
                     (r["nota"], r["letra"], json.dumps(r["motivos"], ensure_ascii=False), agora(), chave))
    conn.commit()


def mudar_status(conn, chave, status):
    if status not in STATUS_LEAD:
        raise ValueError("status invalido: " + status)
    conn.execute("UPDATE leads SET status=?, atualizado_em=? WHERE chave=?", (status, agora(), chave))
    conn.commit()
