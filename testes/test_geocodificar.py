import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

from kit import geocodificar as g


class Falso:
    """Substitui a rede: guarda as chamadas e devolve respostas prontas."""

    def __init__(self, resposta):
        self.resposta, self.chamadas = resposta, []

    def __call__(self, url, cabecalhos):
        self.chamadas.append((url, cabecalhos))
        if isinstance(self.resposta, Exception):
            raise self.resposta
        return self.resposta


OK = json.dumps([{"lat": "-15.65", "lon": "-47.79", "display_name": "Cidade Teste"}])


def geo(resposta, **kw):
    falso = Falso(resposta)
    tempo = {"t": 0.0}
    dormidas = []
    kw.setdefault("relogio", lambda: tempo["t"])
    kw.setdefault("dormir", lambda s: (dormidas.append(s), tempo.__setitem__("t", tempo["t"] + s)))
    return g.Geocodificador(abrir_url=falso, **kw), falso, dormidas, tempo


class TestGeocodificar(unittest.TestCase):
    def test_devolve_numeros(self):
        gc, _, _, _ = geo(OK)
        self.assertEqual(gc.buscar("Cidade Teste", "DF"), (-15.65, -47.79))

    def test_identifica_o_app_e_limita_ao_brasil(self):
        gc, falso, _, _ = geo(OK)
        gc.buscar("Cidade Teste", "DF")
        url, cab = falso.chamadas[0]
        self.assertIn("LeadKitSilver", cab["User-Agent"])
        self.assertIn("country=Brazil", url)
        self.assertIn("limit=1", url)

    def test_cache_em_memoria_evita_segunda_chamada(self):
        gc, falso, _, _ = geo(OK)
        gc.buscar("Cidade Teste", "DF")
        gc.buscar("cidade  TESTE", "df")
        self.assertEqual(len(falso.chamadas), 1)

    def test_cache_em_disco_vale_entre_execucoes(self):
        with tempfile.TemporaryDirectory() as d:
            arq = Path(d) / "cache.json"
            gc, _, _, _ = geo(OK, arquivo_cache=arq)
            gc.buscar("Cidade Teste", "DF")
            gc2, falso2, _, _ = geo(OK, arquivo_cache=arq)
            self.assertEqual(gc2.buscar("Cidade Teste", "DF"), (-15.65, -47.79))
            self.assertEqual(falso2.chamadas, [])

    def test_no_maximo_uma_requisicao_por_segundo(self):
        gc, _, dormidas, tempo = geo(OK)
        gc.buscar("Cidade A", "DF")
        tempo["t"] += 0.3  # so passaram 0,3 s
        gc.buscar("Cidade B", "DF")
        self.assertEqual(len(dormidas), 1)
        self.assertAlmostEqual(dormidas[0], 0.7)

    def test_nao_espera_se_ja_passou_um_segundo(self):
        gc, _, dormidas, tempo = geo(OK)
        gc.buscar("Cidade A", "DF")
        tempo["t"] += 5
        gc.buscar("Cidade B", "DF")
        self.assertEqual(dormidas, [])

    def test_cidade_nao_encontrada(self):
        gc, _, _, _ = geo("[]")
        with self.assertRaises(g.ErroGeocodificacao) as e:
            gc.buscar("Lugar Nenhum", "DF")
        self.assertIn("Lugar Nenhum-DF", str(e.exception))

    def test_falha_nao_vai_para_o_cache(self):
        gc, falso, _, _ = geo("[]")
        for _ in range(2):
            with self.assertRaises(g.ErroGeocodificacao):
                gc.buscar("Lugar Nenhum", "DF")
        self.assertEqual(len(falso.chamadas), 2)

    def test_sem_internet(self):
        gc, _, _, _ = geo(urllib.error.URLError("sem rede"))
        with self.assertRaises(g.ErroGeocodificacao) as e:
            gc.buscar("Cidade Teste", "DF")
        self.assertIn("internet", str(e.exception))

    def test_resposta_estranha(self):
        gc, _, _, _ = geo("<html>erro</html>")
        with self.assertRaises(g.ErroGeocodificacao):
            gc.buscar("Cidade Teste", "DF")
        gc, _, _, _ = geo(json.dumps([{"nome": "sem coordenadas"}]))
        with self.assertRaises(g.ErroGeocodificacao):
            gc.buscar("Cidade Teste", "DF")


if __name__ == "__main__":
    unittest.main()
