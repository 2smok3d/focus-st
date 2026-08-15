"""Unit tests for the datalog parser + summarizer — pure, no database."""
from app import analysis
from app.parsers import parse_datalog


DATALOG = (
    "Time,RPM,Boost (psi),Knock (deg),Misfire,STFT (%),Coolant (C),IAT (C)\n"
    "0.00,850,-8.0,0,0,1.0,88,40\n"
    "0.50,3200,12.5,0,0,2.5,92,48\n"
    "1.00,5200,20.5,-3.0,1,-4.0,101,58\n"
    "1.50,6200,19.8,0,0,3.0,104,61\n"
)


def test_parse_datalog_populates_measurements():
    res = parse_datalog(DATALOG)
    assert res.measurements
    pids = {m["pid"] for m in res.measurements}
    assert "RPM" in pids and "Boost" in pids and "Knock" in pids
    # unit parsed out of the header
    boost = next(m for m in res.measurements if m["pid"] == "Boost")
    assert boost["unit"] == "psi"
    # time offsets relative to first row
    assert min(m["t_offset_s"] for m in res.measurements) == 0.0
    assert max(m["t_offset_s"] for m in res.measurements) == 1.5


def _rows():
    return [{"pid": m["pid"], "value": m["value"], "unit": m["unit"], "t_offset_s": m["t_offset_s"]}
            for m in parse_datalog(DATALOG).measurements]


def test_summary_recognizes_channels():
    summ = analysis.summarize_measurements(_rows())
    rec = summ["recognized"]
    assert rec.get("boost_actual") == "Boost"
    assert rec.get("knock") == "Knock"
    assert summ["duration_s"] == 1.5
    assert summ["samples"] == len(_rows())


def test_summary_flags_knock_and_misfire():
    summ = analysis.summarize_measurements(_rows())
    texts = " ".join(f["text"].lower() for f in summ["findings"])
    assert "knock" in texts
    assert "misfire" in texts
    assert any(f["level"] == "warn" for f in summ["findings"])


def test_summary_peak_boost_reported():
    summ = analysis.summarize_measurements(_rows())
    boost = summ["channels"]["Boost"]
    assert boost["max"] == 20.5
    assert boost["unit"] == "psi"


def test_summary_dtc_count_surfaces():
    summ = analysis.summarize_measurements(_rows(), dtc_count=2)
    assert summ["dtc_count"] == 2
    assert any("dtc" in f["text"].lower() for f in summ["findings"])


def test_summary_empty_is_safe():
    summ = analysis.summarize_measurements([])
    assert summ["samples"] == 0
    assert summ["findings"] == [] and summ["channels"] == {}
