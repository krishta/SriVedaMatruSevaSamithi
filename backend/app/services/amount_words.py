"""Indian-numbering (lakh/crore) amount-in-words converter. No heavyweight dependency."""

_ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
    "Seventeen", "Eighteen", "Nineteen",
]
_TENS = [
    "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety",
]


def _two_digits(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return f"{_TENS[tens]} {_ONES[ones]}".strip()


def _three_digits(n: int) -> str:
    hundred, rest = divmod(n, 100)
    parts = []
    if hundred:
        parts.append(f"{_ONES[hundred]} Hundred")
    if rest:
        parts.append(_two_digits(rest))
    return " ".join(parts)


def rupees_in_words(rupees: int) -> str:
    """e.g. 150000 -> 'One Lakh Fifty Thousand'. 0 -> 'Zero'."""
    if rupees == 0:
        return "Zero"
    if rupees < 0:
        return f"Minus {rupees_in_words(-rupees)}"

    crore, rem = divmod(rupees, 10_000_000)
    lakh, rem = divmod(rem, 100_000)
    thousand, rem = divmod(rem, 1000)
    hundred_rem = rem

    parts = []
    if crore:
        parts.append(f"{_three_digits(crore)} Crore")
    if lakh:
        parts.append(f"{_two_digits(lakh)} Lakh")
    if thousand:
        parts.append(f"{_two_digits(thousand)} Thousand")
    if hundred_rem:
        parts.append(_three_digits(hundred_rem))
    return " ".join(parts).strip()


def amount_paise_to_words(amount_paise: int) -> str:
    rupees = amount_paise // 100
    return f"Rupees {rupees_in_words(rupees)} Only"


def _group_indian(rupees: int) -> str:
    s = str(rupees)
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ",".join(parts) + "," + last3


def format_inr(amount_paise: int) -> str:
    """Indian digit grouping, e.g. 10000000 paise -> '₹1,00,000'. For web/JSON use — the ₹
    glyph isn't in reportlab's base14 fonts, so the PDF renderer uses format_inr_ascii instead."""
    return f"\u20b9{_group_indian(amount_paise // 100)}"


def format_inr_ascii(amount_paise: int) -> str:
    """Same Indian grouping without the ₹ glyph — safe for reportlab's built-in Helvetica,
    which renders U+20B9 as a missing-glyph box (module 05)."""
    return f"Rs. {_group_indian(amount_paise // 100)}"