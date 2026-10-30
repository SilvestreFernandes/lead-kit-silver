"""Grade de pontos para buscas maiores. So matematica, sem rede.

O motor entrega cerca de 20 negocios por palavra-chave e por ponto, e a profundidade quase nao muda
isso (ver docs/planejamento/fase0-verificacao-motor.md). Para achar mais, a busca vira varios
pontos espalhados pela cobertura, um job por ponto, e os resultados sao juntados sem repetir.
"""
import math

METROS_POR_GRAU_LAT = 111_320.0
COBERTURA_PADRAO_M = 10_000

# Quantos pontos o kit sabe montar. Ampla (mais pontos) ainda nao foi definida nem medida.
PONTOS_SUPORTADOS = (1, 5)


def deslocar(lat, lon, norte_m, leste_m):
    """Anda norte_m para o norte e leste_m para o leste a partir de (lat, lon)."""
    nova_lat = lat + norte_m / METROS_POR_GRAU_LAT
    nova_lon = lon + leste_m / (METROS_POR_GRAU_LAT * math.cos(math.radians(lat)))
    return nova_lat, nova_lon


def pontos_da_grade(lat, lon, quantidade, cobertura_m=COBERTURA_PADRAO_M):
    """Lista de {'lat', 'lon', 'raio_m'} que cobre um circulo de raio cobertura_m.

    1 ponto: o centro, com raio = cobertura.
    5 pontos: o centro e quatro pontos (norte, sul, leste, oeste) a meia cobertura de distancia,
    cada um com meia cobertura de raio.
    """
    if quantidade not in PONTOS_SUPORTADOS:
        raise ValueError(f"Grade de {quantidade} pontos ainda não existe. Use: "
                         + ", ".join(map(str, PONTOS_SUPORTADOS)))
    if quantidade == 1:
        return [{"lat": lat, "lon": lon, "raio_m": cobertura_m}]
    meio = cobertura_m / 2
    pontos = [{"lat": lat, "lon": lon, "raio_m": int(meio)}]
    for norte, leste in ((meio, 0), (-meio, 0), (0, meio), (0, -meio)):
        la, lo = deslocar(lat, lon, norte, leste)
        pontos.append({"lat": round(la, 6), "lon": round(lo, 6), "raio_m": int(meio)})
    return pontos


def distancia_m(lat1, lon1, lat2, lon2):
    """Distancia aproximada entre dois pontos (haversine), em metros."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
