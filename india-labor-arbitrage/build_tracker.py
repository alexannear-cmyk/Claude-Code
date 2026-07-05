#!/usr/bin/env python3
"""Generate India_Labor_Arbitrage_Tracker.xlsx — monthly consolidation workbook.

Structure:
  READ ME            instructions
  Setup              org display names (single place to rename) + dropdown lists
  Targets            committed monthly baseline by org (placeholder values)
  Org_1 .. Org_8     identical monthly input tabs, one per organization
  Consolidation      3-D sums across the eight org tabs
  Dashboard          corporate summary: KPIs, annual table, monthly trend, RAG grid
  Guiding Principles condensed rules of the road

Regenerate any time with:  python3 build_tracker.py
"""

from datetime import datetime

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

# ---------------------------------------------------------------- constants

N_ORGS = 8
START_YEAR, N_MONTHS = 2026, 48          # Jan-2026 .. Dec-2029
FIRST_COL = 3                            # months start in column C
LAST_COL = FIRST_COL + N_MONTHS - 1      # column AX
MONTH_COLS = [get_column_letter(c) for c in range(FIRST_COL, LAST_COL + 1)]
MONTHS = [datetime(START_YEAR + m // 12, m % 12 + 1, 1) for m in range(N_MONTHS)]

CATEGORIES = [
    "Professional services",
    "Offshore contractors",
    "Onshore contractors",
    "Employees / Other",
]

# relative org size factors used only for illustrative placeholder targets
ORG_FACTORS = [1.5, 1.3, 1.2, 1.1, 1.0, 0.9, 0.7, 0.3]

# ---------------------------------------------------------------- styles

TITLE_F = Font(bold=True, size=14, color="1F3864")
SECTION_FILL = PatternFill("solid", fgColor="1F3864")
SECTION_F = Font(bold=True, color="FFFFFF")
HDR_FILL = PatternFill("solid", fgColor="D6DCE5")
HDR_F = Font(bold=True)
INPUT_FILL = PatternFill("solid", fgColor="DDEBF7")     # light blue = enter data
CENTRAL_FILL = PatternFill("solid", fgColor="E2EFDA")   # light green = central fill
TARGET_FILL = PatternFill("solid", fgColor="F2F2F2")    # grey = linked target
PLACEHOLDER_FILL = PatternFill("solid", fgColor="FFF2CC")
BOLD = Font(bold=True)
NOTE_F = Font(italic=True, color="808080")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

NUM = "#,##0"
NUM_K = '#,##0;[Red](#,##0)'
PCT = "0%"


def style_row(ws, row, fill=None, font=None, fmt=None, first=FIRST_COL, last=LAST_COL):
    for c in range(first, last + 1):
        cell = ws.cell(row=row, column=c)
        if fill:
            cell.fill = fill
        if font:
            cell.font = font
        if fmt:
            cell.number_format = fmt
        cell.border = BOX


def month_header(ws, header_row):
    """Year row (header_row-1) + month row (header_row) across the 48 columns."""
    for m, dt in enumerate(MONTHS):
        col = FIRST_COL + m
        if dt.month == 1:
            yc = ws.cell(row=header_row - 1, column=col, value=dt.year)
            yc.font = BOLD
        cell = ws.cell(row=header_row, column=col, value=dt)
        cell.number_format = "mmm-yy"
        cell.font = HDR_F
        cell.fill = HDR_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = BOX
    ws.cell(row=header_row, column=1, value="Metric").font = HDR_F
    ws.cell(row=header_row, column=2, value="Unit / who fills").font = HDR_F
    ws.cell(row=header_row, column=1).fill = HDR_FILL
    ws.cell(row=header_row, column=2).fill = HDR_FILL
    ws.column_dimensions["A"].width = 46
    ws.column_dimensions["B"].width = 20
    for cl in MONTH_COLS:
        ws.column_dimensions[cl].width = 10.5


# ---------------------------------------------------------------- placeholders

def placeholder_targets(org_idx):
    """Illustrative monthly baseline for one org. Returns dict of 48-length lists."""
    f = ORG_FACTORS[org_idx]
    hires = [round((6 if m < 12 else 10 if m < 24 else 0) * f) for m in range(N_MONTHS)]
    cum = 0
    cum_hires = []
    for h in hires:
        cum += h
        cum_hires.append(cum)
    caps = {"Professional services": 600, "Offshore contractors": 250,
            "Onshore contractors": 200, "Employees / Other": 100}
    starts = {"Professional services": 3, "Offshore contractors": 6,
              "Onshore contractors": 6, "Employees / Other": 9}
    slopes = {"Professional services": 25, "Offshore contractors": 10,
              "Onshore contractors": 8, "Employees / Other": 4}
    red = {cat: [round(min(slopes[cat] * max(0, m - starts[cat]), caps[cat]) * f)
                 for m in range(N_MONTHS)] for cat in CATEGORIES}
    # India loaded cost ~ $45K/yr per head => 3.75 $K per head-month
    adds = [round(c * 3.75) for c in cum_hires]
    return {"hires": hires, "red": red, "adds": adds}


# ---------------------------------------------------------------- workbook

wb = Workbook()

# ---------- READ ME ----------
ws = wb.active
ws.title = "READ ME"
readme = [
    ("India Labor Arbitrage Program — Monthly Consolidation Workbook", TITLE_F),
    ("", None),
    ("PURPOSE", BOLD),
    ("Single consolidation file for the India GCC ramp-up program. Each org finance partner "
     "updates their own Org tab monthly; the Consolidation and Dashboard tabs roll up automatically.", None),
    ("", None),
    ("HOW TO SET UP (owner, one time)", BOLD),
    ("1. Go to the Setup tab and replace 'Org 1 — REPLACE' etc. with the real organization names. "
     "Every tab picks the names up automatically.", None),
    ("2. Optionally rename the Org_1..Org_8 sheet tabs to match — Excel updates all formulas "
     "automatically when a sheet is renamed.", None),
    ("3. Replace the ILLUSTRATIVE placeholder numbers on the Targets tab with the committed monthly "
     "baseline you distributed to each org (yellow cells).", None),
    ("4. Org_1 contains EXAMPLE actuals for Jan–Mar 2026 to demonstrate the mechanics — clear them "
     "before first use.", None),
    ("", None),
    ("HOW TO SUBMIT (org finance partners, monthly)", BOLD),
    ("1. Open your org's tab. Enter values in BLUE cells only for the month just closed.", None),
    ("2. GREEN cells are filled centrally from PlanIt/HR — do not overwrite unless asked.", None),
    ("3. GREY cells are your committed targets, linked from the Targets tab — never edit on this tab.", None),
    ("4. Set the month's RAG status, answer the leakage attestation, and add commentary if any "
     "headline metric misses target materially. Enter your name in the 'Attested by' row.", None),
    ("5. Submissions are due workday 3; consolidation is published workday 5. (Placeholder — confirm.)", None),
    ("", None),
    ("RULES", BOLD),
    ("What counts as labor arbitrage savings (and what doesn't) is defined on the Guiding Principles "
     "tab. Read it before your first submission. When in doubt, ask central program finance BEFORE "
     "reporting a number.", None),
    ("", None),
    ("DO NOT", BOLD),
    ("• Insert new sheets between Org_1 and Org_8 (the consolidation ranges span those tabs).", None),
    ("• Add or delete rows/columns on Org tabs — the consolidation reads fixed positions.", None),
    ("• Net one-time transition costs into your reduction numbers — report them on their own row.", None),
    ("", None),
    ("COLOR KEY", BOLD),
    ("BLUE = org enters data   |   GREEN = central fill (PlanIt/HR)   |   GREY = linked target "
     "(do not edit)   |   YELLOW = placeholder to replace during setup", None),
]
for i, (text, font) in enumerate(readme, start=1):
    c = ws.cell(row=i, column=1, value=text)
    if font:
        c.font = font
ws.column_dimensions["A"].width = 120
for r in range(1, len(readme) + 1):
    ws.cell(row=r, column=1).alignment = Alignment(wrap_text=True, vertical="top")

# ---------- Setup ----------
ws = wb.create_sheet("Setup")
ws.cell(row=1, column=1, value="Setup — organization names and lists").font = TITLE_F
ws.cell(row=3, column=1, value="REPLACE the names below with your 8 organizations. "
        "All tabs reference these cells.").font = NOTE_F
ORG_NAME_ROW0 = 4  # org i display name lives at Setup!B(4+i)
for i in range(N_ORGS):
    ws.cell(row=ORG_NAME_ROW0 + i, column=1, value=f"Org tab Org_{i+1} display name:")
    c = ws.cell(row=ORG_NAME_ROW0 + i, column=2, value=f"Org {i+1} — REPLACE")
    c.fill = PLACEHOLDER_FILL
    c.font = BOLD
    c.border = BOX
ws.cell(row=13, column=1, value="Dropdown lists (used by data validation):").font = NOTE_F
ws.cell(row=14, column=1, value="RAG:")
for j, v in enumerate(["Green", "Amber", "Red"]):
    ws.cell(row=14 + j, column=2, value=v)
ws.cell(row=18, column=1, value="Yes/No:")
ws.cell(row=18, column=2, value="Y")
ws.cell(row=19, column=2, value="N")
ws.column_dimensions["A"].width = 34
ws.column_dimensions["B"].width = 40
RAG_LIST = "Setup!$B$14:$B$16"
YN_LIST = "Setup!$B$18:$B$19"


def org_name_ref(i):
    return f"Setup!$B${ORG_NAME_ROW0 + i}"


# ---------- Targets ----------
ws = wb.create_sheet("Targets")
ws.cell(row=1, column=1, value="Committed monthly baseline by organization").font = TITLE_F
ws.cell(row=2, column=1, value="ILLUSTRATIVE PLACEHOLDERS — replace every yellow cell with the "
        "committed baseline distributed to the orgs. Baseline changes only via approved change "
        "request.").font = Font(bold=True, color="C00000")
month_header(ws, 5)
ws.freeze_panes = "C6"

TGT_BLOCK = 9  # header + 7 metric rows + spacer
TGT_START = 7

# per-org block: header, hires, 4 category rows, India adds, net (formula)
for i in range(N_ORGS):
    base = TGT_START + i * TGT_BLOCK
    ph = placeholder_targets(i)
    hdr = ws.cell(row=base, column=1, value=f'=CONCATENATE("ORG: ",{org_name_ref(i)})')
    hdr.font = SECTION_F
    style_row(ws, base, fill=SECTION_FILL, first=1)
    layout = [
        (base + 1, "India hires (heads)", ph["hires"], NUM, False),
        (base + 2, f"Reductions — {CATEGORIES[0]} ($K)", ph["red"][CATEGORIES[0]], NUM_K, False),
        (base + 3, f"Reductions — {CATEGORIES[1]} ($K)", ph["red"][CATEGORIES[1]], NUM_K, False),
        (base + 4, f"Reductions — {CATEGORIES[2]} ($K)", ph["red"][CATEGORIES[2]], NUM_K, False),
        (base + 5, f"Reductions — {CATEGORIES[3]} ($K)", ph["red"][CATEGORIES[3]], NUM_K, False),
        (base + 6, "India cost adds ($K)", ph["adds"], NUM_K, False),
        (base + 7, "Net labor arbitrage ($K)", None, NUM_K, True),
    ]
    for r, label, values, fmt, is_net in layout:
        lc = ws.cell(row=r, column=1, value=label)
        if is_net:
            lc.font = BOLD
        for m, cl in enumerate(MONTH_COLS):
            cell = ws.cell(row=r, column=FIRST_COL + m)
            if is_net:
                cell.value = f"=SUM({cl}{base+2}:{cl}{base+5})-{cl}{base+6}"
                cell.font = BOLD
            else:
                cell.value = values[m]
                cell.fill = PLACEHOLDER_FILL
            cell.number_format = fmt
            cell.border = BOX

TARGETS = {i: {"hires": TGT_START + i * TGT_BLOCK + 1,
               "cats": {cat: TGT_START + i * TGT_BLOCK + 2 + j
                        for j, cat in enumerate(CATEGORIES)},
               "adds": TGT_START + i * TGT_BLOCK + 6,
               "net": TGT_START + i * TGT_BLOCK + 7}
           for i in range(N_ORGS)}


# ---------- Org tabs ----------
# Row layout shared by all org tabs and (structurally) by Consolidation.
def build_org_layout():
    """Return ordered list of (key, label, unit, kind) and a key->row map.

    kind: 'section' | 'input' | 'central' | 'target' | 'formula' | 'text' | 'dropdown_rag'
          | 'dropdown_yn'
    """
    rows, r = [], 6

    def add(key, label, unit, kind):
        nonlocal r
        rows.append((r, key, label, unit, kind))
        r += 1

    add("secA", "A.  INDIA HIRING", "", "section")
    add("hires_t", "India hires — Target", "heads · linked", "target")
    add("hires_a", "India hires — Actual", "heads · central (PlanIt)", "central")
    add("hires_ct", "Cumulative hires — Target", "heads · auto", "formula")
    add("hires_ca", "Cumulative hires — Actual", "heads · auto", "formula")
    add("hires_v", "Hires variance (Actual − Target), cumulative", "heads · auto", "formula")
    add("comp_p", "Avg India loaded comp — Plan", "$K/yr · central (PlanIt)", "central")
    add("comp_a", "Avg India loaded comp — Actual", "$K/yr · central (PlanIt)", "central")
    add("attrition", "India attrition in month", "heads · central (HR)", "central")
    add("productive", "% of India hires fully productive", "% · org input", "input")

    add("secB", "B.  GROSS REDUCTIONS REALIZED IN PERIOD", "", "section")
    for j, cat in enumerate(CATEGORIES):
        add(f"red_t{j}", f"{cat} — Target", "$K · linked", "target")
        add(f"red_a{j}", f"{cat} — Actual", "$K · org input", "input")
    add("red_tt", "Total gross reductions — Target", "$K · auto", "formula")
    add("red_ta", "Total gross reductions — Actual", "$K · auto", "formula")
    add("red_v", "Gross reductions variance", "$K · auto", "formula")
    add("hc_red", "Headcount reduced in month — Actual", "heads · org input", "input")
    add("runrate", "Exit run-rate of reductions (annualized)", "$K · org input", "input")

    add("secC", "C.  INDIA COST ADDS", "", "section")
    add("adds_t", "India loaded cost adds — Target", "$K · linked", "target")
    add("adds_a", "India loaded cost adds — Actual", "$K · org input", "input")
    add("onetime", "One-time transition costs (memo — never net)", "$K · org input", "input")

    add("secD", "D.  NET LABOR ARBITRAGE  (B − C)", "", "section")
    add("net_t", "Net labor arbitrage — Target", "$K · linked", "target")
    add("net_a", "Net labor arbitrage — Actual", "$K · auto", "formula")
    add("net_v", "Net variance (Actual − Target)", "$K · auto", "formula")
    add("net_cum_t", "Cumulative net arbitrage — Target", "$K · auto", "formula")
    add("net_cum_a", "Cumulative net arbitrage — Actual", "$K · auto", "formula")

    add("secE", "E.  STATUS, ATTESTATION & COMMENTARY", "", "section")
    add("rag", "Overall RAG status for month", "G/A/R · org input", "dropdown_rag")
    add("leakage", "Attest: reductions free of leakage?", "Y/N · org input", "dropdown_yn")
    add("attest", "Attested by (org finance partner)", "name · org input", "text")
    add("comment", "Commentary (required on material variance)", "text · org input", "text")
    return rows, {key: rr for rr, key, *_ in rows}


ORG_ROWS, R = build_org_layout()

EXAMPLE_ACTUALS = {  # Org_1 Jan–Mar 2026 demo values, cleared by owner before use
    "hires_a": [5, 6, 6], "comp_p": [45, 45, 45], "comp_a": [44, 46, 47],
    "attrition": [0, 0, 1], "productive": [0.0, 0.2, 0.4],
    "red_a0": [0, 20, 45], "red_a1": [0, 0, 10], "red_a2": [0, 0, 5], "red_a3": [0, 0, 0],
    "hc_red": [0, 1, 3], "runrate": [0, 240, 720],
    "adds_a": [19, 41, 64], "onetime": [35, 15, 10],
    "rag": ["Green", "Green", "Amber"],
    "leakage": ["Y", "Y", "Y"],
    "attest": ["A. Partner", "A. Partner", "A. Partner"],
    "comment": ["", "", "Prof services roll-off slipped ~1 month; recovery expected Apr."],
}

KIND_FILL = {"input": INPUT_FILL, "central": CENTRAL_FILL, "target": TARGET_FILL,
             "dropdown_rag": INPUT_FILL, "dropdown_yn": INPUT_FILL, "text": INPUT_FILL}

for i in range(N_ORGS):
    ws = wb.create_sheet(f"Org_{i+1}")
    t = ws.cell(row=1, column=1, value=f'=CONCATENATE("ORG: ",{org_name_ref(i)})')
    t.font = TITLE_F
    ws.cell(row=2, column=1, value="Enter BLUE cells only. GREEN = central fill. GREY = linked "
            "target (do not edit). See READ ME + Guiding Principles tabs.").font = NOTE_F
    month_header(ws, 5)
    ws.freeze_panes = "C6"
    tg = TARGETS[i]

    for r, key, label, unit, kind in ORG_ROWS:
        lc = ws.cell(row=r, column=1, value=label)
        ws.cell(row=r, column=2, value=unit).font = NOTE_F
        if kind == "section":
            lc.font = SECTION_F
            style_row(ws, r, fill=SECTION_FILL, first=1)
            continue
        fmt = PCT if key == "productive" else NUM if "heads" in unit else NUM_K
        if key in ("attest", "comment", "rag", "leakage"):
            fmt = "General"
        for m, cl in enumerate(MONTH_COLS):
            cell = ws.cell(row=r, column=FIRST_COL + m)
            cell.number_format = fmt
            cell.border = BOX
            fill = KIND_FILL.get(kind)
            if fill:
                cell.fill = fill
            # formulas
            if kind == "target":
                src = {"hires_t": tg["hires"], "adds_t": tg["adds"], "net_t": tg["net"]}
                row_src = src.get(key)
                if row_src is None:  # category target rows red_t0..3
                    j = int(key[-1])
                    row_src = tg["cats"][CATEGORIES[j]]
                cell.value = f"=Targets!{cl}{row_src}"
            elif kind == "formula":
                first_cl = MONTH_COLS[0]
                prev_cl = MONTH_COLS[m - 1] if m else None
                if key == "hires_ct":
                    cell.value = f"=SUM(${first_cl}{R['hires_t']}:{cl}{R['hires_t']})"
                elif key == "hires_ca":
                    cell.value = f"=SUM(${first_cl}{R['hires_a']}:{cl}{R['hires_a']})"
                elif key == "hires_v":
                    cell.value = f"={cl}{R['hires_ca']}-{cl}{R['hires_ct']}"
                elif key == "red_tt":
                    cell.value = "=" + "+".join(f"{cl}{R[f'red_t{j}']}" for j in range(4))
                elif key == "red_ta":
                    cell.value = "=" + "+".join(f"{cl}{R[f'red_a{j}']}" for j in range(4))
                elif key == "red_v":
                    cell.value = f"={cl}{R['red_ta']}-{cl}{R['red_tt']}"
                elif key == "net_a":
                    cell.value = f"={cl}{R['red_ta']}-{cl}{R['adds_a']}"
                elif key == "net_v":
                    cell.value = f"={cl}{R['net_a']}-{cl}{R['net_t']}"
                elif key == "net_cum_t":
                    cell.value = f"=SUM(${first_cl}{R['net_t']}:{cl}{R['net_t']})"
                elif key == "net_cum_a":
                    cell.value = f"=SUM(${first_cl}{R['net_a']}:{cl}{R['net_a']})"
                if key.startswith(("net", "red_t")):
                    cell.font = BOLD
        if key in ("net_a", "net_v", "net_cum_a", "red_tt", "red_ta"):
            style_row(ws, r, font=BOLD, fmt=fmt)

    # data validation
    dv_rag = DataValidation(type="list", formula1=f"={RAG_LIST}", allow_blank=True)
    dv_yn = DataValidation(type="list", formula1=f"={YN_LIST}", allow_blank=True)
    ws.add_data_validation(dv_rag)
    ws.add_data_validation(dv_yn)
    dv_rag.add(f"{MONTH_COLS[0]}{R['rag']}:{MONTH_COLS[-1]}{R['rag']}")
    dv_yn.add(f"{MONTH_COLS[0]}{R['leakage']}:{MONTH_COLS[-1]}{R['leakage']}")

    # demo data on Org_1 only
    if i == 0:
        for key, vals in EXAMPLE_ACTUALS.items():
            for m, v in enumerate(vals):
                if v != "":
                    ws.cell(row=R[key], column=FIRST_COL + m, value=v)

ORG_SHEET_RANGE = "'Org_1:Org_8'"

# ---------- Consolidation ----------
ws = wb.create_sheet("Consolidation")
ws.cell(row=1, column=1, value="Program consolidation — all organizations").font = TITLE_F
ws.cell(row=2, column=1, value="All values calculated. Numeric rows sum across Org_1..Org_8; "
        "comp and % rows are simple averages across orgs.").font = NOTE_F
month_header(ws, 5)
ws.freeze_panes = "C6"

AVERAGE_KEYS = {"comp_p", "comp_a", "productive"}
SKIP_KEYS = {"rag", "leakage", "attest", "comment"}

for r, key, label, unit, kind in ORG_ROWS:
    lc = ws.cell(row=r, column=1, value=label)
    ws.cell(row=r, column=2, value=unit.split("·")[0].strip() + " · auto").font = NOTE_F
    if kind == "section":
        lc.font = SECTION_F
        style_row(ws, r, fill=SECTION_FILL, first=1)
        continue
    if key in SKIP_KEYS:
        ws.cell(row=r, column=2, value="see org tabs / Dashboard").font = NOTE_F
        continue
    fmt = PCT if key == "productive" else NUM if "heads" in unit else NUM_K
    first_cl = MONTH_COLS[0]
    for m, cl in enumerate(MONTH_COLS):
        cell = ws.cell(row=r, column=FIRST_COL + m)
        cell.number_format = fmt
        cell.border = BOX
        if key in AVERAGE_KEYS:
            cell.value = f"=IFERROR(AVERAGE({ORG_SHEET_RANGE}!{cl}{r}),\"\")"
        elif key == "hires_ct":
            cell.value = f"=SUM(${first_cl}{R['hires_t']}:{cl}{R['hires_t']})"
        elif key == "hires_ca":
            cell.value = f"=SUM(${first_cl}{R['hires_a']}:{cl}{R['hires_a']})"
        elif key == "hires_v":
            cell.value = f"={cl}{R['hires_ca']}-{cl}{R['hires_ct']}"
        elif key == "red_tt":
            cell.value = "=" + "+".join(f"{cl}{R[f'red_t{j}']}" for j in range(4))
        elif key == "red_ta":
            cell.value = "=" + "+".join(f"{cl}{R[f'red_a{j}']}" for j in range(4))
        elif key == "red_v":
            cell.value = f"={cl}{R['red_ta']}-{cl}{R['red_tt']}"
        elif key == "net_a":
            cell.value = f"={cl}{R['red_ta']}-{cl}{R['adds_a']}"
        elif key == "net_v":
            cell.value = f"={cl}{R['net_a']}-{cl}{R['net_t']}"
        elif key == "net_cum_t":
            cell.value = f"=SUM(${first_cl}{R['net_t']}:{cl}{R['net_t']})"
        elif key == "net_cum_a":
            cell.value = f"=SUM(${first_cl}{R['net_a']}:{cl}{R['net_a']})"
        else:  # plain 3-D sum of the same row across org tabs
            cell.value = f"=SUM({ORG_SHEET_RANGE}!{cl}{r})"
    if key in ("net_a", "net_v", "net_cum_a", "red_tt", "red_ta"):
        style_row(ws, r, font=BOLD, fmt=fmt)

# ---------- Dashboard ----------
ws = wb.create_sheet("Dashboard")
ws.cell(row=1, column=1, value="India Labor Arbitrage Program — Executive Dashboard").font = TITLE_F
ws.column_dimensions["A"].width = 46
ws.column_dimensions["B"].width = 20

# KPI block
kpis = [
    ("Cumulative India hires — Target (program)",
     f"=SUM(Consolidation!{MONTH_COLS[0]}{R['hires_t']}:{MONTH_COLS[-1]}{R['hires_t']})", NUM),
    ("Cumulative India hires — Actual (program)",
     f"=SUM(Consolidation!{MONTH_COLS[0]}{R['hires_a']}:{MONTH_COLS[-1]}{R['hires_a']})", NUM),
    ("Net labor arbitrage ITD — Target ($K)",
     f"=SUM(Consolidation!{MONTH_COLS[0]}{R['net_t']}:{MONTH_COLS[-1]}{R['net_t']})", NUM_K),
    ("Net labor arbitrage ITD — Actual ($K)",
     f"=SUM(Consolidation!{MONTH_COLS[0]}{R['net_a']}:{MONTH_COLS[-1]}{R['net_a']})", NUM_K),
    ("Exit run-rate of reductions, latest reported ($K annualized)",
     f"=LOOKUP(9.99E+307,Consolidation!{MONTH_COLS[0]}{R['runrate']}:{MONTH_COLS[-1]}{R['runrate']})",
     NUM_K),
]
ws.cell(row=3, column=1, value="PROGRAM KPIs (inception-to-date over all entered months)").font = HDR_F
for j, (label, formula, fmt) in enumerate(kpis):
    ws.cell(row=4 + j, column=1, value=label)
    c = ws.cell(row=4 + j, column=2, value=formula)
    c.number_format = fmt
    c.font = BOLD
    c.border = BOX

# Annual summary table
ws.cell(row=11, column=1, value="ANNUAL SUMMARY").font = HDR_F
years = [2026, 2027, 2028, 2029]
for k, y in enumerate(years):
    c = ws.cell(row=12, column=2 + k, value=y)
    c.font = HDR_F
    c.fill = HDR_FILL
    c.border = BOX
annual_rows = [
    ("India hires — Target (heads)", R["hires_t"], NUM),
    ("India hires — Actual (heads)", R["hires_a"], NUM),
    ("Gross reductions — Target ($K)", R["red_tt"], NUM_K),
    ("Gross reductions — Actual ($K)", R["red_ta"], NUM_K),
    ("India cost adds — Actual ($K)", R["adds_a"], NUM_K),
    ("One-time transition costs ($K)", R["onetime"], NUM_K),
    ("Net labor arbitrage — Target ($K)", R["net_t"], NUM_K),
    ("Net labor arbitrage — Actual ($K)", R["net_a"], NUM_K),
]
for j, (label, src_row, fmt) in enumerate(annual_rows):
    rr = 13 + j
    ws.cell(row=rr, column=1, value=label)
    for k in range(4):
        c1 = get_column_letter(FIRST_COL + 12 * k)
        c2 = get_column_letter(FIRST_COL + 12 * k + 11)
        c = ws.cell(row=rr, column=2 + k,
                    value=f"=SUM(Consolidation!{c1}{src_row}:{c2}{src_row})")
        c.number_format = fmt
        c.border = BOX
        if "Net" in label:
            c.font = BOLD
for k in range(4):
    ws.column_dimensions[get_column_letter(2 + k)].width = 14

# Monthly trend (net arbitrage) + RAG grid share the month axis
TREND_HDR = 23
month_header(ws, TREND_HDR)
ws.cell(row=TREND_HDR - 1, column=1, value="MONTHLY TREND — NET LABOR ARBITRAGE ($K)").font = HDR_F
trend_rows = [
    ("Net arbitrage — Target", R["net_t"], NUM_K),
    ("Net arbitrage — Actual", R["net_a"], NUM_K),
    ("Cumulative — Target", R["net_cum_t"], NUM_K),
    ("Cumulative — Actual", R["net_cum_a"], NUM_K),
]
for j, (label, src_row, fmt) in enumerate(trend_rows):
    rr = TREND_HDR + 1 + j
    ws.cell(row=rr, column=1, value=label)
    for cl in MONTH_COLS:
        c = ws[f"{cl}{rr}"]
        c.value = f"=Consolidation!{cl}{src_row}"
        c.number_format = fmt
        c.border = BOX

RAG_HDR = TREND_HDR + 7
ws.cell(row=RAG_HDR - 1, column=1, value="RAG STATUS BY ORGANIZATION").font = HDR_F
for i in range(N_ORGS):
    rr = RAG_HDR + i
    ws.cell(row=rr, column=1, value=f"={org_name_ref(i)}").font = BOLD
    for cl in MONTH_COLS:
        c = ws[f"{cl}{rr}"]
        c.value = f"=IF('Org_{i+1}'!{cl}{R['rag']}=\"\",\"\",'Org_{i+1}'!{cl}{R['rag']})"
        c.alignment = Alignment(horizontal="center")
        c.border = BOX
rag_range = f"{MONTH_COLS[0]}{RAG_HDR}:{MONTH_COLS[-1]}{RAG_HDR + N_ORGS - 1}"
for val, color in [("Green", "C6EFCE"), ("Amber", "FFE699"), ("Red", "FFC7CE")]:
    ws.conditional_formatting.add(
        rag_range,
        CellIsRule(operator="equal", formula=[f'"{val}"'],
                   fill=PatternFill("solid", fgColor=color)))
ws.freeze_panes = "C2"

# ---------- Guiding Principles (condensed) ----------
ws = wb.create_sheet("Guiding Principles")
gp = [
    ("Guiding Principles — condensed (full draft: Guiding_Principles_DRAFT.md)", TITLE_F),
    ("", None),
    ("1. The baseline is the committed monthly target loaded to your forecast. Variances are vs. "
     "that baseline — never vs. prior year or re-forecast. Baseline moves only via approved change "
     "request, required for changes with in-year savings impact of $500K+ in any year (proposed "
     "threshold); smaller items are handled via commentary and do NOT restate the baseline.", None),
    ("2. A reduction COUNTS only if it is (a) labor cost in a committed category — professional "
     "services, managed/outsourced labor, offshore or onshore contractors, in-scope employees; "
     "(b) causally tied to the India transition; (c) realized and visible in the GL; and "
     "(d) run-rate in nature.", None),
    ("3. What does NOT count: software license or any non-labor favorability; one-time credits or "
     "rebates; rate renegotiations unrelated to transitioned volume; timing deferrals; unrelated "
     "vacancy savings; anything already claimed by another initiative (no double counting).", None),
    ("4. NO SUBSTITUTION: a labor-reduction shortfall may not be offset with unrelated favorability. "
     "Example: on-track India hiring + $500K prof services miss + $500K software favorability is "
     "reported as a $500K program miss, with commentary and recovery plan.", None),
    ("5. Report NET: gross reductions minus India loaded cost adds. One-time transition costs go on "
     "their own row and are never netted into reductions or run-rate.", None),
    ("5a. IN-YEAR IS THE COMMITMENT: the enterprise committed in-year savings targets by year for "
     "2025-2029, allocated by sub-organization. Exit run-rate is a diagnostic only — being 'on "
     "track on run-rate' never offsets or excuses an in-year miss. Run-rate belongs in recovery-"
     "plan commentary, not the scorecard.", None),
    ("6. Recognize savings in the month the run-rate reduction first hits the GL — not at contract "
     "signature or vendor notification. Partial months pro rata.", None),
    ("7. No leakage: a reduction is not real if equivalent spend reappears in another cost center, "
     "vendor, or expense line. You attest to this monthly.", None),
    ("8. Attestation & evidence: the org finance partner attests each submission and can identify "
     "the cost center and expense line for material reductions on request. Quarterly sample "
     "testing and true-up apply.", None),
    ("9. When in doubt, ask central program finance BEFORE reporting the number. Interpretation "
     "rulings are appended to the full Guiding Principles document.", None),
]
for i, (text, font) in enumerate(gp, start=1):
    c = ws.cell(row=i, column=1, value=text)
    c.font = font or Font(size=11)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[i].height = 45 if i > 2 else 20
ws.column_dimensions["A"].width = 130

# ---------------------------------------------------------------- save

OUT = "India_Labor_Arbitrage_Tracker.xlsx"
wb.save(OUT)
print(f"Wrote {OUT}")
print(f"Org tab rows: {len(ORG_ROWS)} (last row {ORG_ROWS[-1][0]}); months C..{MONTH_COLS[-1]}")
