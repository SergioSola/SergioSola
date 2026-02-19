"""
Generate unified PDF outline of the full 4-project research programme.
For each project: title, research questions, empirical strategy, contributions.
"""
from fpdf import FPDF
from datetime import date


class R(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        if self.page_no() == 1: return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "NBFI & Systemic Risk -- Research Programme", align="L")
        self.cell(0, 8, "Sergio Sola, 2026", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        if self.page_no() == 1: return
        self.set_y(-20)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 10, f"Page {self.page_no()-1}", align="C")

    def h1(self, t):
        self.ln(3); self.set_font("Helvetica","B",14); self.set_text_color(20,40,80)
        self.cell(0,9,t,new_x="LMARGIN",new_y="NEXT")
        self.set_draw_color(40,100,160); self.line(10,self.get_y(),120,self.get_y()); self.ln(4)

    def h2(self, t):
        self.ln(2); self.set_font("Helvetica","B",11); self.set_text_color(40,100,160)
        self.cell(0,7,t,new_x="LMARGIN",new_y="NEXT"); self.ln(2)

    def h3(self, t):
        self.set_font("Helvetica","BI",10); self.set_text_color(60,60,60)
        self.cell(0,6,t,new_x="LMARGIN",new_y="NEXT"); self.ln(1)

    def p(self, t):
        self.set_font("Helvetica","",9.5); self.set_text_color(30,30,30)
        self.multi_cell(0,5,t); self.ln(2)

    def b(self, t, indent=15):
        x=self.get_x(); self.set_x(x+indent)
        self.set_font("Helvetica","",9); self.set_text_color(30,30,30)
        w=self.w-self.r_margin-self.get_x()
        self.cell(4,5,"-"); self.multi_cell(w-4,5,t); self.set_x(x); self.ln(1)

    def rq(self, n, t, indent=15):
        x=self.get_x(); self.set_x(x+indent)
        self.set_font("Helvetica","B",9); self.set_text_color(40,100,160)
        self.cell(12,5,f"RQ{n}."); self.set_font("Helvetica","",9); self.set_text_color(30,30,30)
        w=self.w-self.r_margin-self.get_x()
        self.multi_cell(w-12,5,t); self.set_x(x); self.ln(1)

    def ni(self, n, t, indent=15):
        x=self.get_x(); self.set_x(x+indent)
        self.set_font("Helvetica","B",9); self.set_text_color(40,100,160)
        self.cell(8,5,f"{n}."); self.set_font("Helvetica","",9); self.set_text_color(30,30,30)
        w=self.w-self.r_margin-self.get_x()
        self.multi_cell(w-8,5,t); self.set_x(x); self.ln(1)

    def box(self, t):
        self.set_fill_color(242,244,248); self.set_font("Helvetica","I",9); self.set_text_color(40,40,40)
        self.multi_cell(0,5,t,fill=True); self.ln(3)

    def pbox(self, num, title, sub):
        self.set_fill_color(20,40,80); y=self.get_y()
        self.rect(10,y,190,20,"F")
        self.set_xy(15,y+3); self.set_font("Helvetica","B",14); self.set_text_color(255,255,255)
        self.cell(0,7,f"Project {num}: {title}")
        self.set_xy(15,y+11); self.set_font("Helvetica","I",10); self.set_text_color(200,215,240)
        self.cell(0,7,sub); self.set_y(y+24)

    def th(self, cols, ws):
        self.set_font("Helvetica","B",8); self.set_fill_color(20,40,80); self.set_text_color(255,255,255)
        for c,w in zip(cols,ws): self.cell(w,7,c,border=1,align="C",fill=True)
        self.ln()

    def tr(self, cells, ws, s=False):
        self.set_font("Helvetica","",8); self.set_text_color(30,30,30)
        self.set_fill_color(245,247,250) if s else self.set_fill_color(255,255,255)
        for c,w in zip(cells,ws): self.cell(w,6,c,border=1,fill=True)
        self.ln()


def build():
    pdf = R()

    # TITLE PAGE
    pdf.add_page()
    pdf.set_fill_color(20,40,80); pdf.rect(0,0,210,50,"F")
    pdf.set_fill_color(40,100,160); pdf.rect(0,50,210,4,"F")
    pdf.set_y(65); pdf.set_font("Helvetica","B",24); pdf.set_text_color(20,40,80)
    pdf.multi_cell(0,11,"Non-Bank Financial Intermediation\nand Systemic Risk",align="C")
    pdf.ln(3); pdf.set_font("Helvetica","",15); pdf.set_text_color(40,100,160)
    pdf.cell(0,9,"Research Programme Overview",align="C",new_x="LMARGIN",new_y="NEXT")
    pdf.ln(3); pdf.set_draw_color(40,100,160); pdf.line(55,pdf.get_y(),155,pdf.get_y()); pdf.ln(8)

    for label, title, sub in [
        ("Project 1","The Shadow Leverage Map","Reverse-engineering hidden NBFI leverage from repo & derivatives data"),
        ("Project 2","Mapping the Channels","Network analysis of NBFI amplification in monetary policy transmission"),
        ("Project 3","Contagion Across Borders","How NBFI stress spills over via dollar funding & the global financial cycle"),
        ("Project 4","FX Hedging as a Contagion Channel","How NBFI currency risk management transmits global financial shocks"),
    ]:
        pdf.set_fill_color(240,243,248); pdf.set_draw_color(40,100,160); y=pdf.get_y()
        pdf.rect(25,y,160,18,"FD")
        pdf.set_xy(30,y+2); pdf.set_font("Helvetica","B",10); pdf.set_text_color(20,40,80)
        pdf.cell(30,6,label,new_x="END"); pdf.cell(0,6,title)
        pdf.set_xy(60,y+9); pdf.set_font("Helvetica","I",8.5); pdf.set_text_color(80,80,80)
        pdf.cell(0,6,sub); pdf.set_y(y+22)

    pdf.ln(8); pdf.set_font("Helvetica","",12); pdf.set_text_color(50,50,50)
    pdf.cell(0,8,"Sergio Sola",align="C",new_x="LMARGIN",new_y="NEXT")
    pdf.set_font("Helvetica","I",11)
    pdf.cell(0,8,date.today().strftime("%B %Y"),align="C",new_x="LMARGIN",new_y="NEXT")
    pdf.set_fill_color(20,40,80); pdf.rect(0,277,210,20,"F")

    # ── PROGRAMME OVERVIEW ──
    pdf.add_page()
    pdf.h1("1. Programme Overview")
    pdf.p(
        "This research programme investigates the systemic risk implications of "
        "non-bank financial intermediation (NBFI) across four complementary projects. "
        "Each project addresses a distinct dimension of NBFI-related systemic risk -- "
        "hidden leverage, monetary policy amplification, cross-border contagion, and "
        "FX hedging transmission -- while sharing a common methodological toolkit based "
        "on quantile methods, network analysis, and tail-risk econometrics."
    )
    pdf.p(
        "The unifying theme is that NBFI risks are fundamentally nonlinear: they are "
        "largely invisible in normal times but activate powerfully during stress. "
        "Standard mean-based econometric methods (OLS, linear VARs) miss these dynamics. "
        "All four projects therefore employ quantile-specific methods -- quantile "
        "regression, quantile connectedness (Ando, Greenwood-Nimmo & Shin 2022), "
        "Delta-CoVaR (Adrian & Brunnermeier 2016), and location-scale models (Adrian, "
        "Boyarchenko & Giannone 2019) -- to capture tail amplification and asymmetric "
        "contagion."
    )
    ws=[25,75,90]
    pdf.th(["Project","Focus","Key Innovation"],ws)
    for i,r in enumerate([
        ("P1","Shadow leverage in repo & derivatives","Hidden Leverage Index (spectral measure)"),
        ("P2","MP transmission through NBFIs","Resolves Banerjee et al. (2025) puzzle"),
        ("P3","Cross-border NBFI contagion","Quantile connectedness across countries"),
        ("P4","FX hedging as contagion channel","Offsetting forces / tail amplification"),
    ]): pdf.tr(r,ws,s=i%2==1)

    # ── PROJECT 1 ──
    pdf.add_page()
    pdf.pbox(1,"The Shadow Leverage Map","Tracing Hidden Non-Bank Exposures Through Repo and Derivatives Data")
    pdf.p(
        "NBFIs now account for nearly half of global financial assets, yet their leverage "
        "remains largely invisible to regulators. This project develops a Shadow Leverage Map "
        "that reverse-engineers leverage embedded in NBFI balance sheets using publicly "
        "available data from repo markets (OFR, ECB MMSR), derivatives reporting (DTCC), "
        "and FSB monitoring data."
    )
    pdf.h2("Research Questions")
    pdf.rq(1,"Can NBFI leverage be reverse-engineered from observable market data (repo volumes, derivatives notional, equity proxies)?")
    pdf.rq(2,"How are banks and NBFIs interconnected through repo and derivatives exposures, and how do these interconnections evolve over time and during stress?")
    pdf.rq(3,"Can a spectral measure of network structure (the Hidden Leverage Index, based on the largest eigenvalue of the exposure-weighted adjacency matrix) serve as a predictor of systemic events?")
    pdf.rq(4,"Does hidden leverage amplify tail risk during stress? Is the bank-NBFI system more interconnected in the tails, and does high hidden leverage predict worse left-tail growth (GaR)?")

    pdf.h2("Empirical Strategy")
    pdf.h3("Method 1: Implied Leverage Estimation")
    pdf.box("    Implied Leverage_i = (E_i + R_i + delta * D_i) / E_i\n\n"
        "    E_i = equity proxy (FSB data)    R_i = repo borrowing (OFR/MMSR)\n"
        "    D_i = derivatives notional (DTCC), scaled by delta-equivalent\n\n"
        "Captures economic leverage that regulatory ratios miss.")
    pdf.h3("Method 2: Bipartite Bank-NBFI Network")
    pdf.p("Directed weighted network: G-SIB bank nodes and NBFI sector nodes, with edges "
        "representing repo lending and derivatives counterparty risk. Evolves quarterly.")
    pdf.h3("Method 3: Hidden Leverage Index (Spectral)")
    pdf.box("    HLI_t = lambda_1(W_t)  [largest eigenvalue of exposure matrix]\n\n"
        "Captures systemic amplification potential. Related to spectral radius\n"
        "in contagion models (Acemoglu, Ozdaglar & Tahbaz-Salehi 2015).")
    pdf.h3("Method 4: Tail Risk Econometrics")
    pdf.b("Quantile connectedness (tau=0.05 vs 0.50) -- is the system more interconnected in the tails?")
    pdf.b("Tail-risk amplification: quantile regression with stress x HLI interaction.")
    pdf.b("Growth-at-Risk (Adrian et al. 2019): does high HLI predict worse left-tail GDP growth?")

    pdf.h2("Expected Contributions")
    pdf.ni(1,"First implied leverage measure for NBFIs from publicly observable market data.")
    pdf.ni(2,"Hidden Leverage Index as leading indicator -- spikes before March 2020 and Sep 2022.")
    pdf.ni(3,"Shadow leverage amplifies left-tail risk (GaR) but has no effect at the median.")
    pdf.ni(4,"Quantile connectedness confirms asymmetric contagion in bank-NBFI networks.")

    # ── PROJECT 2 ──
    pdf.add_page()
    pdf.pbox(2,"Mapping the Channels","Network Analysis of Non-Bank Amplification in Monetary Policy Transmission")
    pdf.p(
        "Building on Banerjee, Hofmann, Ng & Pinter (2025, BIS Bulletin 116), who document "
        "that OFIs amplify monetary policy transmission while ICPFs dampen it, we decompose "
        "this aggregate effect using granular network and connectedness methods. We address "
        "which OFI sub-sectors drive the amplification, through which balance-sheet channels "
        "it operates, and under what conditions it intensifies."
    )
    pdf.h2("Hypotheses")
    pdf.rq(1,"Heterogeneous amplification: procyclicality beta is highest for hedge funds, "
        "moderate for bond funds/MMFs, lowest for pension/insurance (H1).")
    pdf.rq(2,"Nonlinear tail transmission: quantile IRFs at tau=0.05 show 2-3x stronger "
        "responses than at tau=0.50, especially for policy rate -> HF returns (H2).")
    pdf.rq(3,"Variance amplification: NBFI leverage increases the conditional variance of "
        "future growth outcomes, generating fatter left tails (H3).")
    pdf.rq(4,"Network containment: during the 2022-23 hiking cycle, within-OFI connectedness "
        "was high but OFI-to-real-economy connectedness remained low (H4).")

    pdf.h2("Empirical Strategy")
    pdf.h3("Module 1: VaR-Constraint Channel (Adrian & Shin 2010, 2014)")
    pdf.p("Procyclicality of leverage by NBFI sub-sector. Fire-sale simulation: bank-only "
        "vs bank+NBFI system response to a -5% shock.")
    pdf.h3("Module 2: DCC-GARCH Dynamic Correlations (Engle 2002)")
    pdf.p("Time-varying correlations between bank and NBFI sector returns. Tracks "
        "correlation spikes during stress for bank-HF, bank-MMF, bank-insurance pairs.")
    pdf.h3("Module 3: Quantile VAR -- Nonlinear Transmission")
    pdf.box("    Q_tau(y_{i,t} | Y_{t-1},...,Y_{t-p}) = c_i + SUM B_{ij}^(l)(tau) y_{j,t-l}\n\n"
        "Estimated at tau = {0.05, 0.25, 0.50, 0.75, 0.95}.\n"
        "If MP transmission through NBFIs is a tail phenomenon, IRFs at\n"
        "tau=0.05 >> tau=0.50. Quantile connectedness confirms.")
    pdf.h3("Module 4: Location-Scale GaR")
    pdf.box("    Location: E[y_{t+h}] = X'beta\n"
        "    Scale:    log Var[y_{t+h}] = Z'gamma\n\n"
        "If gamma_NBFI > 0: NBFI leverage fattens the tails of future growth.")
    pdf.h3("Module 5: Resolving the Banerjee et al. Puzzle")
    pdf.p("Diebold-Yilmaz decomposition shows within-OFI connectedness was high in 2022-23 "
        "but OFI-to-real-economy connectedness remained low. Banks' post-Basel III capital "
        "acted as a firewall.")

    pdf.h2("Expected Contributions")
    pdf.ni(1,"Sub-sector decomposition: hedge funds drive amplification, pension funds dampen it.")
    pdf.ni(2,"Quantile connectedness reveals tail-specific MP amplification invisible to linear methods.")
    pdf.ni(3,"Location-scale: NBFI leverage fattens both tails (variance effect), not just shifts the mean.")
    pdf.ni(4,"Resolution of the 2022-23 resilience puzzle via network topology analysis.")

    # ── PROJECT 3 ──
    pdf.add_page()
    pdf.pbox(3,"Contagion Across Borders","How NBFI Stress in One Jurisdiction Spills Over via the Global Financial Cycle")
    pdf.p(
        "Cross-border NBFI linkages create a powerful transmission mechanism through three "
        "interconnected channels: (1) dollar funding, where NBFIs borrow in USD via repo "
        "and FX swaps; (2) portfolio rebalancing by global investment funds; and (3) the "
        "global financial cycle (Rey 2013), a common factor that NBFIs amplify through "
        "leverage and procyclical behavior."
    )
    pdf.h2("Research Questions")
    pdf.rq(1,"Is cross-border NBFI connectedness asymmetric -- dramatically higher in the left tail (stress) than at the median (normal times)?")
    pdf.rq(2,"Does dollar funding stress transmit cross-border, and is this transmission nonlinear (stronger in the tails)?")
    pdf.rq(3,"Are NBFI portfolio flows more volatile and more cross-border-connected than bank flows?")
    pdf.rq(4,"Does NBFI penetration amplify transmission of the global financial cycle to local conditions? Robust to IV?")
    pdf.rq(5,"Can a hedge fund failure cascade through prime brokerage links to generate cross-border deleveraging?")

    pdf.h2("Empirical Strategy")
    pdf.h3("Triple Helix: Three Contagion Channels")
    pdf.b("Dollar funding: FX swap basis -> NBFI deleveraging -> fire sales -> cross-border (quantile regression / GaR).")
    pdf.b("Portfolio flows: NBFI vs bank flows -> Diebold-Yilmaz connectedness on cross-country flow data.")
    pdf.b("GFC: PCA extraction (Miranda-Agrippino & Rey 2020) -> panel regression with NBFI interaction -> IV.")
    pdf.h3("Core: Cross-Country Quantile Connectedness")
    pdf.box("    System: {US equity, UK equity, EU equity, JP equity, EM equity, USD funding}\n"
        "    Estimated at tau = {0.05, 0.50, 0.95}\n\n"
        "Key prediction: Total connectedness at tau=0.05 >> tau=0.50.\n"
        "Rolling quantile connectedness tracks time-varying tail spillovers.")
    pdf.h3("GFC Amplification Panel Regressions")
    pdf.box("    y_{c,t} = alpha_c + beta_1*GFC_t + beta_2*NBFI_{c,t}\n"
        "              + beta_3*(GFC_t x NBFI_{c,t}) + epsilon\n\n"
        "If beta_3 > 0: NBFI penetration amplifies GFC transmission.\n"
        "IV: US monetary policy shocks instrument the GFC factor.")
    pdf.h3("Contagion Cascade Simulation")
    pdf.p("Agent-based: US HF failure -> prime broker losses -> multi-round forced "
        "deleveraging -> cross-border loss propagation (Eisenberg-Noe + Kyle price impact).")

    pdf.h2("Expected Contributions")
    pdf.ni(1,"Left-tail connectedness across borders is 40-60% higher than median connectedness.")
    pdf.ni(2,"NBFI flows are more volatile and more cross-border-connected than bank flows.")
    pdf.ni(3,"NBFI penetration amplifies GFC transmission (robust to IV with US MP shocks).")
    pdf.ni(4,"Location-scale: NBFI flows fatten the tails of EME return distributions.")

    # ── PROJECT 4 ──
    pdf.add_page()
    pdf.pbox(4,"FX Hedging as a Contagion Channel","How NBFI Currency Risk Management Transmits Global Financial Shocks")
    pdf.p(
        "The global FX derivatives market ($75 trillion outstanding, BIS end-2024) is driven "
        "primarily by NBFIs hedging cross-border bond investments. Combining Rey, Stavrakeva "
        "& Tang (2024) on currency centrality with Nenova, Schrimpf & Shin (2025) on FX "
        "derivatives, we identify a contagion chain: equity shocks -> FX movements -> hedging "
        "cost changes -> NBFI portfolio adjustment -> bond flow reversal -> feedback."
    )
    pdf.h2("Research Questions")
    pdf.rq(1,"Do offsetting forces between equity-driven FX movements and yield curve dynamics break down in the tails? (Quantile regression of CIP basis.)")
    pdf.rq(2,"Does FX hedging stress have systemic risk implications for cross-border bond flows? (Delta-CoVaR.)")
    pdf.rq(3,"Does the equity-FX-CIP-bonds transmission chain activate asymmetrically during crises? (Quantile connectedness.)")
    pdf.rq(4,"Do countries with higher NBFI penetration experience stronger contagion through the FX hedging channel? (Panel + IV.)")

    pdf.h2("Empirical Strategy: Three Layers")
    pdf.h3("Layer 1: Quantile Regression -- Offsetting Forces Test")
    pdf.box("    Q_tau(CIP_basis) = alpha + beta_1*Equity + beta_2*SlopeDiff\n"
        "                        + beta_3*VIX + beta_4*(Equity x VIX)\n\n"
        "beta_4 small at tau=0.50, large at tau=0.05 and 0.95.\n"
        "Offsetting forces break down during stress -> amplification.")
    pdf.h3("Layer 2: Delta-CoVaR (Adrian & Brunnermeier 2016)")
    pdf.box("    Delta-CoVaR = CoVaR(bond_flows | CIP = stressed)\n"
        "                 - CoVaR(bond_flows | CIP = median)\n\n"
        "Large negative Delta-CoVaR = FX hedging stress amplifies bond flow tail risk.")
    pdf.h3("Layer 3: Quantile Connectedness")
    pdf.box("    System: {US equity, FX return, CIP basis, Bond flows}\n"
        "    at tau = {0.05, 0.50, 0.95}\n\n"
        "Transmission chain dormant at median, active during stress.")
    pdf.h3("The Offsetting Forces Hypothesis")
    pdf.p("In normal times: USD appreciation raises hedging costs, but yield curve steepening "
        "makes hedged carry attractive -- partial offset. In stress: USD appreciation, "
        "curve flattening, and CIP blowout all reinforce. Testable only with quantile methods.")

    pdf.h2("Expected Contributions")
    pdf.ni(1,"First complete model of the equity-FX-hedging-bonds contagion chain, combining Rey et al. (2024) and Nenova et al. (2025).")
    pdf.ni(2,"Discovery of the 'offsetting forces' mechanism: partial cancellation at the median, reinforcement in the tails.")
    pdf.ni(3,"First application of quantile connectedness to the FX hedging transmission chain.")
    pdf.ni(4,"Evidence that NBFI FX hedging maturity mismatch (3-month swaps / 10-year bonds) creates systemic rollover risk.")

    # ── COMMON TOOLKIT ──
    pdf.add_page()
    pdf.h1("6. Common Methodological Toolkit")
    pdf.p("All four projects share a core econometric toolkit designed to capture nonlinear, "
        "tail-specific dynamics invisible to standard methods:")
    ws2=[55,80,55]
    pdf.th(["Method","What It Captures","Used In"],ws2)
    for i,r in enumerate([
        ("Quantile Regression","Asymmetric effects across the distribution","P1, P2, P3, P4"),
        ("Quantile VAR (QVAR)","Tail-specific shock propagation","P2, P3, P4"),
        ("Quantile Connectedness","Tail spillovers between variables/countries","P1, P2, P3, P4"),
        ("Delta-CoVaR","Systemic risk contribution of channels","P1, P4"),
        ("Location-Scale GaR","Mean + variance effects on future growth","P2, P3"),
        ("DCC-GARCH","Time-varying correlations across sectors","P2"),
        ("Diebold-Yilmaz GFEVD","Directional connectedness (mean)","P2, P3"),
        ("Network / spectral","Centrality, HLI, contagion matrices","P1, P3"),
        ("Agent-based simulation","Cascade / fire-sale propagation","P1, P3, P4"),
        ("Panel FE + IV (2SLS)","Causal identification with MP shocks","P3, P4"),
    ]): pdf.tr(r,ws2,s=i%2==1)

    # ── CROSS-PROJECT LINKAGES ──
    pdf.ln(6)
    pdf.h1("7. Cross-Project Linkages")
    pdf.p("The four projects are complementary. Each addresses a distinct dimension of NBFI "
        "systemic risk, but they share data infrastructure and methodology, and findings "
        "feed into each other:")
    pdf.b("P1 (Shadow Leverage) -> P2 (MP Transmission): Implied leverage estimates serve as "
        "inputs to P2's VaR-constraint channel. Higher hidden leverage = tighter VaR constraints = amplified MP transmission.")
    pdf.b("P2 (MP Transmission) -> P3 (Cross-Border): P2 identifies which NBFI sub-sectors "
        "amplify domestic MP; P3 traces how this propagates across borders via dollar funding and portfolio flows.")
    pdf.b("P3 (Cross-Border) -> P4 (FX Hedging): P3's dollar funding channel (FX swap basis) "
        "is the same mechanism P4 models in detail. P4 adds the equity-FX link (Rey et al.) and yield curve offset (Nenova et al.).")
    pdf.b("P4 (FX Hedging) -> P1 (Shadow Leverage): FX derivatives are a major source of "
        "hidden leverage (P1), and P4 shows how hedging activity creates contagion. Together: derivatives are both a leverage source AND a contagion channel.")
    pdf.ln(3)
    pdf.box("Common finding: NBFI risks are fundamentally nonlinear. Standard mean-based\n"
        "methods miss tail amplification, asymmetric contagion, and crisis-activated\n"
        "transmission that quantile methods reveal.")

    out = "/home/user/SergioSola/reports/research_programme_outline.pdf"
    pdf.output(out)
    print(f"Saved: {out} ({pdf.page_no()} pages)")

if __name__ == "__main__":
    build()
