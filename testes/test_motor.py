import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from kit import motor as m
from testes.fixtures import csv_texto


class MotorFalso(BaseHTTPRequestHandler):
    """Imita o motor em 127.0.0.1, numa porta livre. Nenhuma rede de verdade."""
    estado = {}

    def log_message(self, *a):
        pass

    def _responder(self, codigo, corpo, tipo="application/json"):
        dados = corpo if isinstance(corpo, bytes) else json.dumps(corpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        e = MotorFalso.estado
        if self.path == "/api/v1/jobs":
            return self._responder(200, None)
        if self.path == "/api/v1/jobs/j1":
            e["consultas"] = e.get("consultas", 0) + 1
            return self._responder(200, {"ID": "j1", "Status": e["status"](e["consultas"])})
        if self.path == "/api/v1/jobs/j1/download":
            return self._responder(200, ("﻿" + csv_texto()).encode("utf-8"), "text/csv")
        self._responder(404, {"erro": "nao existe"})

    def do_POST(self):
        tamanho = int(self.headers["Content-Length"])
        MotorFalso.estado["recebido"] = json.loads(self.rfile.read(tamanho))
        MotorFalso.estado["tipo"] = self.headers["Content-Type"]
        if MotorFalso.estado.get("recusar"):
            return self._responder(422, {"message": "invalid lang"})
        self._responder(201, {"id": "j1"})


class TestMotor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servidor = HTTPServer(("127.0.0.1", 0), MotorFalso)
        cls.url = f"http://127.0.0.1:{cls.servidor.server_port}"
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()

    def setUp(self):
        MotorFalso.estado = {"status": lambda n: "ok"}
        self.tempo = {"t": 0.0}
        self.dormidas = []
        self.motor = m.Motor(self.url, dormir=self._dormir, relogio=lambda: self.tempo["t"])

    def _dormir(self, s):
        self.dormidas.append(s)
        self.tempo["t"] += s

    def test_so_aceita_motor_local(self):
        for base in ("http://192.168.0.5:8080", "http://exemplo.invalid", "http://0.0.0.0:8080"):
            with self.assertRaises(m.ErroMotor):
                m.Motor(base)
        m.Motor("http://localhost:8080")

    def test_pedido_tem_o_formato_confirmado_na_fase_0(self):
        p = self.motor.montar_pedido("padaria em Sobradinho DF", -15.65, -47.79, "rapida")
        self.assertEqual(p, {
            "name": "lead-kit", "keywords": ["padaria em Sobradinho DF"], "lang": "pt", "zoom": 15,
            "lat": "-15.65", "lon": "-47.79", "fast_mode": False, "radius": 10000, "depth": 1,
            "email": False, "max_time": 180})
        self.assertIsInstance(p["lat"], str)
        self.assertIsInstance(p["lon"], str)

    def test_tamanho_desconhecido(self):
        with self.assertRaises(m.ErroMotor):
            self.motor.montar_pedido("x", 0, 0, "gigante")

    def test_criar_job_envia_json_de_verdade(self):
        pedido = self.motor.montar_pedido('padaria "do zé"', -15.6, -47.7)
        self.assertEqual(self.motor.criar_job(pedido), "j1")
        self.assertEqual(MotorFalso.estado["recebido"], pedido)  # aspas sobreviveram
        self.assertEqual(MotorFalso.estado["tipo"], "application/json")

    def test_pedido_recusado_vira_mensagem(self):
        MotorFalso.estado["recusar"] = True
        with self.assertRaises(m.ErroMotor) as e:
            self.motor.criar_job({"lang": "pt-BR"})
        self.assertIn("422", str(e.exception))
        self.assertIn("invalid lang", str(e.exception))

    def test_espera_ate_ok(self):
        MotorFalso.estado["status"] = lambda n: "working" if n < 3 else "ok"
        self.assertEqual(self.motor.esperar("j1", intervalo=5), "ok")
        self.assertEqual(self.dormidas, [5, 5, 5])

    def test_status_inesperado_para_com_erro_claro(self):
        MotorFalso.estado["status"] = lambda n: "failed"
        with self.assertRaises(m.ErroMotor) as e:
            self.motor.esperar("j1")
        self.assertIn("failed", str(e.exception))

    def test_limite_de_tempo(self):
        MotorFalso.estado["status"] = lambda n: "working"
        with self.assertRaises(m.ErroMotor) as e:
            self.motor.esperar("j1", intervalo=10, limite=25)
        self.assertIn("25 segundos", str(e.exception))

    def test_baixa_csv_sem_bom(self):
        texto = self.motor.baixar_csv("j1")
        self.assertTrue(texto.startswith("input_id,"))

    def test_motor_desligado_da_mensagem_com_o_comando(self):
        desligado = m.Motor("http://127.0.0.1:9", dormir=self._dormir)
        self.assertFalse(desligado.no_ar())
        with self.assertRaises(m.ErroMotor) as e:
            desligado.status("j1")
        self.assertIn("docker compose up -d", str(e.exception))

    def test_no_ar(self):
        self.assertTrue(self.motor.no_ar())


if __name__ == "__main__":
    unittest.main()
