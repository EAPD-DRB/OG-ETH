"""Regenerate the charts affected by finalizing E2/L2/L3/G3/G4 (gender now
observed, not estimated) and add the G3-vs-G4 'speed of convergence' chart."""
import os, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
HERE=os.path.dirname(os.path.realpath(__file__)); OUT=os.path.join(HERE,"synthesis_charts")
NAVY="#10243f";STEEL="#33597f";GREEN="#1d6b34";RED="#a32020";GOLD="#b8860b"
plt.rcParams.update({"font.size":11,"axes.edgecolor":"#888","axes.grid":True,
                     "grid.color":"#dde5ee","grid.linewidth":0.7,"figure.dpi":150})
pf=FuncFormatter(lambda x,_:f"{x:+.0f}%")
def L(c): return pd.read_csv(os.path.join(HERE,f"results_{c}.csv")).set_index("Variable")
GDP="GDP ($Y_t$)"
def ss(c): return float(L(c).loc[GDP]["SS"])

# ---- A: decomposition (gender now full convergence G3) ----
items=[("Demographics\n(transition only)",max(ss('D2'),ss('D3'),ss('D4')),STEEL),
       ("Moderate TVET (E2)",ss('E2'),STEEL),
       ("Fiscal/gender\ninvestment (F4)",ss('F4'),STEEL),
       ("Strong education (E3)",ss('E3'),STEEL),
       ("Full formalisation (L4)",ss('L4'),STEEL),
       ("Max education (E4)",ss('E4'),STEEL),
       ("Full female\nparticipation (G3/G4)",ss('G3'),STEEL),
       ("Brain gain +\ndiaspora capital (M4)",ss('M4'),STEEL),
       ("Moderate package (I1)",ss('I1'),NAVY),
       ("Ambitious package (I2)",ss('I2'),NAVY),
       ("Maximum dividend (I3)",ss('I3'),NAVY)]
items=sorted(items,key=lambda x:x[1])
fig,ax=plt.subplots(figsize=(8.6,5.4)); y=np.arange(len(items)); v=[i[1] for i in items]
ax.barh(y,v,color=[i[2] for i in items],height=0.64)
ax.set_yticks(y); ax.set_yticklabels([i[0] for i in items],fontsize=9.1)
for yi,val in zip(y,v):
    ax.text(val+1.2,yi,f"{val:+.0f}%",va="center",ha="left",fontsize=9,fontweight="bold",
            color=GREEN if val>0 else "#555")
ax.xaxis.set_major_formatter(pf); ax.axvline(0,color="#555",lw=0.9); ax.set_xlim(-2,95)
ax.set_title("Decomposition of Ethiopia's Youth Dividend\nLong-run gain in GDP per worker, by reform (vs 2025 baseline)",
             fontsize=12,fontweight="bold",color=NAVY); ax.grid(axis="y",visible=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT,"A_decomposition.png")); plt.close(fig)

# ---- E: gender growth (full convergence now observed) ----
def ann(lvl,yrs=25): return ((1+lvl/100)**(1/yrs)-1)*100
gp,gf=ann(ss('G2')),ann(ss('G3'))
fig,ax=plt.subplots(figsize=(7.0,4.3))
b=ax.bar(["Partial convergence\n(G2, observed)","Full convergence\n(G3/G4, observed)"],[gp,gf],
         color=[STEEL,NAVY],width=0.5)
ax.axhline(1.0,color=GOLD,lw=1.6,ls="--",label="Concept Note claim:\n~1.0 pp/yr extra growth")
for bar,val in zip(b,[gp,gf]):
    ax.text(bar.get_x()+bar.get_width()/2,val+0.03,f"+{val:.2f} pp/yr",ha="center",fontweight="bold",color=NAVY,fontsize=10.5)
ax.set_ylabel("Extra annual GDP-per-worker growth, 2025–2050"); ax.set_ylim(0,1.2)
ax.yaxis.set_major_formatter(FuncFormatter(lambda x,_:f"{x:.1f}"))
ax.set_title("Does female participation add ~1 percentage point of growth?\nLevel gain converted to annualised growth over 25 years",
             fontsize=10.8,fontweight="bold",color=NAVY); ax.legend(loc="upper left",fontsize=8.6,frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT,"E_gender_growth.png")); plt.close(fig)

# ---- F: speed of convergence, G3 (2040) vs G4 (2030) ----
yrs=[str(y) for y in range(2025,2035)]
g3=[float(L('G3').loc[GDP][y]) for y in yrs]; g4=[float(L('G4').loc[GDP][y]) for y in yrs]
fig,ax=plt.subplots(figsize=(8.4,4.5))
ax.plot(range(len(yrs)),g4,color=GREEN,marker="o",lw=2.2,label="G4 — accelerated (full by 2030)")
ax.plot(range(len(yrs)),g3,color=STEEL,marker="s",lw=2.2,label="G3 — gradual (full by 2040)")
ax.axhline(ss('G3'),color="#999",ls=":",lw=1.4)
ax.text(0.1,ss('G3')+0.6,f"shared long-run: {ss('G3'):+.0f}%",color="#555",fontsize=8.8)
ax.set_xticks(range(len(yrs))); ax.set_xticklabels(yrs,fontsize=8.5)
ax.yaxis.set_major_formatter(pf); ax.set_ylim(-2,24)
ax.set_title("The 'speed of convergence' dividend: same destination, faster route\nGDP per worker, female-participation convergence",
             fontsize=11,fontweight="bold",color=NAVY); ax.legend(loc="upper left",fontsize=9,frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT,"F_gender_timing.png")); plt.close(fig)
print("updated A, E; added F. gender annualised: partial=%.2f full=%.2f pp/yr"%(gp,gf))
