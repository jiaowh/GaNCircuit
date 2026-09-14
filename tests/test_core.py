import math
import unittest

from src.circuit_tools.core import ArtifactStore, Circuit, CircuitPatch, RevisionConflict, ValidationError


class CoreTests(unittest.TestCase):
  def test_artifacts_are_content_addressed_and_require_parents(self):
    import tempfile
    store = ArtifactStore(__import__('pathlib').Path(tempfile.mkdtemp()) / "store")
    root = store.put("design", {"x": 1})
    assert store.put("design", {"x": 1}) == root
    child = store.put("result", {"ok": True}, [root])
    assert store.parents(child) == (root,)
    assert store.get(child)["payload"] == {"ok": True}
    with self.assertRaises(ValidationError):
        store.put("result", {}, ["0" * 64])
    path = store.objects / f"{root}.json"
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with self.assertRaises(ValidationError):
        store.get(root)


  def test_circuit_validation_patch_and_spice_export(self):
    c = Circuit((
        {"name": "Rload", "kind": "R", "terminals": {"p": "vdd", "n": "out"}, "value": 1000.0},
        {"name": "M1", "kind": "M", "terminals": {"d": "out", "g": "in", "s": "0", "b": "0"}, "model": "nmos"},
    ))
    p = CircuitPatch(c.revision, connect={"M1": {"g": "vin"}}, upsert=(
        {"name": "V1", "kind": "V", "terminals": {"p": "vin", "n": "0"}, "value": 1.2},
    ))
    updated = c.patch(p)
    assert "V1 vin 0 1.2" in updated.export_spice()
    assert "M1 out vin 0 0 nmos" in updated.export_spice()
    with self.assertRaises(RevisionConflict):
        c.patch(CircuitPatch("stale", remove=("Rload",)))


  def test_rejects_nonfinite_or_non_numeric_values(self):
    for bad in [math.inf, math.nan, "1k"]:
      with self.assertRaises(ValidationError):
        Circuit(({"name": "R1", "kind": "R", "terminals": {"p": "a", "n": "b"}, "value": bad},))


  def test_rejects_unsafe_spice_names(self):
    with self.assertRaises(ValidationError):
        Circuit(({"name": "R 1", "kind": "R", "terminals": {"p": "a", "n": "b"}, "value": 1},))

  def test_invariants_and_nested_immutability(self):
    with self.assertRaises(ValidationError):
      Circuit(({"name": "X1", "kind": "R", "terminals": {"p": "0", "n": "b"}, "value": 1},))
    with self.assertRaises(ValidationError):
      Circuit(({"name": "R1", "kind": "R", "terminals": {"p": "0", "n": "b"}, "value": -1},))
    with self.assertRaises(ValidationError):
      Circuit(({"name": "D1", "kind": "D", "terminals": {"a": "0", "k": "b"}, "model": "d", "params": {"x": "bad"}},))
    c = Circuit(({"name": "R1", "kind": "R", "terminals": {"p": "0", "n": "b"}, "value": 1},))
    with self.assertRaises(TypeError):
      c.elements[0]["terminals"]["p"] = "c"


if __name__ == "__main__":
    unittest.main()
