import calendar
from datetime import date

ALLOWED_CODES = {
  "M","T","N","D","N12","F","FE","AT",
  "LN","LT","LE","LP","LM","LS","AF"
}

def days_in_month(year:int, month:int)->int:
    return calendar.monthrange(year, month)[1]

def weekday(year:int, month:int, day:int)->int:
    return date(year, month, day).weekday()  # 0 seg..6 dom

def pattern_fill(year:int, month:int, pattern:str):
    """
    Retorna dict: {day:int -> code:str}
    patterns:
      - 12x36_D_ODD / 12x36_D_EVEN
      - 12x36_N_ODD / 12x36_N_EVEN
      - MT_M / MT_T
    """
    last = days_in_month(year, month)
    out = {}

    if pattern.startswith("12x36_"):
        _, shift, parity = pattern.split("_")  # 12x36, D/N, ODD/EVEN
        code_on = "D" if shift == "D" else "N12"
        want_odd = (parity == "ODD")

        for d in range(1, last+1):
            is_odd = (d % 2 == 1)
            out[d] = code_on if (is_odd == want_odd) else "F"
        return out

    if pattern.startswith("MT_"):
        _, kind = pattern.split("_")  # M or T
        for d in range(1, last+1):
            wd = weekday(year, month, d)
            if wd <= 4:
                out[d] = "M" if kind == "M" else "T"
            else:
                out[d] = "F"
        return out

    return out
