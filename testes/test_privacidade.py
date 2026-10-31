"""O que a tela Buscar diz que sai do computador tem que bater com o que o código faz."""
import re
import unittest
import urllib.parse
from pathlib import Path

from kit import geocodificar

RAIZ = Path(geocodificar.__file__).resolve().parent.parent
KIT = RAIZ / "kit"
PAINEL = KIT / "painel"


def ler(p):
    return p.read_text(encoding="utf-8")


class TestOQueSaiDoComputador(unittest.TestCase):
    def test_so_tres_arquivos_do_kit_fazem_pedidos_de_rede(self):
        com_rede = {p.name for p in KIT.glob("*.py")
                    if re.search(r"urlopen|socket\.|http\.client|\brequests\b|ftplib|smtplib", ler(p))}
        self.assertEqual(com_rede, {"geocodificar.py", "motor.py", "testar_api.py"})

    def test_motor_e_testar_api_so_falam_com_a_propria_maquina(self):
        self.assertIn("_conferir_endereco", ler(KIT / "motor.py"))
        self.assertRegex(ler(KIT / "motor.py"), r'URL_PADRAO = "http://127\.0\.0\.1:8080"')
        self.assertIn('f"http://127.0.0.1:{porta}"', ler(KIT / "testar_api.py"))
        for nome in ("motor.py", "testar_api.py"):
            externos = re.findall(r"https?://(?!127\.0\.0\.1|localhost)[\w.-]+", ler(KIT / nome))
            self.assertEqual(externos, [], nome)

    def test_hosts_externos_citados_no_codigo(self):
        achados = set()
        for p in KIT.glob("*.py"):
            if p.name == "xlsx.py":  # so identificadores de formato (namespaces), nao enderecos acessados
                continue
            achados.update(re.findall(r"https?://([\w.-]+)", ler(p)))
        achados -= {"127.0.0.1", "localhost"}
        # nominatim: usado pelo geocodificador. osmfoundation: so a politica citada num comentario.
        # wa.me: so o link que a pessoa clica no painel, o kit nunca chama.
        self.assertEqual(achados, {"nominatim.openstreetmap.org", "operations.osmfoundation.org", "wa.me"})

    def test_o_geocodificador_envia_so_cidade_estado_e_pais(self):
        pedidos = []

        def falso(url, cabecalhos):
            pedidos.append((url, cabecalhos))
            return '[{"lat": "-15.6", "lon": "-47.7"}]'

        geocodificar.Geocodificador(abrir_url=falso, dormir=lambda s: None).buscar("Sobradinho", "DF")
        url, cabecalhos = pedidos[0]
        partes = urllib.parse.urlsplit(url)
        self.assertEqual(partes.hostname, "nominatim.openstreetmap.org")
        self.assertEqual(partes.scheme, "https")
        consulta = dict(urllib.parse.parse_qsl(partes.query))
        self.assertEqual(set(consulta), {"city", "state", "country", "format", "limit"})
        self.assertEqual((consulta["city"], consulta["state"], consulta["country"]), ("Sobradinho", "DF", "Brazil"))
        self.assertEqual(set(cabecalhos), {"User-Agent", "Accept-Language"})

    def test_o_tipo_de_negocio_nunca_vai_para_o_servico_de_localizacao(self):
        pedidos = []
        geocodificar.Geocodificador(abrir_url=lambda u, c: (pedidos.append(u), '[{"lat":"1","lon":"2"}]')[1],
                                    dormir=lambda s: None).buscar("Brasília", "DF")
        self.assertNotIn("padaria", pedidos[0].lower())
        # e o codigo do geocodificador nem recebe a categoria
        import inspect
        self.assertEqual(list(inspect.signature(geocodificar.Geocodificador.buscar).parameters), ["self", "cidade", "uf"])

    def test_o_texto_da_tela_cita_o_que_o_codigo_realmente_chama(self):
        tela = ler(PAINEL / "tela-buscar.js")
        self.assertIn("OpenStreetMap (Nominatim)", tela)
        self.assertIn("nominatim.openstreetmap", geocodificar.URL)
        self.assertIn("nome da cidade e o estado", tela)
        self.assertIn("ficam só no seu computador", tela)
        self.assertIn("Google Maps pela sua conexão", tela)


class TestRegrasDeTextoDaTelaBuscar(unittest.TestCase):
    def setUp(self):
        self.tela = ler(PAINEL / "tela-buscar.js")
        self.util = ler(PAINEL / "util.js")

    def test_nao_existe_botao_nem_rotulo_de_cancelar(self):
        for nome in ("tela-buscar.js", "app.js", "tela-leads.js", "util.js", "dom.js"):
            texto = ler(PAINEL / nome)
            self.assertIsNone(re.search(r"""['"`]Cancelar['"`]""", texto), nome)
            self.assertIsNone(re.search(r"rotulo:\s*['\"]\s*Cancelar", texto), nome)
        self.assertIsNone(re.search(r"escrever\(\s*['\"]DELETE['\"]", self.tela))
        self.assertIn("não tem como cancelar uma busca", self.tela)

    def test_texto_nao_promete_quantidade_nem_cita_os_numeros_medidos(self):
        for texto in (self.tela, self.util):
            sem_codigo_de_cor = re.sub(r"#[0-9a-fA-F]{3,8}", "", texto)
            self.assertIsNone(re.search(r"\b(65|88)\b", sem_codigo_de_cor))
            self.assertIsNone(re.search(r"garant", sem_codigo_de_cor, re.I))
        self.assertIn("O kit não promete uma quantidade", self.tela)

    def test_tempo_estimado_e_estimativa_nunca_garantia(self):
        from kit import motor
        for t in motor.TAMANHOS.values():
            self.assertTrue(t["tempo_estimado"].startswith("cerca de"))
        self.assertIn("pode variar", self.tela.lower())
        self.assertIn("Os tempos são estimativas e podem variar", self.tela)

    def test_ampla_so_aparece_como_em_breve_e_desativada(self):
        self.assertIn("tamanhos_em_breve", self.tela)
        self.assertIn("disabled: true", self.tela)
        self.assertIn("'em breve'", self.tela)

    def test_a_tela_usa_o_estado_do_servidor_e_nao_a_memoria_da_pagina(self):
        self.assertIn("busca_em_andamento", self.tela)
        self.assertIn("/api/buscas/${id}", self.tela)
        self.assertNotIn("localStorage.setItem('lks-busca", self.tela)  # a busca ativa nunca fica guardada no navegador


if __name__ == "__main__":
    unittest.main()
