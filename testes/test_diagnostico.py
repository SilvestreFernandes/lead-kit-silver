import subprocess
import unittest

from kit import diagnostico


class MotorFalso:
    def __init__(self, no_ar):
        self.no_ar_valor, self.consultas = no_ar, 0

    def no_ar(self):
        self.consultas += 1
        return self.no_ar_valor


class Executor:
    """Substitui subprocess.run: guarda o que foi pedido e devolve o resultado combinado."""

    def __init__(self, retorno=0, erro=None):
        self.retorno, self.erro, self.chamadas = retorno, erro, []

    def __call__(self, comando, **kwargs):
        self.chamadas.append((comando, kwargs))
        if self.erro:
            raise self.erro
        return subprocess.CompletedProcess(comando, self.retorno, "", "")


class TestDiagnosticar(unittest.TestCase):
    def test_motor_no_ar_nao_roda_nada(self):
        executor = Executor()
        self.assertIsNone(diagnostico.diagnosticar(MotorFalso(True), executor))
        self.assertEqual(executor.chamadas, [])

    def test_docker_ligado_e_motor_parado(self):
        d = diagnostico.diagnosticar(MotorFalso(False), Executor(retorno=0))
        self.assertEqual(d["estado"], "motor_parado")
        self.assertEqual(d["comando"], "docker compose up -d")
        self.assertIn("O Docker está ligado, mas o motor de busca não", d["texto"])
        self.assertTrue(any("digite powershell e aperte Enter" in p for p in d["passos"]))

    def test_docker_desligado(self):
        d = diagnostico.diagnosticar(MotorFalso(False), Executor(retorno=1))
        self.assertEqual(d["estado"], "docker_parado")
        self.assertEqual(d["titulo"], "O Docker está desligado")
        self.assertIn("Docker Desktop está fechado", d["texto"])
        self.assertIn("Abra o Docker Desktop pelo menu Iniciar", d["passos"][0])
        self.assertIn("digite powershell e aperte Enter", " ".join(d["passos"]))
        self.assertEqual(d["comando"], "docker compose up -d")

    def test_docker_que_nao_responde_a_tempo_conta_como_desligado(self):
        d = diagnostico.diagnosticar(MotorFalso(False), Executor(erro=subprocess.TimeoutExpired("docker", 6)))
        self.assertEqual(d["estado"], "docker_parado")

    def test_docker_nao_instalado(self):
        d = diagnostico.diagnosticar(MotorFalso(False), Executor(erro=FileNotFoundError()))
        self.assertEqual(d["estado"], "docker_ausente")
        self.assertIsNone(d["comando"])
        self.assertIn("não foi encontrado", d["titulo"])

    def test_so_roda_um_comando_fixo_sem_texto_de_ninguem(self):
        executor = Executor()
        diagnostico.diagnosticar(MotorFalso(False), executor)
        comando, kwargs = executor.chamadas[0]
        self.assertEqual(comando, ["docker", "info"])
        self.assertNotIn("shell", kwargs)  # nunca por shell
        self.assertLessEqual(kwargs["timeout"], 10)

    def test_os_tres_motivos_sao_diferentes_e_sem_travessao(self):
        textos = set()
        for estado in ("docker_ausente", "docker_parado", "motor_parado"):
            d = diagnostico.DIAGNOSTICOS[estado]
            self.assertNotIn("—", d["titulo"] + d["texto"])
            textos.add(d["titulo"])
        self.assertEqual(len(textos), 3)


class TestDiagnosticoComCache(unittest.TestCase):
    def setUp(self):
        self.tempo = [0.0]
        self.executor = Executor(retorno=1)
        self.d = diagnostico.DiagnosticoComCache(
            funcao=lambda motor: diagnostico.diagnosticar(motor, self.executor),
            validade=15, relogio=lambda: self.tempo[0])

    def test_nao_roda_docker_info_a_cada_pergunta(self):
        motor = MotorFalso(False)
        for _ in range(5):
            self.d(motor)
        self.assertEqual(len(self.executor.chamadas), 1)

    def test_depois_da_validade_roda_de_novo(self):
        motor = MotorFalso(False)
        self.d(motor)
        self.tempo[0] = 16
        self.d(motor)
        self.assertEqual(len(self.executor.chamadas), 2)

    def test_motor_que_voltou_nao_usa_o_resultado_velho(self):
        motor = MotorFalso(False)
        self.assertEqual(self.d(motor)["estado"], "docker_parado")
        motor.no_ar_valor = True
        self.assertIsNone(self.d(motor))


if __name__ == "__main__":
    unittest.main()
