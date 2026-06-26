"""Validate weekend rotation against exemplifying blocks (Mar–Apr, Mag–Giu, Lug–Ago 2026)."""
from datetime import date, timedelta

ROLES = ["VN", "SN", "SG", "MN", "MG"]
ORDER = [
    "CAMPAGNOL", "PICCOLI", "VERARDO", "DELLA LIBERA", "LOVERO",
    "MAROTTA", "VIRDIS", "BRONDOLIN", "TESO",
]


def role(i, w, n):
    k = ((i - w) % n + n) % n
    return ROLES[k] if k < 5 else "/"


def saturdays(start, count):
    d = start
    out = []
    while len(out) < count:
        if d.weekday() == 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def weeks_from_anchor(anchor, target):
    n = 0
    d = anchor
    while d < target:
        n += 1
        d += timedelta(days=7)
    return n


def check_block(label, start, n_docs, n_we, w0):
    docs = [d for d in ORDER if d != "TESO"][:n_docs] if n_docs <= 8 else ORDER[:n_docs]
    sats = saturdays(start, n_we)
    print(f"\n=== {label}  N={n_docs}  w0={w0} ===")
    for wi, sat in enumerate(sats):
        row = [role(i, w0 + wi, n_docs) for i in range(n_docs)]
        roles = [c for c in row if c in ROLES]
        ok = len(roles) == 5 and len(set(roles)) == 5
        print(
            f"  {sat.strftime('%d/%m')}  {' '.join(f'{c:2}' for c in row)}"
            + ("  OK" if ok else "  ERR")
        )


def main():
    anchor = date(2026, 3, 14)
    check_block("Mar–Apr esempio", anchor, 7, 7, 0)
    may = date(2026, 5, 2)
    check_block("Mag–Giu esempio", may, 8, 8, weeks_from_anchor(anchor, may))
    jul = date(2026, 6, 27)
    check_block("Lug–Ago esempio", jul, 8, 8, weeks_from_anchor(anchor, jul))
    # Con Teso rientrata: 9 medici, 9 weekend
    check_block("Blocco futuro 9 medici", date(2026, 9, 5), 9, 9, weeks_from_anchor(anchor, date(2026, 9, 5)))


if __name__ == "__main__":
    main()
