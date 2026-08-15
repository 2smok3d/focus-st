"""Unit tests for the NHTSA recall parser + known baseline — pure, no network."""
import datetime as dt

from app import recalls


# A trimmed but realistic NHTSA recallsByVehicle payload.
SAMPLE = {
    "results": [
        {
            "Manufacturer": "Ford Motor Company",
            "NHTSACampaignNumber": "18V684000",
            "ReportReceivedDate": "20/09/2018",
            "Component": "FUEL SYSTEM, GASOLINE",
            "Summary": "Purge valve may stick open.",
            "Consequence": "An engine stall increases the risk of a crash.",
            "Remedy": "Dealers will replace the canister purge valve, free of charge.",
            "ModelYear": "2017", "Make": "FORD", "Model": "FOCUS",
        },
        {  # missing campaign number → skipped
            "Component": "UNKNOWN", "Summary": "no campaign id",
        },
    ]
}


def test_parse_nhtsa_maps_fields():
    rows = recalls.parse_nhtsa(SAMPLE["results"])
    assert len(rows) == 1  # the entry without a campaign number is dropped
    r = rows[0]
    assert r["campaign_number"] == "18V684000"
    assert r["origin"] == "nhtsa"
    assert r["component"] == "FUEL SYSTEM, GASOLINE"
    assert r["verification"] == "OEM_VERIFIED"
    assert r["report_date"] == dt.date(2018, 9, 20)


def test_parse_nhtsa_empty():
    assert recalls.parse_nhtsa([]) == []
    assert recalls.parse_nhtsa(None) == []


def test_date_parsing_variants():
    assert recalls._to_date("09/20/2018") == dt.date(2018, 9, 20)
    assert recalls._to_date("2018-09-20") == dt.date(2018, 9, 20)
    assert recalls._to_date("") is None
    assert recalls._to_date(None) is None


def test_known_baseline_has_purge_campaign():
    camps = {k["campaign_number"] for k in recalls.KNOWN}
    assert "18S32" in camps and "26S40" in camps
    for k in recalls.KNOWN:
        assert k["origin"] == "ford-known"
        assert k["component"] and k["summary"]
