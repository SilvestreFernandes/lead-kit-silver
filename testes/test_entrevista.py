"""O roteiro entrevista/perguntas.md: as 12 perguntas não mudam sem querer e as opções batem com o esquema e com as regras."""
import re
import unittest
from pathlib import Path

from kit import validar_perfil

RAIZ = Path(__file__).resolve().parent.parent
ROTEIRO = (RAIZ / "entrevista" / "perguntas.md").read_text(encoding="utf-8")
ESPECIFICACAO = (RAIZ / "docs" / "planejamento" / "entrevista-e-perfil.md").read_text(encoding="utf-8")
ESQUEMA = validar_perfil.ESQUEMA
REGRAS = validar_perfil.REGRAS


def blocos_do_roteiro():
    """{numero: texto do bloco}"""
    partes = re.split(r"^## Pergunta (\d+)\s*$", ROTEIRO, flags=re.M)
    return {int(partes[i]): partes[i + 1] for i in range(1, len(partes), 2)}


def campo(bloco, nome):
    achou = re.search(rf"^- \*\*{re.escape(nome)}:\*\*\s*(.+)$", bloco, flags=re.M)
    return achou.group(1).strip() if achou else None


def ids_das_opcoes(bloco):
    """Os ids entre crases das linhas numeradas de opção."""
    return re.findall(r"^\s*\d+\. .*?\(`([^`]+)`\)", bloco, flags=re.M)


def tabela_da_especificacao():
    """{numero: (texto da pergunta, campos do perfil)} lido da tabela de entrevista-e-perfil.md."""
    saida = {}
    for linha in ESPECIFICACAO.splitlines():
        achou = re.match(r"^\| (\d+) \| (.+?) \| (.+?) \| (.+?) \|$", linha)
        if achou and 1 <= int(achou.group(1)) <= 12:
            saida[int(achou.group(1))] = (achou.group(2).replace(" (opcional)", ""), achou.group(4))
    return saida


class TestRoteiro(unittest.TestCase):
    def setUp(self):
        self.blocos = blocos_do_roteiro()

    def test_sao_exatamente_12_perguntas_em_ordem(self):
        self.assertEqual(list(self.blocos), list(range(1, 13)))

    def test_o_texto_de_cada_pergunta_e_o_da_especificacao(self):
        especificacao = tabela_da_especificacao()
        self.assertEqual(sorted(especificacao), list(range(1, 13)))
        for numero, bloco in self.blocos.items():
            self.assertEqual(campo(bloco, "Texto"), especificacao[numero][0], f"pergunta {numero}")

    def test_os_campos_do_perfil_batem_com_a_especificacao(self):
        especificacao = tabela_da_especificacao()
        for numero, bloco in self.blocos.items():
            no_roteiro = set(re.findall(r"`([^`]+)`", campo(bloco, "Campo do perfil")))
            na_especificacao = set(re.findall(r"`([^`]+)`", especificacao[numero][1]))
            self.assertEqual(no_roteiro, na_especificacao, f"pergunta {numero}")

    def test_so_a_pergunta_7_e_opcional(self):
        for numero, bloco in self.blocos.items():
            self.assertEqual(campo(bloco, "Obrigatória").startswith("não"), numero == 7, f"pergunta {numero}")

    def test_toda_pergunta_diz_em_que_formato_gravar_a_resposta(self):
        for numero, bloco in self.blocos.items():
            self.assertIn(f'"{numero}":', campo(bloco, "Resposta no arquivo"), f"pergunta {numero}")

    def test_pergunta_com_opcoes_numeradas_termina_com_outra_resposta(self):
        for numero, bloco in self.blocos.items():
            opcoes = re.findall(r"^\s*(\d+)\. (.+)$", bloco, flags=re.M)
            if not opcoes:
                continue
            if numero in (12, 9 + 0) and False:
                continue
            ultimas = {}
            # cada lista numerada começa em 1; a última de cada lista precisa ser "Outra resposta" quando a pergunta
            # permite fugir das opções (a 12 só tem as três respostas da especificação)
            atual = []
            listas = []
            for n, texto in opcoes:
                if n == "1" and atual:
                    listas.append(atual)
                    atual = []
                atual.append(texto)
            listas.append(atual)
            if numero == 12:
                self.assertTrue(listas[-1][-1].startswith("Não sei"))
                continue
            for lista in listas:
                self.assertTrue(lista[-1].startswith("Outra resposta"), f"pergunta {numero}: {lista[-1]}")

    def test_o_desdobramento_da_pergunta_6_nao_cria_uma_13a_pergunta(self):
        self.assertNotIn(13, self.blocos)
        bloco = self.blocos[6]
        self.assertIn("Desdobramento", bloco)
        self.assertIn("concorrentes", bloco)
        self.assertIn("não é uma 13ª pergunta", bloco)

    def test_nenhum_texto_usa_travessao(self):
        self.assertNotIn("—", ROTEIRO)
        self.assertNotIn("–", ROTEIRO)


class TestOpcoesBatemComOEsquema(unittest.TestCase):
    def setUp(self):
        self.blocos = blocos_do_roteiro()

    def test_ids_da_pergunta_5_sao_regras_do_kit(self):
        ids = ids_das_opcoes(self.blocos[5])
        self.assertEqual(len(ids), 9)
        self.assertTrue(set(ids) <= set(REGRAS["regras"]))

    def test_lacuna_conhecida_a_regra_celular_nao_esta_na_pergunta_5(self):
        # A especificação lista 9 opções na pergunta 5, mas o kit tem 10 regras: falta "telefone parece celular".
        # Isso é decisão do Silvestre (mudar a pergunta 5). Enquanto não decidir, o roteiro segue a especificação.
        self.assertEqual(set(REGRAS["regras"]) - set(ids_das_opcoes(self.blocos[5])), {"celular"})

    def test_ids_da_pergunta_6_sao_exclusoes_do_kit(self):
        ids = ids_das_opcoes(self.blocos[6])
        self.assertEqual(set(ids), set(REGRAS["exclusoes"]))

    def test_demais_perguntas_usam_ids_do_esquema(self):
        self.assertEqual(ids_das_opcoes(self.blocos[3]), ESQUEMA["portes"])
        self.assertEqual(ids_das_opcoes(self.blocos[4]), ESQUEMA["atendimentos"])
        self.assertEqual(ids_das_opcoes(self.blocos[8]), ESQUEMA["canais"])
        self.assertEqual(ids_das_opcoes(self.blocos[9]), ESQUEMA["tons"])
        self.assertEqual(ids_das_opcoes(self.blocos[11]), [v["id"] for v in ESQUEMA["volumes_semana"]])
        self.assertEqual(ids_das_opcoes(self.blocos[12]), ["nao", "sim", "nao sei"])

    def test_a_pergunta_10_lista_as_ofertas_da_especificacao(self):
        for oferta in ("Diagnóstico grátis", "Orçamento", "Teste gratuito", "Reunião rápida", "Amostra"):
            self.assertIn(oferta, self.blocos[10])

    def test_o_exemplo_do_esquema_cobre_os_campos_que_o_roteiro_preenche(self):
        exemplo = (RAIZ / "entrevista" / "perfil.exemplo.json").read_text(encoding="utf-8")
        for numero, bloco in self.blocos.items():
            for caminho in re.findall(r"`([a-z_]+\.[a-z_]+|exclusoes[a-z_]*)`", campo(bloco, "Campo do perfil")):
                chave = caminho.split(".")[-1]
                self.assertIn(f'"{chave}"', exemplo, f"pergunta {numero}: {caminho}")


if __name__ == "__main__":
    unittest.main()
