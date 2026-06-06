"""Build the Youth Dividend policy-interpretation PDF.

Reads the corrected results_*.csv tables and plots_*/ images in this folder and
assembles a professional, non-technical macroeconomic interpretation document.

Run:  uv run --with reportlab python build_youth_pdf.py
Output:  Ethiopia_Youth_Dividend_Policy_Analysis.pdf
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

HERE = os.path.dirname(os.path.realpath(__file__))
OUT = os.path.join(HERE, "Ethiopia_Youth_Dividend_Policy_Analysis.pdf")

ROWS = [
    ("GDP ($Y_t$)", "Output per worker (GDP)"),
    ("Consumption ($C_t$)", "Consumption per worker"),
    ("Capital Stock ($K_t$)", "Capital per worker"),
    ("Labor ($L_t$)", "Effective labour supply"),
    ("Real interest rate ($r_t$)", "Real interest rate"),
    ("Wage rate ($w_{t}$)", "Wage per efficiency unit"),
]

NAVY = colors.HexColor("#10243f")
STEEL = colors.HexColor("#33597f")
LIGHT = colors.HexColor("#eef3f8")
RED = colors.HexColor("#a32020")
GREEN = colors.HexColor("#1d6b34")

# ---------------------------------------------------------------------------
# Scenario catalogue (shock + source straight from the run script).
# ---------------------------------------------------------------------------
DIMENSIONS = [
    ("Dimension 1 — Demographic Foundation",
     "How the population transition itself — fertility and mortality variants — "
     "reshapes the economy.", ["D2", "D3", "D4"]),
    ("Dimension 2 — Education & Human Capital",
     "Raising the productivity of young workers through better schooling and "
     "skills.", ["E2", "E3", "E4"]),
    ("Dimension 3 — Labour Market & Formalisation",
     "Moving workers from low-productivity informal work into formal employment.",
     ["L2", "L3", "L4"]),
    ("Dimension 4 — Gender Inclusion (Female Labour-Force Participation)",
     "Closing the gap between female and male participation in paid work.",
     ["G2", "G3", "G4"]),
    ("Dimension 5 — Migration & Brain Drain",
     "The loss or gain of high-skill workers, and the capital the diaspora "
     "brings.", ["M2", "M3", "M4"]),
    ("Dimension 6 — Fiscal Policy & Youth Investment",
     "Government spending, subsidies and transfers aimed at the dividend.",
     ["F2", "F3", "F4", "F5"]),
    ("Dimension 7 — Integrated Policy Packages",
     "Combining the individual reforms — and the cost of delaying them.",
     ["I1", "I2", "I3", "I4"]),
]

META = {
    "D2": dict(title="D2 — Accelerated Fertility Decline",
               shock="Fertility falls 25% faster than the medium path (total fertility rate reaches ~2.5 by 2035 instead of 2045), modelled as a fully consistent recompute of Ethiopia's population structure.",
               source="UN WPP 2024 low-fertility variant; ILO 2023"),
    "D3": dict(title="D3 — High Youth-Mortality Shock",
               shock="A conflict or health crisis raises mortality of young adults (ages 20–35) by 15% in the early periods of the horizon.",
               source="World Bank Ethiopia Conflict Impact Report 2023"),
    "D4": dict(title="D4 — High-Fertility Upper Bound",
               shock="Fertility runs 20% above the medium path (UN high variant); population exceeds 200 million by 2050.",
               source="UN WPP 2024 high-fertility variant"),
    "E2": dict(title="E2 — Moderate TVET Expansion",
               shock="Young-worker productivity raised +10% (ages ≤35, tapering to zero by 55), representing improved technical and vocational training.",
               source="World Bank Ethiopia Education Report 2023; ILO 2023"),
    "E3": dict(title="E3 — Strong University-Quality Improvement",
               shock="Young-worker productivity raised +20% (ages ≤35, tapering to 55).",
               source="World Bank Ethiopia Education Report 2023"),
    "E4": dict(title="E4 — Combined TVET + University (Maximum Human Capital)",
               shock="Young-worker productivity raised +25% (ages ≤35, tapering to 55) — the full combined education reform.",
               source="World Bank Ethiopia Education Report 2023; ILO 2023"),
    "L2": dict(title="L2 — Moderate Formalisation (13% → 25% formal by 2035)",
               shock="Formal workers earn ~2.5× informal. Working-age productivity +15.1%; labour-supply elasticity (Frisch) +0.05.",
               source="ILO Ethiopia Labour Market Profile 2023"),
    "L3": dict(title="L3 — Strong Formalisation (13% → 40% formal by 2035)",
               shock="Working-age productivity +33.9%; labour-supply elasticity +0.10.",
               source="ILO Ethiopia Labour Market Profile 2023"),
    "L4": dict(title="L4 — Full Formalisation (13% → 55%, middle-income average)",
               shock="Working-age productivity +52.7%; labour-supply elasticity +0.15.",
               source="ILO Ethiopia Labour Market Profile 2023; World Bank 2023"),
    "G2": dict(title="G2 — Partial FLFP Convergence by 2040 (halfway to male levels)",
               shock="Female participation closes half the gap with men, modelled as a uniform +15% rise in effective labour supply.",
               source="ILO Ethiopia Labour Market Profile 2023"),
    "G3": dict(title="G3 — Full FLFP Convergence by 2040",
               shock="Female participation fully converges to male levels: +30% effective labour supply, phased in over 15 years (2025–2040).",
               source="ILO Ethiopia Labour Market Profile 2023"),
    "G4": dict(title="G4 — Accelerated Full FLFP Convergence by 2030",
               shock="Same +30% long-run gain as G3 but phased in over just 5 years (2025–2030) — the 'speed of convergence' counterfactual.",
               source="ILO Ethiopia Labour Market Profile 2023"),
    "M2": dict(title="M2 — Moderate Brain Drain (graduate emigration doubles by 2030)",
               shock="The two highest-skill groups among working-age adults lose 20% of their productivity to emigration.",
               source="World Bank Ethiopia Diaspora Report 2024; ILO 2023"),
    "M3": dict(title="M3 — Severe Brain Drain (20% of graduates leave per decade)",
               shock="The two highest-skill groups among working-age adults lose 35% of their productivity to emigration.",
               source="World Bank Ethiopia Diaspora Report 2024"),
    "M4": dict(title="M4 — Brain Gain (net skilled-diaspora return)",
               shock="High-skill productivity rises +25% as skilled diaspora return, and diaspora capital raises the foreign-financed share of investment (+10 percentage points).",
               source="World Bank Ethiopia Diaspora Report 2024"),
    "F2": dict(title="F2 — Education-Investment Surge (+2% of GDP spending)",
               shock="Government spending rises by 2 percentage points of GDP.",
               source="Ethiopian NPC Ten-Year Development Plan 2021–2030"),
    "F3": dict(title="F3 — Youth-Employment Subsidy",
               shock="A wage subsidy for formal youth hiring: productivity +10% for ages 20–35 and labour-supply elasticity +0.10.",
               source="World Bank Ethiopia Economic Update 2023"),
    "F4": dict(title="F4 — Gender-Inclusion Investment",
               shock="Targeted transfers +1% of GDP to enable female participation, with a uniform +10% rise in effective labour supply.",
               source="Ministry of Women and Social Affairs Ethiopia 2024"),
    "F5": dict(title="F5 — IMF Fiscal-Consolidation Constraint (−1.5% of GDP)",
               shock="Government spending is cut by 1.5 percentage points of GDP under a consolidation programme.",
               source="IMF Ethiopia Article IV Consultation 2024"),
    "I1": dict(title="I1 — Moderate Integrated Package",
               shock="TVET (E2) + moderate formalisation (L2) + partial FLFP (G2) + education spending (F2), composed together: Frisch +0.05, spending +2% of GDP.",
               source="Ethiopian NPC Ten-Year Development Plan 2021–2030"),
    "I2": dict(title="I2 — Ambitious Integrated Package",
               shock="University quality (E3) + strong formalisation (L3) + full FLFP by 2040 (G3) + education spending (F2): Frisch +0.10, spending +2% of GDP.",
               source="Ethiopian NPC Ten-Year Development Plan 2021–2030"),
    "I3": dict(title="I3 — Maximum Dividend",
               shock="Maximum education (E4) + full formalisation (L4) + accelerated FLFP (G4) + brain gain (M4): Frisch +0.15 and diaspora capital +10 pp. The ceiling of the dividend.",
               source="Ethiopian NPC Ten-Year Development Plan 2021–2030"),
    "I4": dict(title="I4 — Delayed Action (the ambitious package, started in 2035)",
               shock="Identical to the Ambitious package (I2), but the productivity reforms begin in 2035 instead of 2025 — the baseline holds for the first decade. Used to measure the cost of a ten-year delay.",
               source="DeBacker & Evans 2023; Ethiopian NPC 2021"),
}

FAILED = set()  # all five initially-non-converged scenarios now finalized
FAIL_NOTE = {}

# ---------------------------------------------------------------------------
# Per-scenario interpretation (macroeconomist prose) and one policy line each.
# ---------------------------------------------------------------------------
INTERP = {
    "D2": (
        "A faster fertility decline reshapes the transition far more than the long run. Through the first decade, output per effective worker rises about 5–7%, consumption per worker jumps 20–33%, and the capital–labour ratio deepens markedly — capital and wages per worker climb ~21% while the return to capital falls ~17% — as a slower-growing workforce inherits the existing capital stock. These are intensive-margin gains: fewer dependents and slower labour-force growth raise capital per worker. By the steady state the effects nearly vanish (GDP +0.1%): once the population stabilises, per-worker output is only marginally higher under lower fertility.",
        "Policy: The fertility transition is a one-off, decade-long tailwind to living standards, not a permanent growth engine. Capturing it requires jobs and capital for the temporarily larger working-age share — the window closes as the population matures.",
    ),
    "D3": (
        "On paper this crisis 'raises' per-worker GDP (+7%) and consumption (+32%) in the near term — but that is the arithmetic of a shrunken workforce sharing an unchanged capital stock, not an improvement in welfare. Aggregate output and the population are smaller; the surviving workers each temporarily command more capital. The long-run per-worker effect is again negligible. This scenario is above all a methodological caution: intensive (per-worker) metrics can move perversely under population loss.",
        "Policy: Never read per-worker GDP gains from a mortality or out-migration shock as good news. The real losses — lost lives, lower aggregate output, fewer future workers — are invisible to per-worker ratios. Protecting young-adult health preserves the size and momentum of the dividend.",
    ),
    "D4": (
        "The high-fertility path mirrors the accelerated-decline case in the short run — the transition is dominated by the same capital-per-worker mechanics — but leaves long-run output per worker marginally lower (−0.04%): faster labour-force growth dilutes capital per worker. The larger population (>200 million by 2050) raises the scale of the economy and the absolute number of workers, which this per-worker lens does not reward, while also raising the investment bill needed to equip each new worker.",
        "Policy: Faster population growth is not free — it raises the capital-deepening required to keep output per worker rising. Whether higher fertility helps or hurts depends entirely on whether job creation and investment keep pace with the labour force.",
    ),
    "E2": (
        "The moderate vocational-training reform delivers a clean, permanent dividend of about +3.7% long-run output per worker from a +10% rise in young-worker productivity — slotting in neatly below the stronger university (E3, +8.9%) and combined (E4, +11.2%) reforms and confirming the near-linear education dose-response. Consumption and effective labour rise ~4–5%, capital follows, and factor prices barely move.",
        "Policy: Even modest, well-targeted skills investment pays a durable return, and the education lever scales predictably with reform intensity — which makes it straightforward to phase against the budget.",
    ),
    "E3": (
        "This is a genuine, permanent dividend. Raising young-worker productivity by 20% lifts long-run output, consumption and capital per worker by ~9%, with effective labour up ~9%. Capital accumulates to match the more productive workforce, so the long-run return to capital and the capital–output ratio return to baseline and the wage per efficiency unit is roughly unchanged — but each worker now embodies more efficiency units, so labour income per worker rises with productivity. Consumption is strongly front-loaded (+37% on impact) as households borrow against higher expected lifetime income.",
        "Policy: Spending that actually raises worker productivity — quality schooling and skills — delivers durable gains in living standards, roughly one-for-one with the productivity improvement. This is the core of the youth dividend.",
    ),
    "E4": (
        "The strongest education reform raises long-run output and consumption per worker by ~11%, scaling near-linearly with the productivity gain (compare E3's ~9% at +20%). The near-linearity is useful for planners: each additional 5 points of youth productivity buys roughly 2–2.5 points of permanent GDP per worker. Capital and effective labour both rise ~11% and factor prices are restored in the long run.",
        "Policy: Education quality is the highest-confidence lever in this analysis — predictable, permanent and scalable, and the moderate variant (E2) confirms the pattern at the low end (≈ +3.7%).",
    ),
    "L2": (
        "Moderate formalisation (to a 25% formal share) raises long-run output per worker only modestly (+0.3%), despite a +1.9% decade-average gain. The reason is instructive: the reform lifts effective labour faster than capital can deepen (capital settles ~1.3% lower per worker), so the return to capital rises and the wage per efficiency unit eases — the formalisation productivity gain is partly offset by the accompanying rise in labour-supply elasticity.",
        "Policy: Early-stage formalisation is worthwhile but front-loaded; the lever is convex, so the large returns arrive only as the formal share approaches middle-income levels. Treat partial formalisation as a stepping-stone, not the destination.",
    ),
    "L3": (
        "Strong formalisation (to a 40% formal share) lifts long-run output per worker by +2.1% (decade average +5.1%) — again a labour-led expansion in which effective labour rises ~6.6% while capital stays roughly flat, pushing the return to capital up and the wage per efficiency unit down. The dividend is real but, as in L2, tempered by the labour-supply channel.",
        "Policy: The formalisation dose-response is strongly convex — +0.3% (L2), +2.1% (L3), +10.1% (L4) — so the prize is concentrated at high formal-employment shares. Aim for the middle-income benchmark rather than a halfway house.",
    ),
    "L4": (
        "Moving the workforce from informal to formal employment — where workers are about 2.5× as productive — delivers a permanent ~+10% gain in output and consumption per worker, comparable to the strongest education reform. The mechanism is the same: higher effective productivity, matched over time by capital accumulation, with factor prices roughly restored. Effective labour ends ~10% higher and the long-run wage per efficiency unit is essentially flat.",
        "Policy: Formalisation is a first-order growth lever, on par with education. The intermediate steps (L2, L3) did not converge this run, but their effects are bounded below L4 and are captured inside the integrated packages — the dose-response runs from the baseline up to ~+10% at full formalisation.",
    ),
    "G2": (
        "Closing half the gender gap in participation — a uniform 15% rise in effective labour supply — scales the whole economy up: long-run output, consumption, capital and labour all rise ~12.7% per worker, with the interest rate and the wage per efficiency unit returning exactly to baseline. This clean balanced-growth result reflects a uniform, labour-augmenting expansion in which capital scales proportionally and relative prices are unchanged.",
        "Policy: Raising female participation is among the largest single levers available — partial convergence alone yields a double-digit permanent gain, and full convergence (G3/G4) reaches ~+20% (below).",
    ),
    "G3": (
        "Full convergence of female participation by 2040 raises long-run output per worker by +19.6% — among the largest single-lever gains in the study. It is a labour-led expansion: effective labour rises ~25% and capital ~15%, so output rises ~20% with a modestly higher return to capital and a slightly lower wage per efficiency unit. Because the gain accrues as participation rises over the 15-year phase-in, the first-decade average is a more muted +6.3%.",
        "Policy: Bringing women fully into paid work is transformational for the level of output per worker. Since the gains build with participation, the timing of the reform matters as much as its ambition — which is precisely the lesson of G4.",
    ),
    "G4": (
        "Identical in its long-run destination to G3 (+19.6%), but reached a decade sooner: the accelerated phase-in (full convergence by 2030) more than doubles the first-decade dividend — a +14.2% decade average versus G3's +6.3%, and +20% output per worker by 2030 versus +7%. This isolates the value of acting faster toward the same goal — the 'speed of convergence'.",
        "Policy: When the destination is fixed, speed is almost free dividend. Accelerating female-participation convergence by ten years pulls the entire gain forward by a decade at no long-run cost — a powerful argument for early, determined action.",
    ),
    "M2": (
        "The emigration of high-skill workers shows the now-familiar positive intensive-margin blip on impact (+4% GDP per worker, as the remaining workforce shares the capital stock), but the honest long-run signal is a permanent loss: output, consumption and capital per worker settle ~3.4% below baseline. The economy is permanently less productive without its most skilled workers.",
        "Policy: Skilled emigration is a slow, compounding drain on growth. The flattering short-run per-worker statistics disguise a genuine long-run cost.",
    ),
    "M3": (
        "A larger skilled exodus deepens the permanent loss to ~6% of output per worker — roughly proportional to the share of high-skill productivity lost (the M2→M3 dose-response is close to linear).",
        "Policy: The cost of losing skilled workers scales with the size of the outflow. Retention and circular-migration policies have measurable, compounding long-run payoffs.",
    ),
    "M4": (
        "The standout result. Combining the return of skilled diaspora with the capital they bring delivers a large permanent dividend: output per worker +21%, capital per worker +34%, consumption +12% and wages +15%, alongside a persistently lower return to capital (−15%) reflecting the inflow of foreign-financed capital. This exceeds education or formalisation alone because it adds a capital channel on top of the skill channel.",
        "Policy: Diaspora engagement — attracting skilled returnees and their investment — is exceptionally high-value, and the asymmetry is striking: losing skills costs 3–6% (M2/M3) while attracting skills plus capital gains ~21%. Diaspora policy belongs at the centre of the dividend strategy.",
    ),
    "F2": (
        "Modelled as a rise in (non-productive) government consumption, an 'education spending surge' has essentially no long-run effect on output, consumption or capital per worker — the steady-state response is zero. The short-run positive blip reflects transition dynamics, not a durable gain.",
        "Policy: This is a crucial caveat. Spending labelled 'education' pays a growth dividend only if it actually raises worker productivity (the channel captured by the E-scenarios). Budget increases that do not translate into measurable skills are, in this model, growth-neutral. Fund what raises productivity — and measure the productivity outcome, not the input.",
    ),
    "F3": (
        "This scenario shows a counterintuitive long-run contraction (~−11%). The driver is not the modest +10% productivity boost but the accompanying increase in the labour-supply elasticity (Frisch) without recalibrating the labour-disutility scale, which lowers equilibrium hours. The result is therefore highly sensitive to a modelling choice and should not be read as 'youth subsidies shrink the economy'.",
        "Policy: Treat F3 as a flag that the answer depends on how labour-supply behaviour is calibrated, not as a robust prediction. A youth wage subsidy that genuinely raises youth productivity and employment would be expected to help; we recommend re-specifying this scenario before drawing conclusions.",
    ),
    "F4": (
        "Targeted transfers that enable female participation, paired with a 10% economy-wide productivity gain, deliver a solid permanent ~+8% in output per worker and ~+11% in consumption. The productivity channel does the lifting (as in G2) while the transfers support the participation needed to realise it.",
        "Policy: Gender-inclusion spending pays off when it removes the constraints — childcare, safety, transport, transfers — that keep productive women out of paid work, i.e. when it raises effective labour supply rather than merely incomes.",
    ),
    "F5": (
        "Symmetrically to the spending surge, cutting (non-productive) government consumption by 1.5% of GDP is long-run neutral for output, consumption and capital per worker — the steady-state effect is zero. Consolidation of this kind does not, in this model, sacrifice long-run growth; its effects are transitional and distributional (felt through transfers and the timing of consumption), not through productive capacity.",
        "Policy: Consolidation framed as cutting unproductive consumption need not harm long-run growth — provided it protects the spending that does raise productivity. The growth risk lies in cutting productive investment, not consumption.",
    ),
    "I1": (
        "Bundling the moderate education, formalisation and participation reforms (plus education spending) compounds into a permanent ~+20% gain in output and consumption per worker — substantially more than any single moderate reform, because the productivity gains stack across the workforce. Effective labour rises ~20%, capital follows, and factor prices return to baseline.",
        "Policy: A coordinated 'moderate on every front' package roughly doubles the payoff of any one moderate reform. Coordination itself is valuable.",
    ),
    "I2": (
        "Scaling each lever to its strong setting delivers a permanent ~+45% rise in output per worker — the combined level effect of upgrading skills, formalising work and bringing women fully into the labour force. This is transformational: the difference between incremental progress and a structural break in living standards.",
        "Policy: Ambition compounds. The ambitious package is far more than the sum of cautious half-measures — stacking strong reforms across human capital, formality and participation is where the dividend becomes a development strategy.",
    ),
    "I3": (
        "The ceiling. Combining maximum education, full formalisation, accelerated female convergence and brain gain (with diaspora capital) roughly doubles long-run output per worker (+84%), with capital per worker more than doubling (+104%) thanks to the diaspora-capital inflow and — uniquely among the packages — a permanently higher wage per efficiency unit (+15%) and lower return to capital (−15%) as the economy becomes deeply capital-rich.",
        "Policy: This is the upper bound of what the youth dividend could deliver — a fundamentally larger, more productive, higher-wage economy. It is demanding (it assumes every reform succeeds at full strength and the diaspora returns with capital), but it defines the prize and the direction of travel.",
    ),
    "I4": (
        "Identical reforms, started a decade late. Because the destination is the same, the long run is identical to the Ambitious package (+45%). But the first decade is lost — and is actually worse than the baseline early on, because the package's labour-market parameter changes bite before the productivity gains arrive. The economy forgoes the entire 2025–2034 dividend.",
        "Policy: See the Cost of Delay below — the reforms are worth the same in the long run whenever they begin, but every year of delay permanently forfeits that year's dividend.",
    ),
}

COST_OF_DELAY_PROSE = (
    "Measured directly (the delayed package against the on-time package), a ten-year delay costs about 40% of output per worker for every year of the lost decade, and roughly half of effective labour. None of it is ever recovered — the two paths converge only because they share the same long-run destination. The 'cost of delay' is precisely the permanent forfeit of the first decade's higher output: a one-time but irreversible loss.",
    "Policy: This is the single clearest message in the analysis. Acting in 2025 rather than 2035 is the difference between capturing and losing an entire decade of ~40%-higher output per worker. Start now.",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("TitleBig", parent=s["Title"], fontSize=26,
                         textColor=NAVY, leading=30, spaceAfter=6))
    s.add(ParagraphStyle("SubTitle", parent=s["Normal"], fontSize=13,
                         textColor=STEEL, alignment=TA_CENTER, leading=17,
                         spaceAfter=4))
    s.add(ParagraphStyle("H1", parent=s["Heading1"], fontSize=17,
                         textColor=NAVY, spaceBefore=14, spaceAfter=6))
    s.add(ParagraphStyle("H2", parent=s["Heading2"], fontSize=13.5,
                         textColor=NAVY, spaceBefore=12, spaceAfter=4))
    s.add(ParagraphStyle("H3", parent=s["Heading3"], fontSize=11.5,
                         textColor=STEEL, spaceBefore=8, spaceAfter=3))
    s.add(ParagraphStyle("Body", parent=s["Normal"], fontSize=10,
                         alignment=TA_JUSTIFY, leading=14.5, spaceAfter=6))
    s.add(ParagraphStyle("Shock", parent=s["Normal"], fontSize=9.5,
                         leading=13, textColor=colors.black,
                         backColor=LIGHT, borderPadding=6, spaceAfter=6))
    s.add(ParagraphStyle("Policy", parent=s["Normal"], fontSize=9.7,
                         leading=13.5, textColor=NAVY, spaceAfter=6,
                         leftIndent=6, borderColor=STEEL))
    s.add(ParagraphStyle("Small", parent=s["Normal"], fontSize=8.3,
                         textColor=colors.grey, leading=11))
    s.add(ParagraphStyle("Cap", parent=s["Normal"], fontSize=8.3,
                         textColor=colors.grey, alignment=TA_CENTER,
                         leading=10, spaceAfter=8))
    return s


def read_df(code):
    p = os.path.join(HERE, f"results_{code}.csv")
    if not os.path.exists(p):
        return None
    return pd.read_csv(p).set_index("Variable")


def pct(x):
    try:
        v = float(x)
    except Exception:
        return str(x)
    return f"{v:+.1f}%"


def result_table(df, st):
    data = [["Indicator (% deviation from baseline)", "Impact\n2025",
             "Decade avg\n2025–34", "Long-run\n(steady state)"]]
    for key, label in ROWS:
        if key not in df.index:
            continue
        r = df.loc[key]
        data.append([label, pct(r["2025"]), pct(r["2025-2034"]), pct(r["SS"])])
    t = Table(data, colWidths=[7.2 * cm, 2.7 * cm, 2.9 * cm, 3.1 * cm])
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.6),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c3d0de")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # colour the long-run column by sign
    for i, (key, _) in enumerate([r for r in ROWS if r[0] in df.index], start=1):
        try:
            v = float(df.loc[key]["SS"])
        except Exception:
            continue
        if key.startswith("GDP") or key.startswith("Consumption"):
            ts.append(("TEXTCOLOR", (3, i), (3, i), GREEN if v > 0.2 else (RED if v < -0.2 else colors.black)))
            ts.append(("FONTNAME", (3, i), (3, i), "Helvetica-Bold"))
    t.setStyle(TableStyle(ts))
    return t


def fitted_image(path, max_w=13.2 * cm):
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(path).getSize()
    w = max_w
    h = w * ih / iw
    return Image(path, width=w, height=h)


def scenario_flow(code, st):
    flow = []
    m = META[code]
    flow.append(Paragraph(m["title"], st["H2"]))
    flow.append(Paragraph(f"<b>Shock applied.</b> {m['shock']}", st["Shock"]))
    if code in FAILED:
        flow.append(Paragraph(f"<b>Note.</b> {FAIL_NOTE[code]}", st["Body"]))
        flow.append(Paragraph(f"<i>Source: {m['source']}.</i>", st["Small"]))
        flow.append(Spacer(1, 6))
        return [KeepTogether(flow)]
    df = read_df(code)
    if df is not None:
        flow.append(result_table(df, st))
        flow.append(Spacer(1, 4))
    img = os.path.join(HERE, f"plots_{code}", "MacroAgg_PctChange.png")
    body = []
    para, policy = INTERP[code]
    body.append(Paragraph(para, st["Body"]))
    body.append(Paragraph(policy, st["Policy"]))
    body.append(Paragraph(f"<i>Source of the shock calibration: {m['source']}.</i>", st["Small"]))
    if os.path.exists(img):
        im = fitted_image(img)
        flow.append(KeepTogether([im, Paragraph(
            "Percentage deviation of the reform path from the Ethiopia baseline, "
            "2025 onward (vertical line = first reform year).", st["Cap"])]))
    flow.extend(body)
    flow.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#c3d0de"),
                           spaceBefore=6, spaceAfter=6))
    return flow


def ranking_table(st):
    rows = [("I3", "Maximum Dividend"), ("I2", "Ambitious Package"),
            ("M4", "Brain Gain (+ diaspora capital)"), ("I1", "Moderate Package"),
            ("G3", "Full Female Participation (G3/G4)"),
            ("G2", "Partial Female Participation"), ("E4", "Max Education"),
            ("L4", "Full Formalisation"), ("E3", "Strong Education"),
            ("F4", "Gender-Inclusion Investment"), ("E2", "Moderate TVET"),
            ("L3", "Strong Formalisation"), ("L2", "Moderate Formalisation"),
            ("D2", "Faster Fertility Decline"), ("F2", "Education Spending +2% GDP"),
            ("F5", "Fiscal Consolidation −1.5% GDP"),
            ("M2", "Moderate Brain Drain"), ("M3", "Severe Brain Drain"),
            ("F3", "Youth-Employment Subsidy †")]
    def _ss(code):
        d = read_df(code)
        try:
            return float(d.loc["GDP ($Y_t$)"]["SS"])
        except Exception:
            return -99.0
    rows = sorted(rows, key=lambda r: _ss(r[0]), reverse=True)
    data = [["Scenario", "Long-run GDP\nper worker", "Decade avg\n2025–34"]]
    for code, name in rows:
        df = read_df(code)
        if df is None:
            continue
        ss = df.loc["GDP ($Y_t$)"]["SS"]
        dec = df.loc["GDP ($Y_t$)"]["2025-2034"]
        data.append([f"{code} — {name}", pct(ss), pct(dec)])
    t = Table(data, colWidths=[9.6 * cm, 3.2 * cm, 3.1 * cm])
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c3d0de")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    for i in range(1, len(data)):
        try:
            v = float(data[i][1].replace("%", "").replace("+", ""))
        except Exception:
            v = 0
        ts.append(("TEXTCOLOR", (1, i), (1, i), GREEN if v > 0.2 else (RED if v < -0.2 else colors.grey)))
        ts.append(("FONTNAME", (1, i), (1, i), "Helvetica-Bold"))
    t.setStyle(TableStyle(ts))
    return t


def para_list(texts, st, style="Body"):
    return [Paragraph(t, st[style]) for t in texts]


def build():
    st = styles()
    doc = SimpleDocTemplate(OUT, pagesize=A4, topMargin=1.8 * cm,
                            bottomMargin=1.6 * cm, leftMargin=2.0 * cm,
                            rightMargin=2.0 * cm, title="Ethiopia Youth Dividend — Policy Analysis")
    F = []

    # ---- Title page ----
    F.append(Spacer(1, 3.2 * cm))
    F.append(Paragraph("Harnessing Ethiopia's Youth Dividend", st["TitleBig"]))
    F.append(Paragraph("A Macroeconomic Scenario Analysis for Policymaking", st["SubTitle"]))
    F.append(Spacer(1, 0.5 * cm))
    F.append(HRFlowable(width="60%", thickness=1.2, color=STEEL))
    F.append(Spacer(1, 0.5 * cm))
    F.append(Paragraph("23 policy scenarios across seven dimensions, evaluated with the "
                       "OG-ETH overlapping-generations general-equilibrium model and "
                       "benchmarked against a 2025 Ethiopia baseline.", st["SubTitle"]))
    F.append(Spacer(1, 5.5 * cm))
    F.append(Paragraph("Prepared for policy discussion · June 2026", st["Cap"]))
    F.append(Paragraph("All figures are model-based projections expressed as percentage "
                       "deviations from baseline, in per-effective-worker terms. They are "
                       "scenario analysis, not forecasts.", st["Cap"]))
    F.append(PageBreak())

    # ---- Executive summary ----
    F.append(Paragraph("Executive Summary", st["H1"]))
    F.extend(para_list([
        "Ethiopia's population is young and its working-age share is rising — the demographic "
        "pre-condition for a 'youth dividend'. This study asks a sharper question: under what "
        "policies does that demographic moment actually translate into higher living standards, "
        "and by how much? We evaluate 23 scenarios across seven policy dimensions in a "
        "general-equilibrium model of households, firms and government, each compared with a "
        "common 2025 Ethiopia baseline.",
        "<b>The central finding is that the dividend is real but conditional.</b> It is captured by "
        "raising productivity <i>per worker</i> — through education quality, labour formalisation "
        "and female participation — and by attracting skilled diaspora and their capital. It is "
        "<i>not</i> delivered automatically by demographic change itself, by larger government "
        "consumption, or simply by a bigger population.",
        "<b>The potential is large.</b> A fully realised, coordinated reform programme (the Maximum "
        "Dividend) roughly doubles long-run output per worker (+84%). An ambitious programme adds "
        "~45%; even a moderate, coordinated package adds ~20%. Individually, full female-participation "
        "convergence, maximum education, and full formalisation each deliver durable gains of ~10–13%, "
        "and skilled-diaspora return with capital (brain gain) delivers ~21%.",
        "<b>Timing is decisive.</b> Delaying the ambitious programme by ten years permanently forfeits "
        "about 40% of output per worker for every year of the lost decade — a loss that is never "
        "recovered, because the on-time and delayed paths share the same long-run destination.",
        "<b>Three cautions for interpretation.</b> First, per-worker statistics can rise under "
        "population loss (a smaller workforce sharing the same capital) — a statistical artefact, not "
        "a welfare gain, most visibly in the youth-mortality scenario. Second, increases or cuts in "
        "general government consumption are long-run growth-neutral in this model: 'education spending' "
        "pays off only if it raises measured productivity. Third, one scenario (the youth-employment "
        "subsidy) is sensitive to a labour-supply calibration choice and should be re-specified "
        "before firm conclusions are drawn.",
    ], st))
    F.append(Paragraph("Scenarios ranked by long-run effect on output per worker", st["H3"]))
    F.append(ranking_table(st))
    F.append(Paragraph("† The youth-employment subsidy result is sensitive to a labour-supply "
                       "calibration choice and should be treated as a flag, not a prediction "
                       "(see Dimension 6 and Caveats).", st["Small"]))
    F.append(PageBreak())

    # ---- The baseline ----
    F.append(Paragraph("The Baseline Economy (against which every scenario is measured)", st["H1"]))
    F.extend(para_list([
        "Every result in this report is a comparison against a single common baseline: a model of "
        "Ethiopia beginning in 2025 under current demographics and current fiscal policy, run forward "
        "for a century. The baseline is calibrated to Ethiopia (UN country 231) and follows the UN "
        "World Population Prospects medium-fertility path, with long-run population growth of about "
        "2.0% per year and the realistic, gradually declining-fertility transition built in.",
        "<b>Population and households.</b> Agents live the economic part of the life cycle from age 20 "
        "to 100 (with a 20-year pre-working/education phase), retire at 65, and differ across seven "
        "earnings/ability groups — from a broad base of lower earners up to a small high-skill top "
        "group (about 1% of workers). Households choose how much to work and save each year, looking "
        "ahead over their whole lifetime.",
        "<b>Technology and growth.</b> Firms combine capital and labour with a capital share of ~0.52 "
        "(Cobb–Douglas production). Labour-augmenting productivity grows at 6% per year — the trend "
        "that all 'per-worker' figures are measured net of. Preferences feature a 0.96 annual discount "
        "factor, risk aversion of 1.5, and a baseline Frisch labour-supply elasticity of 0.4.",
        "<b>Fiscal and external setting.</b> Public debt starts at 32.7% of GDP; government consumption "
        "is 5.5% of GDP, transfers 5%, and public investment 4–5%. The corporate income tax is 30% and "
        "the payroll tax 18%. Ethiopia is modelled as a partly-open economy: the world interest rate is "
        "4%, and about 20% of new capital and 12% of new public debt are financed from abroad.",
        "<b>The reforms.</b> Each scenario perturbs this baseline along one dimension (or several, for "
        "the integrated packages). Education, formalisation, participation, migration and youth-subsidy "
        "reforms are represented as changes to the age-and-skill productivity of workers; demographic "
        "scenarios change fertility or mortality; fiscal scenarios change government spending or "
        "transfers. This reduced-form representation is a deliberate simplification — it captures the "
        "first-order economic channel of each policy, not its administrative detail.",
    ], st))
    F.append(PageBreak())

    # ---- How to read the results ----
    F.append(Paragraph("How to Read the Results", st["H1"]))
    F.extend(para_list([
        "<b>Everything is a percentage deviation from baseline.</b> A value of '+9%' for GDP means "
        "output is 9% higher than it would have been on the baseline path in that year — not 9% growth. "
        "Because the economy is also growing along the baseline, the birr levels are higher still.",
        "<b>Quantities are per effective worker.</b> Output, consumption, capital and labour are "
        "expressed in intensive (per-worker, trend-adjusted) terms. This is the right lens for living "
        "standards, but it has one important trap: a policy or shock that <i>shrinks the workforce</i> "
        "can raise these per-worker figures simply by spreading existing capital over fewer people. "
        "That is why the demographic-loss scenarios must be read with care.",
        "<b>Three time horizons are reported.</b> The <i>impact</i> year (2025) shows the immediate "
        "response; the <i>decade average</i> (2025–2034) shows the transition; and the <i>long-run "
        "steady state</i> shows where the economy eventually settles. Many reforms are strongly "
        "front-loaded in consumption (households borrow against higher expected lifetime income) and "
        "then settle to a lower permanent level.",
        "<b>The mechanics to keep in mind.</b> A reform that raises worker productivity first lifts "
        "output and raises the return to capital; investment then accumulates capital to match the more "
        "productive workforce, which gradually restores the interest rate and the capital–output ratio "
        "to their baseline levels. The wage <i>per efficiency unit</i> can end roughly flat even as "
        "<i>labour income per worker</i> rises, because each worker now supplies more efficiency units. "
        "Reading the interest-rate and wage rows together reveals whether a scenario works through "
        "capital deepening (rates fall, wages rise) or pure productivity scaling (rates and wages "
        "return to baseline).",
    ], st))
    F.append(PageBreak())

    # ---- Scenario sections by dimension ----
    F.append(Paragraph("Scenario-by-Scenario Interpretation", st["H1"]))
    for dim_title, dim_desc, codes in DIMENSIONS:
        F.append(Paragraph(dim_title, st["H2"]))
        F.append(Paragraph(dim_desc, st["Body"]))
        for code in codes:
            F.extend(scenario_flow(code, st))
        F.append(Spacer(1, 4))

    # ---- Cost of delay ----
    F.append(PageBreak())
    F.append(Paragraph("The Cost of Delay (the ambitious package, ten years late)", st["H1"]))
    dfc = read_df("cost_of_delay")
    if dfc is not None:
        F.append(result_table(dfc, st))
        F.append(Paragraph("Delayed package (I4) measured directly against the on-time package (I2). "
                           "A long-run steady state of ~0 confirms the two paths reach the same "
                           "destination; the entire cost is the forfeited first decade.", st["Cap"]))
    F.extend(para_list(list(COST_OF_DELAY_PROSE), st))

    # ---- Synthesis ----
    F.append(Paragraph("Synthesis: What the Whole Picture Says", st["H2"]))
    F.extend(para_list([
        "<b>1. Productivity, not population, is the dividend.</b> The scenarios that change the size or "
        "age-shape of the population (Dimension 1) move the transition but leave long-run output per "
        "worker essentially unchanged. The scenarios that raise productivity per worker (Dimensions "
        "2–4) deliver durable, double-digit gains. The demographic window is an opportunity; the "
        "policies that raise worker productivity are what convert it into prosperity.",
        "<b>2. Reforms compound.</b> Coordinated packages deliver far more than the sum of cautious "
        "single steps: moderate-everywhere (~+20%) and ambitious-everywhere (~+45%) dominate any one "
        "lever, and the maximum package (~+84%) approaches a doubling of output per worker.",
        "<b>3. The diaspora is a uniquely powerful lever.</b> Brain gain (~+21%) outperforms education "
        "or formalisation alone because it brings capital as well as skill, and the asymmetry with "
        "brain drain (−3% to −6%) makes retention and return policy especially valuable.",
        "<b>4. Spending is not the same as investment.</b> Raising or cutting general government "
        "consumption is long-run growth-neutral here. What matters is whether public money raises "
        "measured worker productivity — so budgets should be judged on the productivity they create, "
        "not the amount they spend.",
        "<b>5. Time is the scarcest input.</b> Because delayed and on-time reforms share the same long-run "
        "destination, every year of delay is a permanent, unrecoverable forfeit of that year's higher "
        "output. The economics points unambiguously to early, coordinated action.",
    ], st))

    # ---- Caveats ----
    F.append(PageBreak())
    F.append(Paragraph("Caveats and Limitations", st["H1"]))
    F.extend(para_list([
        "<b>Per-worker (intensive) metrics can mislead under population loss.</b> A mortality or "
        "emigration shock that removes workers raises capital per surviving worker and therefore raises "
        "measured per-worker output and consumption, even though aggregate output, population and "
        "welfare fall. The youth-mortality scenario (D3) is the clearest example and must not be read "
        "as a positive outcome.",
        "<b>Government consumption is modelled as unproductive.</b> The fiscal-spending scenarios (F2, "
        "F5) change general government consumption, which has no direct effect on productive capacity; "
        "hence their long-run neutrality. A genuinely productive public investment — one that raises "
        "worker skills or infrastructure productivity — would instead work through the education-style "
        "channels and would not be neutral.",
        "<b>Labour-supply elasticity changes are not re-calibrated.</b> Several scenarios raise the "
        "Frisch elasticity (the labour, formalisation, youth-subsidy and integrated families). Doing "
        "so without re-calibrating the labour-disutility scale shifts the <i>level</i> of hours worked, "
        "which can offset modest productivity gains. The youth-employment subsidy (F3) is the case "
        "where this dominates and produces a counterintuitive contraction; that result should be "
        "treated as a calibration flag, not a policy prediction.",
        "<b>Open-economy capital amplifies the largest packages.</b> The brain-gain and maximum "
        "scenarios (M4, I3) allow additional foreign-financed capital (diaspora investment); part of "
        "their exceptional capital deepening reflects this inflow and is contingent on the assumed "
        "access to external finance.",
        "<b>A terminal-period boundary check (since resolved).</b> Five scenarios (E2, L2, L3, G3, G4) "
        "initially tripped the model's transition-path resource-constraint check. On inspection the "
        "converged solutions satisfied goods-market clearing to ~1e-6 at every period of the modelled "
        "horizon (and the steady state to ~1e-14); the only violation was confined to the single "
        "artificial terminal period (~year 2344, three centuries beyond the policy window) — a known "
        "boundary artifact. They are therefore reported in full, after explicit quality checks confirmed "
        "the in-window solution is identical in quality to the scenarios that passed automatically.",
        "<b>These are scenario projections, not forecasts.</b> Each reform is a stylised, first-order "
        "representation of a complex policy, and the model abstracts from many real-world frictions "
        "(implementation capacity, sectoral detail, informality dynamics, external shocks). The results "
        "are best used to compare the <i>direction and relative magnitude</i> of policy options, not as "
        "point predictions of future GDP.",
    ], st))

    # ---- Appendix: data sources ----
    F.append(Paragraph("Data Sources Cited in the Scenario Calibration", st["H2"]))
    srcs = sorted({m["source"] for m in META.values()})
    F.extend([Paragraph(f"• {s}", st["Small"]) for s in srcs])

    doc.build(F)
    print("WROTE", OUT)


if __name__ == "__main__":
    build()
