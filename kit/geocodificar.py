"""Cidade e UF viram latitude e longitude pelo Nominatim (OpenStreetMap).

Segue a politica de uso do Nominatim: identifica o aplicativo no User-Agent, faz no maximo uma
requisicao por segundo e guarda o resultado em cache no disco, para nao perguntar duas vezes.
Politica: https://operations.osmfoundation.org/policies/nominatim/
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from kit.limpeza import normalizar_nome

URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "LeadKitSilver/1.0 (kit local de busca de leads; uso individual)"
INTERVALO_MINIMO = 1.0


class ErroGeocodificacao(Exception):
    """Nao deu pra achar a cidade."""


class CidadeNaoEncontrada(ErroGeocodificacao):
    """O servico respondeu, mas nao conhece essa cidade nesse estado."""


class Geocodificador:
    def __init__(self, arquivo_cache=None, abrir_url=None, relogio=time.monotonic, dormir=time.sleep):
        self.arquivo_cache = Path(arquivo_cache) if arquivo_cache else None
        self._abrir_url = abrir_url or self._abrir_de_verdade
        self._relogio, self._dormir = relogio, dormir
        self._ultima = None
        self._cache = self._ler_cache()

    def _ler_cache(self):
        if self.arquivo_cache and self.arquivo_cache.exists():
            try:
                return json.loads(self.arquivo_cache.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return {}
        return {}

    def _gravar_cache(self):
        if self.arquivo_cache:
            self.arquivo_cache.parent.mkdir(parents=True, exist_ok=True)
            self.arquivo_cache.write_text(json.dumps(self._cache, ensure_ascii=False, indent=1),
                                          encoding="utf-8")

    @staticmethod
    def _abrir_de_verdade(url, cabecalhos):
        req = urllib.request.Request(url, headers=cabecalhos)
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8")

    def _esperar_a_vez(self):
        agora = self._relogio()
        if self._ultima is not None:
            falta = INTERVALO_MINIMO - (agora - self._ultima)
            if falta > 0:
                self._dormir(falta)
        self._ultima = self._relogio()

    def buscar(self, cidade, uf):
        """Devolve (latitude, longitude) como numeros."""
        chave = f"{normalizar_nome(cidade)}|{uf.strip().casefold()}"
        if chave in self._cache:
            return tuple(self._cache[chave])
        params = urllib.parse.urlencode({
            "city": cidade, "state": uf, "country": "Brazil", "format": "jsonv2", "limit": 1})
        self._esperar_a_vez()
        try:
            corpo = self._abrir_url(f"{URL}?{params}", {"User-Agent": USER_AGENT, "Accept-Language": "pt-BR"})
            achados = json.loads(corpo)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                raise ErroGeocodificacao("O serviço de mapas que acha a cidade pediu para esperar um pouco. "
                                         "Tente de novo daqui a alguns minutos.")
            raise ErroGeocodificacao("O serviço de mapas que acha a cidade está com problema agora. "
                                     "Tente de novo daqui a pouco.")
        except (urllib.error.URLError, OSError):
            raise ErroGeocodificacao("Não consegui falar com o serviço de mapas para achar a cidade. "
                                     "Confira a internet e tente de novo.")
        except json.JSONDecodeError:
            raise ErroGeocodificacao("O serviço de mapas respondeu algo que não entendi. Tente de novo daqui a pouco.")
        if not achados:
            raise CidadeNaoEncontrada(f"Não achei a cidade {cidade}-{uf}. Confira o nome e a sigla do estado.")
        try:
            resultado = (float(achados[0]["lat"]), float(achados[0]["lon"]))
        except (KeyError, ValueError, TypeError):
            raise ErroGeocodificacao("O serviço de mapas devolveu um local sem coordenadas. Tente outro nome de cidade.")
        self._cache[chave] = list(resultado)
        self._gravar_cache()
        return resultado
