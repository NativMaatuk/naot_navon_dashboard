def floor_numeric(floor) -> int:
    if floor is None or (isinstance(floor, float) and str(floor) == "nan"):
        return 0
    s = str(floor).strip()
    if s == "קרקע":
        return 0
    if "מרתף" in s:
        return -1
    try:
        return int(float(s))
    except ValueError:
        return 0


def floor_label_sort_key(floor) -> tuple:
    n = floor_numeric(floor)
    if n == -1:
        return (-2, str(floor))
    if n == 0:
        return (-1, str(floor))
    return (n, str(floor))
