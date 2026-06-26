"""Infer VN/SN/SG/MN/MG from daily Excel grid (sat/sun/fri)."""
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "TURNI 2026.xlsx"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
WE_ROT = {"VN", "SN", "SG", "MN", "MG", "F", "/", "//"}


def col_num(c):
    n = 0
    for ch in c:
        n = n * 26 + (ord(ch) - 64)
    return n


def col_row(ref):
    m = re.match(r"([A-Z]+)(\d+)", ref)
    return m.group(1), int(m.group(2))


def excel_date(val):
    if val is None:
        return None
    s = str(val).strip()
    if re.match(r"^\d+(\.\d+)?$", s):
        n = float(s)
        if 40000 < n < 60000:
            return datetime(1899, 12, 30) + timedelta(days=int(n))
    months = {
        "gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
        "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12,
    }
    m = re.match(r"(\d+)-(\w+)", s.lower())
    if m:
        d, mon = int(m.group(1)), m.group(2)[:3]
        if mon in months:
            return datetime(2026, months[mon], d)
    return None


def norm(raw):
    if not raw:
        return ""
    s = str(raw).strip().upper()
    return s.split()[0] if s else ""


def base_code(c):
    c = norm(c)
    if c.startswith("M/"):
        return "M"
    if c in ("RN", "RF", "SN"):
        return c
    if c.startswith("AR") or c.startswith("GM"):
        return c[:2]
    return c.split("/")[0] if c else ""


def infer_we(fri, sat, sun):
    """Map fri/sat/sun daily codes -> weekend rotation code."""
    fri, sat, sun = base_code(fri), base_code(sat), base_code(sun)
    if sat == "F" or sun == "F" or fri == "F":
        return "F"
    if sat in ("MAL", "C") or sun in ("MAL", "C"):
        return "F"
    if fri == "N" and sat != "N":
        return "VN"
    if sat == "N":
        return "SN"
    if sat == "G":
        return "SG"
    if sat == "M" and sun == "N":
        return "MN"
    if sat == "M" and sun == "G":
        return "MG"
    if sat == "M" and sun in ("", "/"):
        return "MG"  # partial
    if sat in ("", "/") and sun in ("", "/"):
        return "/"
    if sat == "SN":
        return "SN"
    if sun == "G" and sat in ("", "/"):
        return "/"  # only dom guardia from other pattern
    if sun == "N" and sat in ("", "/"):
        return "/"
    return f"?{fri}|{sat}|{sun}"


def load_all():
    with zipfile.ZipFile(path) as z:
        shared = []
        ss = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in ss.findall(f".//{NS}si"):
            shared.append("".join(n.text or "" for n in si.iter(f"{NS}t")))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid_to = {
            r.get("Id"): r.get("Target")
            for r in rels.findall(
                "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
            )
        }
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        out = {}
        for s in wb.findall(f".//{NS}sheet"):
            name = s.get("name")
            rid = s.get(REL)
            target = rid_to[rid]
            if not target.startswith("xl/"):
                target = "xl/" + target.lstrip("/")
            sh = ET.fromstring(z.read(target))
            rows = defaultdict(dict)
            for c in sh.findall(f".//{NS}c"):
                ref = c.get("r")
                if not ref:
                    continue
                col, row = col_row(ref)
                v = c.find(f"{NS}v")
                if v is None:
                    continue
                val = v.text
                if c.get("t") == "s" and val and val.isdigit():
                    val = shared[int(val)]
                rows[row][col] = val
            out[name] = rows
    return out


def parse_days(rows):
    hdr = rows.get(1, {})
    doc_cols = sorted(
        [c for c in hdr if hdr[c] and hdr[c] not in ("Presenze", "Legenda", "Ore")],
        key=col_num,
    )
    docs = [hdr[c] for c in doc_cols]
    by_date = {}
    for r in sorted(rows):
        row = rows[r]
        dow = str(row.get("B", "")).lower()
        if not dow or dow in ("tot", "presenze") or "legenda" in dow or "totale" in dow:
            continue
        dt = excel_date(row.get("C"))
        if not dt:
            continue
        shifts = {doc: norm(row.get(c, "")) for c, doc in zip(doc_cols, docs)}
        by_date[dt.date()] = shifts
    return docs, by_date


def main():
    sheets = load_all()
    all_by_date = {}
    docs = None
    for name, rows in sheets.items():
        if "bis" in name.lower():
            continue
        d, by = parse_days(rows)
        if d:
            docs = d
        all_by_date.update(by)

    dates = sorted(all_by_date.keys())
    pairs = []
    for d in dates:
        if d.weekday() == 5:  # Saturday
            sun = d + timedelta(days=1)
            fri = d - timedelta(days=1)
            if sun not in all_by_date:
                continue
            label = d.strftime("%d/%m") + "-" + sun.strftime("%d/%m")
            rot = {}
            for doc in docs:
                rot[doc] = infer_we(
                    all_by_date.get(fri, {}).get(doc, ""),
                    all_by_date[d].get(doc, ""),
                    all_by_date[sun].get(doc, ""),
                )
            active = sum(1 for c in rot.values() if c in WE_ROT and c not in ("/", "//", "F"))
            pairs.append({"label": label, "sat": str(d), "n": active, "rotation": rot})

    print(f"Doctors: {docs}\n")
    print("=== INFERRED WEEKEND ROTATION ===")
    for p in pairs:
        codes = " ".join(
            f"{k.split()[0][:4]}:{v}"
            for k, v in sorted(p["rotation"].items())
            if v not in ("", "/")
        )
        unk = [f"{k}:{v}" for k, v in p["rotation"].items() if str(v).startswith("?")]
        print(f"{p['label']}  N~{p['n']}  {codes}")
        if unk:
            print("  ?", " ".join(unk))

    # Detect bimestre blocks (7 or 8 consecutive weekends with same doctor set)
    print("\n=== BLOCKS (7-8 consecutive WE) ===")
    i = 0
    while i < len(pairs):
        for block_len in (8, 7):
            if i + block_len > len(pairs):
                continue
            block = pairs[i : i + block_len]
            # check consecutive dates
            ok = True
            for j in range(1, block_len):
                prev = datetime.strptime(block[j - 1]["sat"], "%Y-%m-%d")
                curr = datetime.strptime(block[j]["sat"], "%Y-%m-%d")
                if (curr - prev).days != 7:
                    ok = False
                    break
            if not ok:
                continue
            # check each weekend has 5 guard roles
            valid = True
            for p in block:
                roles = [v for v in p["rotation"].values() if v in ("VN", "SN", "SG", "MN", "MG")]
                if len(roles) != 5:
                    valid = False
                    break
            if valid:
                print(
                    f"{block[0]['label']} -> {block[-1]['label']}  "
                    f"len={block_len}  N={block_len}"
                )
                # print matrix
                for doc in docs:
                    seq = [p["rotation"].get(doc, "/") for p in block]
                    if any(x not in ("/", "F", "//") for x in seq):
                        print(f"  {doc.split()[0][:8]:8}", " ".join(f"{x:2}" for x in seq))
                i += block_len
                break
        else:
            i += 1

    out_path = Path(__file__).resolve().parent / "excel_we_inferred.json"
    out_path.write_text(json.dumps(pairs, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved {out_path}")


if __name__ == "__main__":
    main()
