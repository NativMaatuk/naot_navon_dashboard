def format_price(val) -> str:
    if val is None or (isinstance(val, float) and val != val):
        return "—"
    return f"{int(val):,} ₪"


def format_number(val, decimals=0) -> str:
    if val is None or (isinstance(val, float) and val != val):
        return "—"
    if decimals == 0:
        return f"{int(val):,}"
    return f"{val:,.{decimals}f}"
