import unittest

from kit import grade

BRASILIA = (-15.7939869, -47.8828)


class TestGrade(unittest.TestCase):
    def test_um_ponto_e_o_centro_com_a_cobertura_inteira(self):
        p = grade.pontos_da_grade(*BRASILIA, 1)
        self.assertEqual(p, [{"lat": BRASILIA[0], "lon": BRASILIA[1], "raio_m": 10000}])

    def test_cinco_pontos_centro_mais_quatro_a_meia_cobertura(self):
        p = grade.pontos_da_grade(*BRASILIA, 5)
        self.assertEqual(len(p), 5)
        self.assertEqual((p[0]["lat"], p[0]["lon"]), BRASILIA)
        for ponto in p[1:]:
            d = grade.distancia_m(*BRASILIA, ponto["lat"], ponto["lon"])
            self.assertAlmostEqual(d, 5000, delta=25)
        self.assertTrue(all(x["raio_m"] == 5000 for x in p))

    def test_pontos_ficam_em_norte_sul_leste_oeste(self):
        _, n, s, l, o = grade.pontos_da_grade(*BRASILIA, 5)
        self.assertGreater(n["lat"], BRASILIA[0])
        self.assertLess(s["lat"], BRASILIA[0])
        self.assertGreater(l["lon"], BRASILIA[1])
        self.assertLess(o["lon"], BRASILIA[1])
        self.assertAlmostEqual(n["lon"], BRASILIA[1], places=5)
        self.assertAlmostEqual(l["lat"], BRASILIA[0], places=5)

    def test_pontos_vizinhos_ficam_distantes_um_do_outro(self):
        p = grade.pontos_da_grade(*BRASILIA, 5)
        _, n, s, l, o = p
        self.assertAlmostEqual(grade.distancia_m(n["lat"], n["lon"], s["lat"], s["lon"]), 10000, delta=50)
        self.assertAlmostEqual(grade.distancia_m(l["lat"], l["lon"], o["lat"], o["lon"]), 10000, delta=50)

    def test_cobertura_diferente(self):
        p = grade.pontos_da_grade(*BRASILIA, 5, cobertura_m=4000)
        self.assertTrue(all(x["raio_m"] == 2000 for x in p))

    def test_quantidade_nao_suportada(self):
        for q in (0, 2, 9, -1):
            with self.assertRaises(ValueError):
                grade.pontos_da_grade(*BRASILIA, q)

    def test_funciona_longe_da_linha_do_equador(self):
        p = grade.pontos_da_grade(-30.03, -51.23, 5)  # perto de Porto Alegre
        d = grade.distancia_m(-30.03, -51.23, p[3]["lat"], p[3]["lon"])
        self.assertAlmostEqual(d, 5000, delta=25)


if __name__ == "__main__":
    unittest.main()
