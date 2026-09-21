"""Generate a human-readable byte-layout reference from the mission database.

The mission database (mdb/etana.yaml) is the single source of truth for packet
structure. This tool reads it through the same ccsds loader the codec uses and
emits a self-contained HTML page showing, for each packet: the CCSDS primary
header, a visual byte map, and a field table with offsets, sizes, encoding,
units, calibration, and enumerations.

Because it is generated from the mission database, the reference cannot drift:
regenerate it whenever etana.yaml changes.

Usage:
    python generate.py [path/to/etana.yaml] [-o output.html]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
from pathlib import Path

from ccsds import load_mission_db

HEADER_BYTES = 6  # CCSDS primary header


def _enc_label(enc: str, bits: int) -> str:
    base = {"unsigned_int": "uint", "signed_int": "int"}.get(enc, enc)
    return f"{base}{bits}"


def _field_rows(container):
    """Yield (offset, size_bytes, name, encoding, unit, detail) per field, after
    the 6-byte primary header."""
    offset = HEADER_BYTES
    for f in container.fields:
        size = f.type.size_bits // 8
        unit = getattr(f.type, "unit", None) or ""
        enc = _enc_label(f.type.encoding, f.type.size_bits)
        detail_parts = []
        cal = getattr(f.type, "calibrator", None)
        if cal is not None:
            coeffs = ", ".join(str(c) for c in cal.coefficients)
            detail_parts.append(f"calibrated: [{coeffs}]")
        enum = getattr(f.type, "enumeration", None)
        if enum:
            detail_parts.append("enum: " + ", ".join(f"{k}={v}" for k, v in enum.items()))
        desc = getattr(f, "description", "") or ""
        detail = desc + (("  ·  " + "  ·  ".join(detail_parts)) if detail_parts else "")
        yield offset, size, f.name, enc, unit, detail.strip()
        offset += size


def _byte_map_svg(container) -> str:
    """A visual byte grid: header bytes + each field's byte span, labelled."""
    rows = list(_field_rows(container))
    total = HEADER_BYTES + sum(r[1] for r in rows)

    cell = 30
    per_row = 16
    gap_y = 62
    n_rows = (total + per_row - 1) // per_row
    width = per_row * cell + 60
    height = n_rows * gap_y + 40

    # colour cycle for fields (header is fixed slate)
    palette = ["#00e5c7", "#4da3ff", "#ffb020", "#c98bff", "#ff8f6b", "#5fd08a"]
    # assign a colour per field span
    spans = [("HDR", HEADER_BYTES, "#3a4757")]
    for i, (_, size, name, *_rest) in enumerate(rows):
        spans.append((name, size, palette[i % len(palette)]))

    # expand to per-byte colour+label-start
    byte_owner = []  # (colour, is_first_of_field, label)
    for name, size, colour in spans:
        for j in range(size):
            byte_owner.append((colour, j == 0, name if j == 0 else ""))

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" '
             f'style="max-width:{width}px" xmlns="http://www.w3.org/2000/svg">']
    field_idx = -1
    for idx in range(total):
        r = idx // per_row
        c = idx % per_row
        x = 30 + c * cell
        y = 20 + r * gap_y
        colour, first, label = byte_owner[idx]
        parts.append(
            f'<rect x="{x}" y="{y}" width="{cell-2}" height="{cell-2}" rx="3" '
            f'fill="{colour}" fill-opacity="0.18" stroke="{colour}" stroke-opacity="0.7"/>'
        )
        parts.append(
            f'<text x="{x+(cell-2)/2}" y="{y+(cell-2)/2+4}" text-anchor="middle" '
            f'font-family="monospace" font-size="10" fill="#8a97a6">{idx}</text>'
        )
        if first and label:
            field_idx += 1
            # Stagger labels on two levels so adjacent short fields don't collide.
            dy = cell + 11 + (14 if field_idx % 2 else 0)
            parts.append(
                f'<line x1="{x+1}" y1="{y+cell-2}" x2="{x+1}" y2="{y+dy-9}" '
                f'stroke="{colour}" stroke-opacity="0.4" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{x+3}" y="{y+dy}" font-family="monospace" '
                f'font-size="9" fill="{colour}">{html.escape(label)}</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


def _render(db) -> str:
    generated = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mission = getattr(db, "name", "Etana")

    packets_html = []
    for name in db.containers:
        c = db.container(name)
        rows = list(_field_rows(c))
        total = HEADER_BYTES + sum(r[1] for r in rows)

        field_trs = "".join(
            f"<tr><td class='off'>{off}</td><td class='off'>{size}</td>"
            f"<td class='fname'>{html.escape(nm)}</td><td class='enc'>{enc}</td>"
            f"<td>{html.escape(unit)}</td><td class='detail'>{html.escape(detail)}</td></tr>"
            for (off, size, nm, enc, unit, detail) in rows
        )

        packets_html.append(f"""
        <section class="packet">
          <div class="phead">
            <h2>{html.escape(c.name)}</h2>
            <div class="meta">
              <span>APID <b>{c.apid}</b></span>
              <span>rate <b>{c.rate_hz} Hz</b></span>
              <span>size <b>{total} bytes</b></span>
            </div>
          </div>
          <p class="desc">{html.escape(getattr(c, 'description', '') or '')}</p>
          <div class="bytemap">{_byte_map_svg(c)}</div>
          <table>
            <thead><tr><th>Offset</th><th>Bytes</th><th>Field</th><th>Encoding</th><th>Unit</th><th>Notes</th></tr></thead>
            <tbody>{field_trs}</tbody>
          </table>
        </section>
        """)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(mission)} · Packet Byte Reference</title>
<style>
  :root {{
    --bg:#05070a; --panel:#0b1017; --line:#1b2632; --cyan:#00e5c7;
    --text:#d6e0ea; --muted:#8a97a6; --dim:#4a5765;
    --mono:"JetBrains Mono",ui-monospace,Menlo,monospace;
    --sans:"Inter",system-ui,sans-serif;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font-family:var(--sans);
    line-height:1.5; padding:0 0 60px; }}
  header {{ padding:28px 32px; border-bottom:1px solid var(--line);
    background:linear-gradient(180deg,#0f1721,#0b1017); }}
  header h1 {{ margin:0; font-size:18px; letter-spacing:0.12em; }}
  header h1 span {{ color:var(--cyan); }}
  header p {{ margin:6px 0 0; color:var(--muted); font-family:var(--mono); font-size:12px; }}
  .wrap {{ max-width:920px; margin:0 auto; padding:0 32px; }}
  .intro {{ color:var(--muted); font-size:14px; margin:24px 0; }}
  .intro code {{ font-family:var(--mono); color:var(--cyan); }}
  .packet {{ margin:34px 0; border:1px solid var(--line); border-radius:6px;
    background:var(--panel); overflow:hidden; }}
  .phead {{ display:flex; align-items:baseline; justify-content:space-between;
    padding:16px 20px; border-bottom:1px solid var(--line); }}
  .phead h2 {{ margin:0; font-family:var(--mono); font-size:16px; color:var(--cyan);
    letter-spacing:0.04em; }}
  .meta {{ display:flex; gap:18px; font-family:var(--mono); font-size:12px; color:var(--muted); }}
  .meta b {{ color:var(--text); }}
  .desc {{ padding:12px 20px 0; color:var(--muted); font-size:13px; margin:0; }}
  .bytemap {{ padding:18px 20px 8px; overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ text-align:left; padding:8px 20px; color:var(--dim); font-size:10px;
    letter-spacing:0.14em; text-transform:uppercase; border-bottom:1px solid var(--line); }}
  td {{ padding:8px 20px; border-bottom:1px solid rgba(27,38,50,0.5); vertical-align:top; }}
  .off {{ font-family:var(--mono); color:var(--muted); text-align:center; }}
  .fname {{ font-family:var(--mono); color:var(--text); }}
  .enc {{ font-family:var(--mono); color:var(--cyan); }}
  .detail {{ color:var(--muted); font-size:12px; }}
  footer {{ max-width:920px; margin:40px auto 0; padding:0 32px; color:var(--dim);
    font-family:var(--mono); font-size:11px; }}
</style></head>
<body>
<header>
  <h1>{html.escape(mission)}<span> · </span>PACKET BYTE REFERENCE</h1>
  <p>generated from mdb/etana.yaml · {generated}</p>
</header>
<div class="wrap">
  <p class="intro">
    Every packet begins with a 6-byte CCSDS primary header, followed by its fields
    in the order shown. Multi-byte fields are <b>big-endian</b>. Offsets and sizes
    are in bytes. This reference is generated from the mission database
    (<code>etana.yaml</code>) and matches exactly what the flight software encodes
    and the ground segment decodes.
  </p>
  {"".join(packets_html)}
</div>
<footer>Etana ground segment · regenerate with tools/byte-reference/generate.py</footer>
</body></html>"""


def main():
    ap = argparse.ArgumentParser(description="Generate the packet byte-layout reference")
    default_mdb = Path(__file__).resolve().parents[2] / "mdb" / "etana.yaml"
    ap.add_argument("mdb", nargs="?", default=str(default_mdb))
    ap.add_argument("-o", "--output", default="packet-reference.html")
    args = ap.parse_args()

    db = load_mission_db(args.mdb)
    Path(args.output).write_text(_render(db), encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
