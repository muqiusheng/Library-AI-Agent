from app.pipelines.clean import (
    clean_text,
    map_book_status,
    map_circulation_status,
    normalize_isbn,
    parse_pages,
    parse_year,
    repair_mojibake,
)


def test_repairs_gbk_text_decoded_as_latin1() -> None:
    assert repair_mojibake("ÐòºÅ") == "序号"
    assert clean_text("  ÈË¹¤ÖÇÄÜ  ") == "人工智能"


def test_isbn10_and_isbn13_validation() -> None:
    assert normalize_isbn("978-7-5641-3446-4") == (None, "9787564134464", None)
    assert normalize_isbn("7-302-12345-X") == (None, None, "7-302-12345-X")
    assert normalize_isbn(None) == (None, None, None)


def test_year_pages_and_status_mapping() -> None:
    assert parse_year("2012年") == 2012
    assert parse_pages("xv, 336 p.") == 336
    assert map_book_status("可借", "在架") == "available"
    assert map_circulation_status("可借", "在架") == "lendable"
