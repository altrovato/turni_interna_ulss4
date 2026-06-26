"""Convert TURNI 2026.xlsx -> data/seed-turni-2026.json (formato app Turni Reparto)."""
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "TURNI 2026.xlsx"
OUT = ROOT / "data" / "seed-turni-2026.json"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
WE_ROT = {"VN", "SN", "SG", "MN", "MG"}
VALID_CODES = {
    "N", "G", "GM", "GP", "M", "M/AI", "M/AD", "M/AR", "AR", "AR/AR", "AR/GP",
    "AD", "AI", "MA", "F", "P", "MAL", "C", "R", "RF", "RN", "SN", "/", "//",
}


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


def med_id(name):
    slug = re.sub(r"[^A-Z0-9]", "", name.upper())[:16].lower()
    return f"m_{slug or 'med'}"


def mk_medico(name):
    return {
        "id": med_id(name),
        "nome": name.strip().upper(),
        "attivo": True,
        "puoNotte": True,
        "puoWeekend": True,
        "oreSett": 38,
        "decCalabria": False,
        "competenze": {"AI": True, "AD": True, "AR": True},
        "email": "",
        "ruolo": "medico",
        "faTurni": False,
    }


def infer_we(fri, sat, sun):
    fri, sat, sun = norm(fri), norm(sat), norm(sun)
    if sat in ("F", "MAL", "C") or sun in ("F", "MAL", "C") or fri in ("F", "MAL", "C"):
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
    if sat in ("", "/") and sun in ("", "/"):
        return "/"
    if sat == "SN":
        return "SN"
    for c in (sat, sun, fri):
        if c in WE_ROT:
            return c
    if sat.startswith("?") or sun.startswith("?"):
        parts = (sat + "|" + sun + "|" + fri).split("|")
        for p in parts:
            p = p.lstrip("?")
            if p in WE_ROT:
                return p
    return "/"


def load_sheets():
    with zipfile.ZipFile(XLSX) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
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
    docs = [hdr[c].strip().upper() for c in doc_cols]
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


def sab_key(d):
    return d.strftime("%Y-%m-%d")


def main():
    if not XLSX.exists():
        raise SystemExit(f"File non trovato: {XLSX}")

    sheets = load_sheets()
    all_by_date = {}
    doctor_names = []
    for name, rows in sheets.items():
        if "bis" in name.lower():
            continue
        docs, by = parse_days(rows)
        if docs:
            doctor_names = docs
        all_by_date.update(by)

    doctor_names = list(dict.fromkeys(doctor_names))
    id_by_name = {n: med_id(n) for n in doctor_names}
    organico = [mk_medico(n) for n in doctor_names]

    mesi = defaultdict(lambda: {"turni": defaultdict(dict), "assenze": []})
    for d, shifts in sorted(all_by_date.items()):
        key = f"{d.year}-{d.month - 1}"
        g = d.day
        for name, code in shifts.items():
            if not code or code not in VALID_CODES:
                continue
            mid = id_by_name[name]
            mesi[key]["turni"][mid][str(g)] = code

    mesi_out = {}
    for k, v in mesi.items():
        mesi_out[k] = {
            "turni": {mid: dict(cells) for mid, cells in v["turni"].items()},
            "assenze": [],
        }

    weekend_celle = defaultdict(dict)
    dates = sorted(all_by_date.keys())
    for d in dates:
        if d.weekday() != 5:
            continue
        sun = d + timedelta(days=1)
        fri = d - timedelta(days=1)
        if sun not in all_by_date:
            continue
        key = sab_key(d)
        for name in doctor_names:
            role = infer_we(
                all_by_date.get(fri, {}).get(name, ""),
                all_by_date[d].get(name, ""),
                all_by_date[sun].get(name, ""),
            )
            if role and role != "/":
                weekend_celle[id_by_name[name]][key] = role

    note = (
        "REGOLE PROMEMORIA:\n"
        "- Domenica: solo medico di guardia (N/G); nessun giro in reparto; minimo 6 e ideale 7 non valgono.\n"
        "- Lunedì: recupero a chi fa guardia domenica; guardia a chi ha weekend libero.\n"
        "- Venerdì: guardia a chi ha sabato notte o weekend libero.\n"
        "- Evitare guardia il martedì dopo riposo del lunedì (di chi ha fatto guardia domenica).\n"
        "- Recupero per festivi, mezzi festivi, notti di sab/dom e notti su festivo.\n"
        "- Max 12 giorni lavorativi consecutivi (meglio meno).\n\n"
        "AMBULATORI:\n"
        "- Lun pom: amb. medicina interna\n"
        "- Mar mattina: amb. reumato\n"
        "- Mer pom: amb. doppler\n"
        "- Gio pom: amb. reumato (1° giovedì del mese alla Marotta per capillaroscopie)"
    )

    db = {
        "oreVersion": 2,
        "organico": organico,
        "mesi": mesi_out,
        "weekend": {"celle": {mid: dict(c) for mid, c in weekend_celle.items()}, "celleFormat": 1},
        "scambi": [],
        "ore": {
            "N": 12, "G": 12, "GM": 6, "GP": 6, "M": 5, "M/AI": 6, "M/AD": 7, "M/AR": 10,
            "AR": 5, "AR/AR": 10, "AR/GP": 11, "AD": 5, "AI": 5, "MA": 11,
            "F": 6.33, "P": 0, "MAL": 6.33, "C": 6.33, "R": 0, "RF": 0, "RN": 0, "SN": 0,
            "/": 0, "//": 0, "": 0,
        },
        "req": {
            "notte": 1, "giorno": 1, "reparto": 3, "tot": 6, "ideale": 7,
            "idealeFeriale": 7, "smezzaGuardie": False,
        },
        "note": note,
        "_seedMeta": {
            "source": "TURNI 2026.xlsx",
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "doctors": len(organico),
            "months": len(mesi_out),
            "weekendKeys": sum(len(v) for v in weekend_celle.values()),
            "days": len(all_by_date),
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = db["_seedMeta"]
    print(f"Salvato {OUT}")
    print(f"  Medici: {meta['doctors']}")
    print(f"  Mesi: {meta['months']}")
    print(f"  Giorni turni: {meta['days']}")
    print(f"  Assegnazioni weekend: {meta['weekendKeys']}")


if __name__ == "__main__":
    main()
