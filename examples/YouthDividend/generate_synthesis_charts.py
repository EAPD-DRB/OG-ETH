"""Synthesis charts answering the Concept Note research questions."""
import os, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

HERE = os.path.dirname(os.path.realpath(__file__))
OUT = os.path.join(HERE, "synthesis_charts"); os.makedirs(OUT, exist_ok=True)
NAVY="#10243f"; STEEL="#33597f"; GREEN="#1d6b34"; RED="#a32020"; GOLD="#b8860b"; LIGHT="#eef3f8"
plt.rcParams.update({"font.size":11,"axes.edgecolor":"#888","axes.grid":True,
                     "grid.color":"#dde5ee","grid.linewidth":0.7,"figure.dpi":150})
pf = FuncFormatter(lambda x,_: f"{x:+.0f}%")

def L(code): return pd.read_csv(os.path.join(HERE,f"results_{code}.csv")).set_index("Variable")
GDP="GDP ($Y_t$)"
def ss(c): return float(L(c).loc[GDP]["SS"])
def dec(c): return float(L(c).loc[GDP]["2025-2034"])

# ---- Chart A: Decomposition of the dividend (long-run GDP/worker) ----
items=[("Demographics\n(transition only)",max(ss('D2'),ss('D3'),ss('D4')),STEEL),
       ("Fiscal/gender\ninvestment (F4)",ss('F4'),STEEL),
       ("Strong education (E3)",ss('E3'),STEEL),
       ("Full formalisation (L4)",ss('L4'),STEEL),
       ("Max education (E4)",ss('E4'),STEEL),
       ("Partial female\nparticipation (G2)",ss('G2'),STEEL),
       ("Brain gain +\ndiaspora capital (M4)",ss('M4'),STEEL),
       ("Moderate package (I1)",ss('I1'),NAVY),
       ("Ambitious package (I2)",ss('I2'),NAVY),
       ("Maximum dividend (I3)",ss('I3'),NAVY)]
items=sorted(items,key=lambda x:x[1])
fig,ax=plt.subplots(figsize=(8.6,5.2))
y=np.arange(len(items)); vals=[i[1] for i in items]; cols=[i[2] for i in items]
ax.barh(y,vals,color=cols,height=0.62)
ax.set_yticks(y); ax.set_yticklabels([i[0] for i in items],fontsize=9.3)
for yi,v in zip(y,vals):
    ax.text(v+ (1.2 if v>=0 else -1.2),yi,f"{v:+.0f}%",va="center",
            ha="left" if v>=0 else "right",fontsize=9,fontweight="bold",
            color=GREEN if v>0 else (RED if v<0 else "#555"))
ax.xaxis.set_major_formatter(pf); ax.axvline(0,color="#555",lw=0.9)
ax.set_xlim(-5,95); ax.set_title("Decomposition of Ethiopia's Youth Dividend\nLong-run gain in GDP per worker, by reform (vs 2025 baseline)",
            fontsize=12,fontweight="bold",color=NAVY)
ax.grid(axis="y",visible=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT,"A_decomposition.png")); plt.close(fig)

# ---- Chart B: Integrated packages vs Concept Note's 20-35% target ----
fig,ax=plt.subplots(figsize=(7.2,4.6))
codes=["I1","I2","I3"]; names=["Moderate\n(I1)","Ambitious\n(I2)","Maximum\n(I3)"]
v=[ss(c) for c in codes]
ax.axhspan(20,35,color=GOLD,alpha=0.18,label="Concept Note target:\n+20–35% by 2050")
bars=ax.bar(names,v,color=[STEEL,NAVY,NAVY],width=0.55)
for b,val in zip(bars,v):
    ax.text(b.get_x()+b.get_width()/2,val+1.5,f"{val:+.0f}%",ha="center",
            fontweight="bold",color=GREEN,fontsize=11)
ax.yaxis.set_major_formatter(pf); ax.set_ylim(0,95)
ax.set_title("Integrated reform packages vs the Concept Note's projection\nLong-run GDP per worker",
             fontsize=12,fontweight="bold",color=NAVY)
ax.legend(loc="upper left",fontsize=9,frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT,"B_packages_vs_target.png")); plt.close(fig)

# ---- Chart C: Cost of delay over the lost decade ----
cd=pd.read_csv(os.path.join(HERE,"results_cost_of_delay.csv")).set_index("Variable")
yrs=[str(y) for y in range(2025,2035)]; g=[float(cd.loc[GDP][y]) for y in yrs]
fig,ax=plt.subplots(figsize=(8.4,4.4))
ax.fill_between(range(len(yrs)),g,0,color=RED,alpha=0.18)
ax.plot(range(len(yrs)),g,color=RED,marker="o",lw=2,label="GDP per worker: delayed (I4) vs on-time (I2)")
for i,val in enumerate(g):
    if i in (0,len(g)-1): ax.text(i,val-2.4,f"{val:.0f}%",ha="center",color=RED,fontsize=9,fontweight="bold")
ax.axhline(0,color="#555",lw=0.9)
ax.set_xticks(range(len(yrs))); ax.set_xticklabels(yrs,rotation=0,fontsize=8.5)
ax.yaxis.set_major_formatter(pf); ax.set_ylim(-46,6)
ax.annotate("Long-run: 0%\n(paths converge — the\nlost decade is never recovered)",
            xy=(len(yrs)-1,g[-1]),xytext=(4.4,-12),fontsize=8.6,color=NAVY,
            ha="center",arrowprops=dict(arrowstyle="->",color=NAVY,lw=0.8))
ax.set_title("The Cost of a 10-Year Delay (Ambitious package, started 2035 not 2025)\nAnnual shortfall in GDP per worker during 2025–2034",
             fontsize=11.5,fontweight="bold",color=NAVY)
ax.legend(loc="lower right",fontsize=8.6,frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT,"C_cost_of_delay.png")); plt.close(fig)

# ---- Chart D: Brain drain vs brain gain asymmetry ----
fig,ax=plt.subplots(figsize=(7.0,4.4))
codes=["M3","M2","M4"]; names=["Severe drain\n(M3)","Moderate drain\n(M2)","Brain gain +\ncapital (M4)"]
v=[ss(c) for c in codes]; cols=[RED,RED,GREEN]
bars=ax.bar(names,v,color=cols,width=0.55)
for b,val in zip(bars,v):
    ax.text(b.get_x()+b.get_width()/2,val+(1.0 if val>=0 else -1.0),f"{val:+.0f}%",
            ha="center",va="bottom" if val>=0 else "top",fontweight="bold",
            color=GREEN if val>0 else RED,fontsize=11)
ax.axhline(0,color="#555",lw=0.9); ax.yaxis.set_major_formatter(pf); ax.set_ylim(-10,26)
ax.set_title("Migration is asymmetric: losing skills costs little, gaining skills+capital pays a lot\nLong-run GDP per worker",
             fontsize=10.8,fontweight="bold",color=NAVY)
fig.tight_layout(); fig.savefig(os.path.join(OUT,"D_brain.png")); plt.close(fig)

# ---- Chart E: Gender participation -> annual growth contribution ----
def annualise(level_pct,years=25): return ((1+level_pct/100)**(1/years)-1)*100
g_partial=annualise(ss('G2')); g_full=annualise(25.0)  # full conv ~+25% (embedded estimate)
fig,ax=plt.subplots(figsize=(7.0,4.3))
names=["Partial convergence\n(G2, observed)","Full convergence\n(G3/G4, estimated)"]
v=[g_partial,g_full]
bars=ax.bar(names,v,color=[STEEL,NAVY],width=0.5)
ax.axhline(1.0,color=GOLD,lw=1.6,ls="--",label="Concept Note claim:\n~1.0 pp/yr extra growth")
for b,val in zip(bars,v):
    ax.text(b.get_x()+b.get_width()/2,val+0.03,f"+{val:.2f} pp/yr",ha="center",
            fontweight="bold",color=NAVY,fontsize=10.5)
ax.set_ylabel("Extra annual GDP-per-worker growth, 2025–2050")
ax.set_ylim(0,1.2); ax.yaxis.set_major_formatter(FuncFormatter(lambda x,_:f"{x:.1f}"))
ax.set_title("Does female participation add ~1 percentage point of growth?\nLevel gain converted to annualised growth over 25 years",
             fontsize=10.8,fontweight="bold",color=NAVY)
ax.legend(loc="upper left",fontsize=8.6,frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT,"E_gender_growth.png")); plt.close(fig)

print("charts written to", OUT)
for f in sorted(os.listdir(OUT)): print(" ",f)
