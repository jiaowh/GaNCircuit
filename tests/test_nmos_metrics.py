import unittest

from circuit_tools.nmos_data import NMOSDataError, NMOSDataset
from circuit_tools.nmos_metrics import dc_secants


def dataset(gates=(.45, .5, .55), drains=(.45, .5, .55), current=None):
    current = current or (lambda g, d: 2 * g * g + 3 * d * d + g * d)
    records = []
    for gi, g in enumerate(gates):
        for di, d in enumerate(drains):
            value = current(g, d)
            records.append({"id": f"g{gi}_d{di}", "vgs_v": g, "vds_v": d,
                "currents_a_per_cm": {"gate": 0., "drain": value, "source": -value, "body": 0.},
                "solver_converged": True})
    return NMOSDataset.from_records(records,
        {"device_revision": "device", "mesh_sha256": "mesh", "physics_sha256": "physics"},
        [r["id"] for r in records if r["vgs_v"] != gates[1]],
        [r["id"] for r in records if r["vgs_v"] == gates[1]])


class NMOSMetricsTests(unittest.TestCase):
    def test_quadratic_secants_match_analytic_central_derivatives(self):
        metrics = dc_secants(dataset())
        self.assertEqual(len(metrics), 6)
        for bias in (.45, .5, .55):
            self.assertAlmostEqual(metrics[f"gm_vds_{bias:g}"]["value"], 2 + bias)
            self.assertAlmostEqual(metrics[f"gds_vgs_{bias:g}"]["value"], 3 + bias)
        self.assertAlmostEqual(metrics["gm_vds_0.5"]["span_v"], .1)
        self.assertEqual(metrics["gm_vds_0.5"]["low_id"], "g0_d1")

    def test_smaller_steps_expose_cubic_secant_error(self):
        broad = dc_secants(dataset(current=lambda g, d: g ** 3 + d ** 3))
        narrow = dc_secants(dataset((.475, .5, .525), (.475, .5, .525), lambda g, d: g ** 3 + d ** 3))
        for name in ("gm_vds_0.5", "gds_vgs_0.5"):
            self.assertAlmostEqual(broad[name]["value"] - .75, .05 ** 2)
            self.assertAlmostEqual(narrow[name]["value"] - .75, .025 ** 2)

    def test_reject_incomplete_asymmetric_and_overflow_grids(self):
        for data in (dataset(drains=(.45, .5)), dataset(gates=(.45, .5, .6)),
                     dataset(current=lambda g, d: -1e308 if g < .5 else 1e308)):
            with self.subTest(points=len(data.records)), self.assertRaises(NMOSDataError):
                dc_secants(data)
