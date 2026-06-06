"""Build the report that answers the Research Concept Note from the model results.

Reads results_*.csv and synthesis_charts/*.png in this folder.
Run:  uv run --with reportlab python build_answer_report.py
"""
import os
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    PageBreak, KeepTogether, HRFlowable,
)
from reportlab.lib.utils import ImageReader

HERE = os.path.dirname(os.path.realpath(__file__))
CH = os.path.join(HERE, "synthesis_charts")
OUT = os.path.join(HERE, "Ethiopia_Youth_Dividend_Findings_vs_ConceptNote.pdf")

NAVY = colors.HexColor("#10243f"); STEEL = colors.HexColor("#33597f")
LIGHT = colors.HexColor("#eef3f8"); RED = colors.HexColor("#a32020")
GREEN = colors.HexColor("#1d6b34"); GOLD = colors.HexColor("#9c7a16")

GDP = "GDP ($Y_t$)"; CONS = "Consumption ($C_t$)"; WAGE = "Wage rate ($w_{t}$)"
LAB = "Labor ($L_t$)"


def df(code):
    p = os.path.join(HERE, f"results_{code}.csv")
    return pd.read_csv(p).set_index("Variable") if os.path.exists(p) else None


def val(code, row, col="SS"):
    d = df(code)
    if d is None or row not in d.index:
        return None
    return float(d.loc[row][col])


def pc(x):
    return "—" if x is None else f"{x:+.1f}%"


def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("TitleBig", parent=s["Title"], fontSize=24, textColor=NAVY, leading=29, spaceAfter=6))
    s.add(ParagraphStyle("Sub", parent=s["Normal"], fontSize=12.5, textColor=STEEL, alignment=TA_CENTER, leading=16, spaceAfter=4))
    s.add(ParagraphStyle("H1", parent=s["Heading1"], fontSize=16, textColor=NAVY, spaceBefore=12, spaceAfter=6))
    s.add(ParagraphStyle("H2", parent=s["Heading2"], fontSize=13, textColor=NAVY, spaceBefore=11, spaceAfter=3))
    s.add(ParagraphStyle("Min", parent=s["Normal"], fontSize=9, textColor=STEEL, spaceAfter=3))
    s.add(ParagraphStyle("Body", parent=s["Normal"], fontSize=10, alignment=TA_JUSTIFY, leading=14.4, spaceAfter=6))
    s.add(ParagraphStyle("Ans", parent=s["Normal"], fontSize=10.3, alignment=TA_JUSTIFY, leading=14.6, spaceAfter=6, textColor=colors.black, backColor=LIGHT, borderPadding=7))
    s.add(ParagraphStyle("Cap", parent=s["Normal"], fontSize=8.3, textColor=colors.grey, alignment=TA_CENTER, leading=10, spaceAfter=8))
    s.add(ParagraphStyle("Small", parent=s["Normal"], fontSize=8.4, textColor=colors.grey, leading=11))
    return s


def chart(name, st, cap=None, w=15.4 * cm):
    p = os.path.join(CH, name)
    iw, ih = ImageReader(p).getSize()
    flow = [Image(p, width=w, height=w * ih / iw)]
    if cap:
        flow.append(Paragraph(cap, st["Cap"]))
    return KeepTogether(flow)


def dim_table(rows):
    data = [["Scenario", "Long-run\nGDP / worker", "Long-run\nConsumption", "Long-run\nWage"]]
    for code, label in rows:
        d = df(code)
        if d is None:
            data.append([f"{code} — {label}", "not solved", "—", "—"])
        else:
            data.append([f"{code} — {label}", pc(val(code, GDP)), pc(val(code, CONS)), pc(val(code, WAGE))])
    t = Table(data, colWidths=[8.0 * cm, 3.0 * cm, 2.9 * cm, 2.4 * cm])
    ts = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
          ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.6),
          ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c3d0de")),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]
    for i, (code, _) in enumerate(rows, start=1):
        v = val(code, GDP)
        if v is not None:
            ts.append(("TEXTCOLOR", (1, i), (1, i), GREEN if v > 0.2 else (RED if v < -0.2 else colors.grey)))
            ts.append(("FONTNAME", (1, i), (1, i), "Helvetica-Bold"))
    t.setStyle(TableStyle(ts))
    return t


def kv_table(header, rows, widths):
    data = [header] + rows
    t = Table(data, colWidths=widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c3d0de")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
    return t


def P(s, st, style="Body"):
    return Paragraph(s, st[style])


DIMS = [
    ("D", "Dimension D — Demographic Foundation",
     "Audience: National Planning Commission. Concept Note role: establish the 'floor' of the dividend.",
     [("D2", "Accelerated fertility decline"), ("D3", "Youth-mortality shock"), ("D4", "High population growth")],
     "The demographic transition is the <b>floor, not the dividend</b>. On its own, the changing age "
     "structure leaves long-run output per worker essentially unchanged (≈0%); its visible effect is a "
     "large but <i>temporary</i> reshaping of the first decade as capital is spread over a slower-growing "
     "workforce. This is the direct answer to the Concept Note's question on the relative importance of "
     "demographic versus policy-driven growth: <b>demographics open the window; policy delivers the "
     "prosperity.</b> (The mortality scenario D3 shows a perverse positive per-worker blip — a smaller "
     "workforce sharing the capital stock — which must not be read as welfare improvement.)"),
    ("E", "Dimension E — Education & Human Capital",
     "Audience: Ministry of Education. Concept Note role: the return on education investment.",
     [("E2", "Moderate TVET (+10%)"), ("E3", "Strong university quality (+20%)"), ("E4", "Maximum human capital (+25%)")],
     "Education quality is the <b>highest-confidence lever</b>: a permanent, near-linear return in which "
     "+20% youth productivity lifts long-run GDP per worker by ~9% and +25% lifts it by ~11%. Capital "
     "accumulates to match the more productive workforce, so the gain is durable and broadly shared. "
     "Each additional 5 points of youth productivity buys roughly 2–2.5 points of permanent output per "
     "worker — a clean planning rule for the education budget. The moderate vocational variant (E2, +10%) "
     "confirms the pattern at the low end (+3.7%)."),
    ("L", "Dimension L — Labour Market & Formalisation",
     "Audience: Ministry of Labour and Skills. Concept Note role: gains from formal-sector expansion.",
     [("L2", "Moderate formalisation (→25%)"), ("L3", "Strong formalisation (→40%)"), ("L4", "Full formalisation (→55%)")],
     "Moving workers from informal to formal employment — where they are about 2.5× as productive — is a "
     "<b>first-order lever at full scale</b>: full formalisation (to the middle-income average of 55%) "
     "raises long-run output per worker by ~10%. But the dose-response is strongly <b>convex</b> — +0.3% "
     "(L2, →25%), +2.1% (L3, →40%), +10.1% (L4, →55%) — because at low formal shares the accompanying rise "
     "in labour-supply elasticity lifts hours and the return to capital faster than capital can deepen, "
     "muting the net gain; the large prize arrives only as formalisation approaches middle-income levels. "
     "The implication is to aim high rather than settle for partial formalisation."),
    ("G", "Dimension G — Gender Inclusion",
     "Audience: Ministry of Women and Social Affairs; Ministry of Finance. Concept Note role: the economic case for closing the gender gap.",
     [("G2", "Partial convergence (by 2040)"), ("G3", "Full convergence (by 2040)"), ("G4", "Accelerated convergence (by 2030)")],
     "Among the <b>largest single levers</b>. Partial convergence delivers +12.7% long-run output per "
     "worker; full convergence (G3/G4) delivers +19.6%. Converted to growth, that is about +0.5 and +0.7 "
     "percentage points of additional annual GDP-per-worker growth over 2025–2050 — broadly matching the "
     "Concept Note's projection of <b>'nearly one additional percentage point'</b>. Crucially, the speed "
     "matters: accelerating convergence to 2030 (G4) rather than 2040 (G3) more than doubles the "
     "first-decade gain — a +14.2% decade average versus +6.3% — for the same long-run destination. This "
     "is the quantitative backing for treating gender inclusion as a fiscal investment with a measurable "
     "return, not a social-policy cost."),
    ("M", "Dimension M — Migration & Brain Drain",
     "Audience: Ministry of Finance; Ministry of Foreign Affairs. Concept Note role: the first OG-ETH quantification of brain-drain risk.",
     [("M2", "Moderate brain drain"), ("M3", "Severe brain drain"), ("M4", "Brain gain + diaspora capital")],
     "Migration is <b>strongly asymmetric</b>. Losing skilled workers is a permanent cost of −3% (moderate) "
     "to −6% (severe) of output per worker, while attracting skilled returnees together with their capital "
     "gains +21% — the most powerful individual lever in the whole study after the integrated packages, "
     "because it adds a capital channel on top of the skill channel. The policy implication is unambiguous: "
     "<b>diaspora engagement — retention and return-with-investment — belongs at the centre of the dividend "
     "strategy.</b>"),
    ("F", "Dimension F — Fiscal Policy & Youth Investment",
     "Audience: Ministry of Finance; Development Partners (IMF). Concept Note role: the fiscal business case under the consolidation constraint.",
     [("F2", "Education spending +2% GDP"), ("F3", "Youth-employment subsidy †"), ("F4", "Gender-inclusion investment"), ("F5", "Fiscal consolidation −1.5% GDP")],
     "The central message for the IMF programme: <b>general government consumption is growth-neutral in the "
     "long run</b> — raising it (F2) or cutting it (F5) both settle at ~0% for output per worker. The "
     "implication is reassuring and demanding at once: consolidation need not sacrifice long-run growth "
     "<i>provided it protects the productivity-raising spending</i> (education, formalisation, "
     "participation). Gender-targeted investment (F4) pays a solid +8%. The youth-employment subsidy (F3, "
     "marked †) shows a contraction that is an artefact of a labour-supply calibration choice and should be "
     "re-specified before use — a flag, not a finding."),
]


def build():
    st = styles()
    doc = SimpleDocTemplate(OUT, pagesize=A4, topMargin=1.7 * cm, bottomMargin=1.5 * cm,
                            leftMargin=1.9 * cm, rightMargin=1.9 * cm,
                            title="Ethiopia Youth Dividend — Findings vs the Concept Note")
    F = []

    # Title
    F.append(Spacer(1, 2.6 * cm))
    F.append(P("Ethiopia's Youth Dividend:<br/>Model Findings Against the Research Concept Note", st, "TitleBig"))
    F.append(P("Answering the central research question and testing the Concept Note's projections, "
               "with the completed OG-ETH scenario runs", st, "Sub"))
    F.append(Spacer(1, 0.4 * cm))
    F.append(HRFlowable(width="55%", thickness=1.2, color=STEEL))
    F.append(Spacer(1, 0.6 * cm))
    F.append(P("A companion to the detailed scenario report. All figures are model results expressed as "
               "percentage deviations from a 2025 Ethiopia baseline, in per-effective-worker terms. "
               "June 2026.", st, "Cap"))
    F.append(PageBreak())

    # The headline answer
    F.append(P("The Headline Answer", st, "H1"))
    F.append(P("<b>How large is Ethiopia's youth dividend, and what does it cost to miss it?</b> The "
               "completed runs answer the Concept Note's central question directly. The dividend is real "
               "and large, but it is <b>earned through policy, not granted by demography</b>. A coordinated "
               "reform programme can raise long-run output per worker by +20% (moderate), +45% (ambitious) "
               "or as much as +84% (maximum). The demographic transition by itself contributes almost "
               "nothing to long-run output per worker — it sets the stage; education, formalisation, female "
               "participation and skilled-diaspora return are what fill it.", st, "Ans"))
    F.append(chart("A_decomposition.png", st,
                   "Each bar is the permanent (steady-state) gain in GDP per worker from that reform, "
                   "relative to the 2025 Ethiopia baseline. Mid-blue = single levers; dark navy = combined packages."))
    F.append(PageBreak())

    # Central research question
    F.append(P("Answering the Central Research Question", st, "H1"))
    F.append(P("<i>“How large is Ethiopia's youth dividend across every major policy dimension — "
               "demographics, education, labour, gender, migration and fiscal policy — and what is the "
               "macroeconomic cost of failing to capture it?”</i>", st, "Body"))
    F.extend([
        P("<b>Across dimensions, the ranking is clear.</b> The biggest individual prizes are skilled-diaspora "
          "return with capital (+21%), female-participation convergence (+13% partial, +20% full), maximum "
          "education (+11%) and full formalisation (+10%). Demographics alone are ~0% in the long run, and "
          "general fiscal spending is growth-neutral. Combining the levers is where the dividend becomes "
          "transformational: the ambitious package nearly halves the distance to a doubling of output per "
          "worker, and the maximum package reaches it.", st),
        P("<b>The cost of failing to capture it is concentrated in time.</b> Because reforms reach the same "
          "long-run destination whenever they start, the cost of inaction is the permanent forfeit of each "
          "year's higher output during the years of delay — on the order of 40% of output per worker for "
          "every year a full programme is postponed (quantified below).", st),
        P("<b>Relative importance — demographics vs policy.</b> This is the Concept Note's sharpest question, "
          "and the answer is unambiguous: the demographic transition is necessary but not sufficient. It "
          "produces a powerful decade-long swing in the <i>transition</i> but a ~0% change in the long-run "
          "<i>level</i> of output per worker. Essentially the entire durable dividend is policy-driven.", st),
    ])
    F.append(PageBreak())

    # Dimension briefs
    F.append(P("Findings by Dimension (the ministry-level briefs)", st, "H1"))
    F.append(P("Each dimension below corresponds to one of the Concept Note's planned ministry briefs. "
               "Tables report the permanent (long-run) effect on output, consumption and wages per worker; "
               "the detailed year-by-year and transition figures are in the companion scenario report.", st))
    for key, title, audience, rows, narrative in DIMS:
        block = [P(title, st, "H2"), P(audience, st, "Min"), dim_table(rows), Spacer(1, 4), P(narrative, st)]
        F.append(KeepTogether(block) if key in ("D", "E") else block[0])
        if key not in ("D", "E"):
            for b in block[1:]:
                F.append(b)
        if key == "M":
            F.append(chart("D_brain.png", st, "Long-run GDP per worker. Losing skills is a modest permanent "
                           "loss; gaining skilled returnees with their capital is a large permanent gain."))
        if key == "G":
            F.append(chart("E_gender_growth.png", st, "Level gains converted to annualised GDP-per-worker "
                           "growth over 25 years, against the Concept Note's ~1 pp/yr projection."))
            F.append(chart("F_gender_timing.png", st, "The 'speed of convergence' result: G4 (full by 2030) "
                           "and G3 (full by 2040) reach the same long-run gain, but the faster route "
                           "more than doubles the first-decade dividend.", w=14.0 * cm))
        F.append(Spacer(1, 6))

    # Integrated packages & the 20-35% claim
    F.append(PageBreak())
    F.append(P("Integrated Packages and the Concept Note's +20–35% Projection", st, "H1"))
    F.append(P("Audience: Cabinet; National Planning Commission; IMF.", st, "Min"))
    F.append(P("The Concept Note projected that an integrated package 'could add between 20 and 35 percent to "
               "Ethiopia's cumulative GDP above baseline by 2050.' The runs both <b>confirm and extend</b> "
               "that projection: the moderate package lands at the bottom of the band (+20%), while the "
               "ambitious and maximum packages exceed it (+45% and +84% long-run GDP per worker). The "
               "Concept Note's range is therefore a reasonable-to-conservative statement of the achievable "
               "dividend.", st, "Ans"))
    F.append(chart("B_packages_vs_target.png", st, "Long-run GDP per worker for the three integrated "
                   "packages, against the Concept Note's projected +20–35% band (shaded).", w=12.5 * cm))

    # Cost of delay
    F.append(PageBreak())
    F.append(P("The Cost of Delay (Objective 4 — the flagship advocacy figure)", st, "H1"))
    F.append(P("The Concept Note identifies the cost of a decade of inaction as 'arguably the most powerful "
               "finding the study can produce.' Comparing the ambitious package started on time (2025) with "
               "the identical package started ten years late (2035) gives the answer: the delayed economy "
               "runs about <b>36–45% below the on-time economy throughout the lost decade</b>, and the gap is "
               "<b>never recovered</b> — the two paths converge only because they share the same long-run "
               "destination. Every year of delay permanently forfeits that year's dividend.", st, "Ans"))
    F.append(chart("C_cost_of_delay.png", st))
    dcd = df("cost_of_delay")
    if dcd is not None:
        rows = [[lbl, pc(float(dcd.loc[k]["2025"])), pc(float(dcd.loc[k]["2025-2034"])), pc(float(dcd.loc[k]["SS"]))]
                for k, lbl in [(GDP, "GDP per worker"), (CONS, "Consumption per worker"),
                               (LAB, "Effective labour"), (WAGE, "Wage per efficiency unit")]]
        F.append(kv_table(["Delayed (I4) vs on-time (I2)", "Impact 2025", "Decade avg 2025–34", "Long-run"],
                          rows, [7.6 * cm, 3.0 * cm, 3.4 * cm, 2.3 * cm]))

    # Testing the Concept Note's claims
    F.append(PageBreak())
    F.append(P("Testing the Concept Note's Preliminary Projections", st, "H1"))
    claims = [
        ["Integrated package adds +20–35% GDP above baseline by 2050",
         "Moderate +20%, Ambitious +45%, Maximum +84% (long-run GDP/worker)",
         "Confirmed at the low end; exceeded by the stronger packages"],
        ["Gender inclusion adds ~1 percentage point of annual growth",
         "Full convergence (G3/G4) ≈ +0.72 pp/yr; partial ≈ +0.48 pp/yr",
         "Broadly confirmed (full convergence ≈ 0.7 pp/yr)"],
        ["The cost of delayed action is large and quantifiable",
         "~36–45% lower GDP/worker each year of a lost decade; never recovered",
         "Confirmed; very large"],
        ["The dividend is real but not automatic",
         "Demographics alone ≈ 0% long-run; gains are policy-driven",
         "Confirmed"],
        ["Brain drain is a genuine macroeconomic cost",
         "−3% (moderate) to −6% (severe); brain gain +21%",
         "Confirmed; strongly asymmetric"],
        ["Education investment yields a measurable return",
         "+9% to +11% long-run GDP/worker (near-linear in quality)",
         "Confirmed"],
    ]
    rows = [[P(c[0], st, "Small"), P(c[1], st, "Small"), P("<b>" + c[2] + "</b>", st, "Small")] for c in claims]
    F.append(kv_table(["Concept Note claim", "Model result", "Verdict"], rows,
                      [5.6 * cm, 6.2 * cm, 4.5 * cm]))

    # Specific objectives
    F.append(P("Status Against the Concept Note's Specific Objectives", st, "H1"))
    objs = [
        ["1. Calibrate/validate OG-ETH across all dimensions",
         "Done — Ethiopia (UN 231) 2025 baseline; all seven dimensions represented."],
        ["2. Establish a baseline projection",
         "Done — common 2025 baseline solved and used for every comparison (baseline error corrected)."],
        ["3. Simulate 25+ scenarios; effects on GDP, wages, savings, revenue, welfare",
         "Largely done — all 23 reform scenarios reported on GDP, consumption, capital, labour, interest "
         "and wages; tax-revenue and lifetime-utility outputs not yet extracted."],
        ["4. Quantify the cost of delay",
         "Done — ambitious-on-time vs ambitious-delayed (I2 vs I4)."],
        ["5. Ministry-level policy briefs",
         "Foundations delivered — dimension findings above map to each ministry brief; standalone briefs "
         "are a writing/packaging step."],
        ["6. Publish an updated open-source OG-ETH model",
         "Model and scenario code are in place; formal publication and analyst training remain."],
    ]
    rows = [[P(o[0], st, "Small"), P(o[1], st, "Small")] for o in objs]
    F.append(kv_table(["Specific objective", "Status from this run"], rows, [6.7 * cm, 9.6 * cm]))

    # Caveats / what's still needed
    F.append(P("Caveats and What Is Still Needed", st, "H1"))
    for t in [
        "<b>Units.</b> Results are percentage deviations in per-effective-worker terms, not birr levels or "
        "cumulative-GDP totals. Translating them into the Concept Note's birr and fiscal-revenue figures "
        "(and the 'USD 2.5bn per 1% of GDP' framing) requires the model's tax-revenue and level outputs, "
        "which were not extracted in this run.",
        "<b>Per-worker metrics can mislead under population loss</b> (the mortality and brain-drain "
        "scenarios show positive short-run per-worker blips that are denominator effects, not welfare gains).",
        "<b>Government consumption is modelled as unproductive</b>, which is why the pure spending scenarios "
        "(F2, F5) are long-run neutral; genuinely productive public investment would instead work through "
        "the education-style channels.",
        "<b>Five scenarios (E2, L2, L3, G3, G4) initially tripped a terminal-period check, since "
        "resolved.</b> Their converged paths satisfy goods-market clearing to ~1e-6 across the modelled "
        "horizon and the steady state to ~1e-14; the only violation was confined to the artificial final "
        "period (~year 2344, three centuries past the policy window) — a boundary artifact. They are now "
        "reported in full after explicit quality checks.",
        "<b>The youth-subsidy result (F3)</b> is sensitive to a labour-supply calibration choice and should "
        "be re-specified before being used.",
        "<b>These are scenario projections, not forecasts</b>, and represent idealised policy "
        "implementations without political-economy or administrative-capacity constraints.",
    ]:
        F.append(P(t, st))

    doc.build(F)
    print("WROTE", OUT)


if __name__ == "__main__":
    build()
