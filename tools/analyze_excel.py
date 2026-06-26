"""Analyze TURNI 2026.xlsx — weekend blocks, rotation, weekday patterns."""
import zipfile
import xml.etree.ElementTree as ET
import re
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "TURNI 2026.xlsx"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
WE_ROT = {"VN", "SN", "SG", "MN", "MG"}


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
            y = 2026
            return datetime(y, months[mon], d)
    return None


def norm_code(raw):
    if not raw:
        return ""
    s = str(raw).strip().upper()
    s = re.sub(r"\s+", " ", s)
    return s.split()[0] if s else ""


def load_sheets():
    with zipfile.ZipFile(path) as z:
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid_to = {
            r.get("Id"): r.get("Target")
            for r in rels.findall(
                "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
            )
        }
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        sheet_info = []
        for s in wb.findall(f".//{NS}sheet"):
            sheet_info.append(
                (
                    s.get("name"),
                    s.get(
                        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                    ),
                )
            )
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            ss = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in ss.findall(f".//{NS}si"):
                shared.append(
                    "".join(n.text or "" for n in si.iter(f"{NS}t"))
                )

        sheets = {}
        for name, rid in sheet_info:
            target = rid_to.get(rid, "").lstrip("/")
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
            sheets[name] = rows
    return sheets


def parse_sheet(rows):
    # Layout Excel: B=giorno, C=data, D=presenze, F..=medici (riga 1)
    hdr = rows.get(1, {})
    doc_cols = sorted(
        [c for c in hdr if hdr[c] and hdr[c] not in ("Presenze", "Legenda", "Ore")],
        key=col_num,
    )
    docs = [hdr[c] for c in doc_cols]
    days = []
    for r in sorted(rows):
        row = rows[r]
        dow = str(row.get("B", "")).lower()
        if not dow or dow in ("tot", "presenze") or "legenda" in dow:
            continue
        dt = excel_date(row.get("C"))
        if not dt:
            continue
        shifts = {}
        for c, doc in zip(doc_cols, docs):
            shifts[doc] = norm_code(row.get(c, ""))
        days.append(
            {
                "date": dt,
                "dow": dow,
                "presenze": row.get("D"),
                "shifts": shifts,
            }
        )
    return docs, days


def main():
    sheets = load_sheets()
    all_days = []
    doctor_names = None

    for name in sorted(sheets.keys()):
        docs, days = parse_sheet(sheets[name])
        if docs:
            doctor_names = docs
        for d in days:
            d["sheet"] = name
            all_days.append(d)

    all_days.sort(key=lambda x: x["date"])

    # Weekend pairs
    pairs = []
    i = 0
    while i < len(all_days):
        d = all_days[i]["date"]
        if d.weekday() == 5:
            sat = all_days[i]
            sun = all_days[i + 1] if i + 1 < len(all_days) else None
            if sun and sun["date"].weekday() == 6:
                pairs.append((sat, sun))
                i += 2
                continue
        i += 1

    print("DOCTORS:", doctor_names)
    print(f"Days parsed: {len(all_days)}  Weekend pairs: {len(pairs)}")
    print(f"Range: {all_days[0]['date'].date()} -> {all_days[-1]['date'].date()}\n")

    print("=== WEEKEND ROTATION (VN/SN/SG/MN/MG) ===")
    blocks = []
    cur_block = []
    for sat, sun in pairs:
        label = (
            sat["date"].strftime("%d/%m")
            + "-"
            + sun["date"].strftime("%d/%m")
        )
        rot = {}
        for doc in doctor_names:
            for code in (sat["shifts"].get(doc, ""), sun["shifts"].get(doc, "")):
                base = code.split("/")[0] if code else ""
                if base in WE_ROT:
                    rot[doc] = base
                    break
        active = len(rot)
        line = f"{label}  N={active}  " + " ".join(
            f"{d.split()[0][:4]}:{c}" for d, c in sorted(rot.items())
        )
        print(line)

        if cur_block and active != cur_block[-1][1]:
            blocks.append(cur_block)
            cur_block = []
        cur_block.append((label, active, rot))
    if cur_block:
        blocks.append(cur_block)

    print("\n=== BIMESTRE BLOCKS (consecutive same N) ===")
    for bi, block in enumerate(blocks):
        print(
            f"Block {bi+1}: {block[0][0]} -> {block[-1][0]}  "
            f"weekends={len(block)}  N={block[0][1]}"
        )

    # Per-doctor weekend rotation sequence
    print("\n=== PER-DOCTOR WE SEQUENCE ===")
    for doc in doctor_names:
        seq = []
        for sat, sun in pairs:
            for code in (sat["shifts"].get(doc, ""), sun["shifts"].get(doc, "")):
                base = code.split("/")[0] if code else ""
                if base in WE_ROT:
                    seq.append((sat["date"].strftime("%d/%m"), base))
                    break
                elif code in ("/", "G", "N", "SN", "F", "C", "MAL"):
                    seq.append((sat["date"].strftime("%d/%m"), code or "/"))
                    break
        if seq:
            short = doc.split()[0][:6]
            print(short, "->", " ".join(f"{d}:{c}" for d, c in seq))

    # Weekday rules sample: Monday R after Sunday G
    mon_r_after_sun_g = 0
    mon_r_total = 0
    tue_no_g_after_sun_g = 0
    fri_g_sat_n = 0
    for i, day in enumerate(all_days):
        if day["dow"].startswith("lun") and i > 0:
            prev = all_days[i - 1]
            if prev["dow"].startswith("dom"):
                for doc in doctor_names:
                    if prev["shifts"].get(doc) == "G":
                        mon_r_total += 1
                        if day["shifts"].get(doc) == "R":
                            mon_r_after_sun_g += 1
        if day["dow"].startswith("mar") and i > 1:
            sun = all_days[i - 2]
            mon = all_days[i - 1]
            for doc in doctor_names:
                if sun["shifts"].get(doc) == "G" and mon["shifts"].get(doc) in ("R", "/"):
                    if day["shifts"].get(doc) != "G":
                        tue_no_g_after_sun_g += 1
        if day["dow"].startswith("ven") and i + 1 < len(all_days):
            sat = all_days[i + 1]
            for doc in doctor_names:
                if sat["shifts"].get(doc) == "N" and day["shifts"].get(doc) == "G":
                    fri_g_sat_n += 1

    print("\n=== RULE VALIDATION (historical) ===")
    print(f"Monday R after Sunday G: {mon_r_after_sun_g}/{mon_r_total}")
    print(f"Tue no G after Sun G + Mon rest: {tue_no_g_after_sun_g} cases OK")
    print(f"Fri G when Sat N: {fri_g_sat_n}")

    # Ambulatori
    amb_counts = defaultdict(int)
    for day in all_days:
        dw = day["date"].weekday()
        if dw >= 5:
            continue
        for doc, code in day["shifts"].items():
            if code.startswith("M/"):
                amb_counts[(dw, code)] += 1
    print("\n=== AMBULATORI by weekday ===")
    names = ["lun", "mar", "mer", "gio", "ven"]
    for dw in range(5):
        codes = {c: n for (d, c), n in amb_counts.items() if d == dw}
        if codes:
            print(names[dw], codes)

    # Export JSON for app
    out = {
        "doctors": doctor_names,
        "weekend_pairs": [
            {
                "sat": sat["date"].strftime("%Y-%m-%d"),
                "sun": sun["date"].strftime("%Y-%m-%d"),
                "rotation": {
                    d: c
                    for d in doctor_names
                    for c in [
                        next(
                            (
                                x.split("/")[0]
                                for x in (
                                    sat["shifts"].get(d, ""),
                                    sun["shifts"].get(d, ""),
                                )
                                if x.split("/")[0] in WE_ROT
                            ),
                            None,
                        )
                    ]
                    if c
                },
            }
            for sat, sun in pairs
        ],
        "blocks": [
            {
                "start": b[0][0],
                "end": b[-1][0],
                "n": b[0][1],
                "weekends": len(b),
            }
            for b in blocks
        ],
    }
    out_path = Path(__file__).resolve().parent / "excel_patterns.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved {out_path}")


if __name__ == "__main__":
    main()
