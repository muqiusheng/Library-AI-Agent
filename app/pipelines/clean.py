import re
import unicodedata
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Any

NULL_VALUES = {"", "null", "none", "nan", "无", "-", "--"}
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
WHITESPACE = re.compile(r"\s+")


def repair_mojibake(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return value
    return _repair_text(value)


@lru_cache(maxsize=250_000)
def _repair_text(value: str) -> str:
    try:
        repaired = value.encode("latin1").decode("gbk")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    chinese_before = sum("\u4e00" <= char <= "\u9fff" for char in value)
    chinese_after = sum("\u4e00" <= char <= "\u9fff" for char in repaired)
    return repaired if chinese_after > chinese_before else value


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    return _clean_text_value(str(value))


@lru_cache(maxsize=300_000)
def _clean_text_value(value: str) -> str | None:
    text = _repair_text(value)
    text = unicodedata.normalize("NFKC", text).replace("\u3000", " ")
    text = WHITESPACE.sub(" ", CONTROL_CHARACTERS.sub("", text)).strip()
    return None if text.lower() in NULL_VALUES else text


def normalize_for_match(value: Any) -> str:
    text = clean_text(value) or ""
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text.casefold())


def normalize_isbn(value: Any) -> tuple[str | None, str | None, str | None]:
    raw = clean_text(value)
    if not raw:
        return None, None, None
    candidate = re.sub(r"[^0-9Xx]", "", raw).upper()
    if len(candidate) == 10 and _valid_isbn10(candidate):
        return candidate, None, None
    if len(candidate) == 13 and _valid_isbn13(candidate):
        return None, candidate, None
    return None, None, raw


def _valid_isbn10(value: str) -> bool:
    if not re.fullmatch(r"\d{9}[\dX]", value):
        return False
    total = sum(
        (10 - index) * (10 if char == "X" else int(char)) for index, char in enumerate(value)
    )
    return total % 11 == 0


def _valid_isbn13(value: str) -> bool:
    if not value.isdigit():
        return False
    total = sum(int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(value[:12]))
    return (10 - total % 10) % 10 == int(value[-1])


def parse_year(value: Any) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"(?:18|19|20|21)\d{2}", text)
    if not match:
        return None
    year = int(match.group())
    return year if 1800 <= year <= datetime.now(UTC).year + 1 else None


def parse_decimal(value: Any) -> Decimal | None:
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if not match:
        return None
    try:
        return Decimal(match.group()).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def parse_pages(value: Any) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    numbers = [int(item) for item in re.findall(r"\d+", text)]
    plausible = [number for number in numbers if 1 <= number <= 100_000]
    return max(plausible, default=None)


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = clean_text(value)
    if not text:
        return None
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def map_book_status(*values: Any) -> str:
    text = " ".join(clean_text(value) or "" for value in values)
    if any(word in text for word in ("遗失", "丢失")):
        return "lost"
    if any(word in text for word in ("加工", "编目", "处理中")):
        return "processing"
    if any(word in text for word in ("预约", "保留")):
        return "reserved"
    if any(word in text for word in ("借出", "外借中")):
        return "borrowed"
    if any(word in text for word in ("在架", "可借", "在馆")):
        return "available"
    return "unknown"


def map_circulation_status(*values: Any) -> str:
    text = " ".join(clean_text(value) or "" for value in values)
    if any(word in text for word in ("可借", "外借")):
        return "lendable"
    if any(word in text for word in ("阅览", "仅供阅读", "不外借")):
        return "reading_only"
    if any(word in text for word in ("限制", "特藏", "保存本")):
        return "restricted"
    return "unknown"
