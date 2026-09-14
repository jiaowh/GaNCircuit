import math
import unittest

from src.circuit_tools.models import CharacterizationDataset, ModelValidationError, ShockleyDiodeModel


class ModelTests(unittest.TestCase):
    def dataset(self):
        isat, n, vt = 1e-12, 1.4, 0.025852
        records = []
        for i, voltage in enumerate((0.20, 0.30, 0.40, 0.50, 0.55, 0.60)):
            records.append({"id": f"r{i}", "voltage": voltage, "current": isat * math.expm1(voltage / (n * vt)), "temperature": 300.0})
        return CharacterizationDataset.from_records(records, {"source": "synthetic-fixture", "seed": 1, "device_revision": "device-1"}, ["r0", "r1", "r2", "r3"], ["r4", "r5"])

    def test_fit_validation_and_export(self):
        data = self.dataset()
        model = ShockleyDiodeModel.fit(data, device_revision="device-1", bias_bounds=(0.2, 0.6))
        self.assertFalse(model.validated)
        # The fit is the declared log(I)-versus-V approximation; expm1 gives
        # a small, expected low-bias deviation from that linearization.
        self.assertLess(model.heldout_error(data), 2e-3)
        with self.assertRaises(ModelValidationError):
            model.export_spice()
        checked = model.validate(data, max_relative_error=2e-3)
        self.assertTrue(checked.validated)
        self.assertIn(".model DIODE D(", checked.export_spice())
        self.assertIn("TNOM=26.85", checked.export_spice())

    def test_dataset_split_is_strict(self):
        with self.assertRaises(ModelValidationError):
            CharacterizationDataset.from_records([{"id": "x", "voltage": 0, "current": 1}], {"source": "x"}, ["x"], ["x"])
        with self.assertRaises(ModelValidationError):
            CharacterizationDataset.from_records([{"id": "x", "voltage": 0, "current": math.nan}], {"source": "x"}, ["x"], [])

    def test_domain_and_device_binding(self):
        model = ShockleyDiodeModel.fit(self.dataset(), device_revision="device-1", temperature_bounds=(300, 300), bias_bounds=(0.2, 0.6))
        with self.assertRaises(ModelValidationError):
            model.current(0.1)
        self.assertEqual(model.device_revision, "device-1")

    def test_provenance_and_validation_identity_are_bound(self):
        data = self.dataset()
        with self.assertRaises(ModelValidationError):
            ShockleyDiodeModel.fit(data, device_revision="other")
        model = ShockleyDiodeModel.fit(data, device_revision="device-1")
        altered = CharacterizationDataset.from_records(tuple(dict(r) for r in data.records[:-1]) + ({"id": "r5", "voltage": .6, "current": 1e-3, "temperature": 300.0},), data.provenance, data.train_ids, data.holdout_ids)
        with self.assertRaises(ModelValidationError):
            model.validate(altered, max_relative_error=1)
        with self.assertRaises(ModelValidationError):
            model.validate(data, max_relative_error=float("nan"))


if __name__ == "__main__":
    unittest.main()
