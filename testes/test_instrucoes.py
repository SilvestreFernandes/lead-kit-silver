"""Toda tela que manda a pessoa executar algo diz ONDE e COMO, com as mesmas palavras em todo lugar."""
import re
import unittest
from pathlib import Path

from kit import diagnostico

PAINEL = Path(diagnostico.__file__).resolve().parent / "painel"


def ler(nome):
    return (PAINEL / nome).read_text(encoding="utf-8")


def lista_js(fonte, nome):
    corpo = re.search(rf"export const {nome} = \[(.*?)\n\];", fonte, re.S).group(1)
    return re.findall(r"^  '(.*)',$", corpo, re.M)


class TestInstrucoes(unittest.TestCase):
    def test_passos_do_terminal_sao_iguais_no_python_e_no_javascript(self):
        self.assertEqual(lista_js(ler("instrucoes.js"), "PASSOS_TERMINAL"), diagnostico.PASSOS_TERMINAL)

    def test_comandos_sao_iguais_no_python_e_no_javascript(self):
        js = ler("instrucoes.js")
        self.assertIn(f"COMANDO_LIGAR_MOTOR = '{diagnostico.COMANDO_LIGAR_MOTOR}'", js)

    def test_passos_do_painel_para_o_motor_batem_com_os_do_servidor(self):
        js = ler("instrucoes.js")
        self.assertIn("...PASSOS_TERMINAL,\n  'Espere uns 20 segundos e clique em Verificar de novo.',", js)
        for chave in ("docker_parado", "motor_parado"):
            self.assertEqual(diagnostico.DIAGNOSTICOS[chave]["passos"][-1], "Espere uns 20 segundos e clique em Verificar de novo.")

    def test_todo_diagnostico_tem_passos_e_so_cita_comando_com_onde_digitar(self):
        for chave, d in diagnostico.DIAGNOSTICOS.items():
            if d is None:
                continue
            self.assertTrue(d["passos"], chave)
            if d["comando"]:
                self.assertIn("digite powershell e aperte Enter", " ".join(d["passos"]), chave)

    def test_a_mensagem_do_servidor_traz_os_passos(self):
        msg = diagnostico.mensagem_completa(diagnostico.DIAGNOSTICOS["motor_parado"])
        self.assertIn("digite powershell e aperte Enter", msg)
        self.assertIn("docker compose up -d", msg)

    def test_comando_so_aparece_na_tela_pelo_componente_com_passos(self):
        for p in PAINEL.glob("*.js"):
            if p.name == "dom.js":
                continue
            self.assertIsNone(re.search(r"(?<![\w.])comando\(", p.read_text(encoding="utf-8")), p.name)

    def test_perfil_ausente_diz_onde_abrir_a_ia(self):
        js = ler("instrucoes.js")
        passos = " ".join(lista_js(js, "PASSOS_PERFIL_AUSENTE"))
        self.assertIn("Abra a sua IA", passos)
        self.assertIn("Faça a entrevista do meu perfil", passos)

    def test_nenhum_texto_usa_travessao(self):
        for texto in (ler("instrucoes.js"), Path(diagnostico.__file__).read_text(encoding="utf-8")):
            self.assertNotIn("—", texto)
            self.assertNotIn("–", texto)


if __name__ == "__main__":
    unittest.main()
