"""Unit tests for receipt parsing + classification — pure, no database."""
import datetime as dt

from app import receipts


def test_parse_structured_receipt():
    r = receipts.parse_receipt({
        "vendor": "Mishimoto", "date": "2026-08-01", "total": 549.95,
        "items": ["Performance Intercooler Kit"], "order_id": "MI-12345",
        "url": "https://mishimoto.com/x",
    })
    assert r.vendor == "Mishimoto"
    assert r.date == dt.date(2026, 8, 1)
    assert r.total == 549.95
    assert r.order_id == "MI-12345"


def test_parse_raw_email_extracts_total_and_vendor():
    text = (
        "From: orders@rockauto.com\n"
        "Order # ABC1234\n"
        "Motorcraft Oil Filter FL910S  $12.49\n"
        "Order Total: $34.97\n"
        "Aug 1, 2026\n"
    )
    r = receipts.parse_receipt(text)
    assert r.vendor == "rockauto"
    assert r.total == 34.97
    assert r.order_id == "ABC1234"
    assert r.date == dt.date(2026, 8, 1)


def test_classify_parts_vendor_is_parts():
    r = receipts.parse_receipt({"vendor": "Mishimoto", "total": 549.95,
                                "items": ["Intercooler Kit"]})
    c = receipts.classify(r)
    assert c.entity == "parts"
    assert c.patch["category"] == "Cooling"
    assert c.patch["approx_price"] == 549.95


def test_classify_service_vendor_is_service_event():
    r = receipts.parse_receipt({"vendor": "Ford Service", "total": 89.99,
                                "items": ["Synthetic oil change and filter"]})
    c = receipts.classify(r)
    assert c.entity == "service_event"
    assert c.patch["item"] == "Engine oil & filter"
    assert c.patch["cost"] == 89.99


def test_classify_service_by_item_even_unknown_vendor():
    r = receipts.parse_receipt({"vendor": "Some Local Shop", "total": 40.0,
                                "items": ["Tire rotation"]})
    c = receipts.classify(r)
    assert c.entity == "service_event"
    assert c.patch["item"] == "Tire rotation"


def test_classify_unknown_vendor_defaults_to_parts():
    r = receipts.parse_receipt({"vendor": "Mystery Store", "total": 25.0,
                                "items": ["Blue LED strip"]})
    c = receipts.classify(r)
    assert c.entity == "parts"


def test_classify_patch_only_allowed_fields():
    from app import domain
    for vendor in ("Mishimoto", "Ford Service"):
        r = receipts.parse_receipt({"vendor": vendor, "total": 10.0, "items": ["oil filter"]})
        c = receipts.classify(r)
        ok, msg = domain.validate_patch(c.entity, c.patch)
        assert ok, msg
