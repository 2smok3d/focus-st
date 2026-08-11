from pathlib import Path

from garage_v2.diagnostics_v2 import p04db_seed_case
from garage_v2.ingest import normalize_file
from garage_v2.parts import shopping_links, slot_by_id
from garage_v2.vehicle_state import ComponentState, current_seed_snapshot


def test_canonical_transmission_not_mt82():
    text = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    assert "MMT6" in text
    assert "MT82" in text  # preserved only as a documented legacy conflict


def test_current_mod_state():
    state = current_seed_snapshot(["intake_airbox", "rear_motor_mount", "active_grille_shutters"])
    assert state["intake_airbox"].state == ComponentState.UPGRADED
    assert state["rear_motor_mount"].state == ComponentState.UPGRADED
    assert state["active_grille_shutters"].state == ComponentState.REMOVED


def test_part_links_are_search_links():
    links = shopping_links("Motorcraft FL-910-S")
    assert "amazon.com/s?k=" in links["amazon"]
    assert "ebay.com/sch/i.html?_nkw=" in links["ebay"]


def test_oem_air_filter_corrected():
    slot = slot_by_id("engine_air_filter")
    assert slot is not None
    assert slot["oem"]["part"] == "FA-1908"


def test_p04db_case_is_least_invasive_first():
    case = p04db_seed_case()
    assert "P04DB" in case.dtcs
    tests = case.next_tests()
    assert tests[0]["invasiveness"] == 0
    assert all(t["result"] is None for t in tests)


def test_candump_and_dtc_normalization(tmp_path):
    sample = tmp_path / "sample.log"
    sample.write_text("(1723000000.125) can0 123#11223344\nPCM P04DB permanent\n", encoding="utf-8")
    out = normalize_file(sample, tmp_path / "vault")
    assert out.sha256
    assert out.can_frames[0]["arbitration_id"] == 0x123
    assert out.can_frames[0]["data_hex"] == "11223344"
    assert any(d["code"] == "P04DB" for d in out.dtcs)
    assert Path(out.raw_path).exists()
    assert Path(out.normalized_path).exists()
