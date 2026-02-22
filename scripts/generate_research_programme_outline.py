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

    pdf.h2("Data Sources & Sample")
    ws_d1=[45,55,25,65]
    pdf.th(["Source","Variables","Freq.","Coverage"],ws_d1)
    for i,r in enumerate([
        ("OFR US Repo (SOFR)","Repo volumes, rates, counterparty","Daily","2014-present"),
        ("ECB MMSR","Euro repo volumes by counterparty","Daily","2016-present"),
        ("DTCC Swap Data","IRS/CDS notional, counterparty type","Weekly","2013-present"),
        ("FSB Global Monitoring","NBFI sector AUM, leverage proxies","Annual","2002-present"),
        ("BIS Locational Banking","Cross-border bank-NBFI exposures","Quarterly","2000-present"),
        ("FRED / ECB SDW","GDP, financial conditions, VIX, spreads","Mixed","2000-present"),
    ]): pdf.tr(r,ws_d1,s=i%2==1)
    pdf.ln(2)
    pdf.p("Sample period: 2013Q1-2024Q4 (post-DTCC reporting). Extended to 2000 for GaR regressions "
        "using FSB annual data. Key stress episodes for validation: Taper Tantrum (May 2013), "
        "China devaluation (Aug 2015), Gilt crisis (Sep 2022), COVID-19 (Mar 2020), SVB (Mar 2023).")

    pdf.h2("Literature Positioning")
    pdf.ni(1,"NBFI leverage measurement: Extends Jiang, Matvos, Piskorski & Seru (2024) on hidden bank losses to the NBFI sector. Complements FSB (2023) Global Monitoring with market-data approach.")
    pdf.ni(2,"Spectral network measures: Builds on Acemoglu et al. (2015) and Greenwood, Landier & Thesmar (2015). Adapts spectral radius to bipartite bank-NBFI setting.")
    pdf.ni(3,"Growth-at-Risk: Extends Adrian et al. (2019) by adding NBFI-specific predictors (hidden leverage) to financial conditions -> GDP GaR framework.")

    pdf.h2("Identification & Robustness")
    pdf.b("Endogeneity of leverage: lagged HLI values, Granger causality, IV with regulatory threshold dummies (margin call triggers).")
    pdf.b("Measurement error: delta-equivalence factor calibrated from BIS survey; robustness across delta in [0.02, 0.10].")
    pdf.b("Network construction sensitivity: tested across alternative edge-weighting (gross vs net, bilateral vs multilateral netting).")

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
    pdf.p("Economic logic: VaR-constrained intermediaries expand balance sheets when asset prices "
        "rise (measured risk falls, creating unused capacity) and contract when prices fall (VaR "
        "breached, forcing asset sales). This makes leverage procyclical -- rising with assets in "
        "booms, falling in busts -- and generates fire-sale spirals. Adrian & Shin (2010, 2014) "
        "document this for US broker-dealers. We extend it to the full NBFI universe.")
    pdf.p("What we test: (1) Is leverage procyclical for each NBFI sub-sector, and is the "
        "procyclicality coefficient larger for leveraged sub-sectors (HFs) than liability-driven "
        "ones (pensions)? (2) Does adding NBFIs to a fire-sale simulation amplify losses?")
    pdf.h3("Specification 1: Procyclicality panel")
    pdf.box("    D log(Lev_{s,t}) = alpha_s + beta_s * D log(A_{s,t}) + gamma * X_{s,t-1} + delta_t + eps\n\n"
        "Unit of observation: NBFI sub-sector s in quarter t.\n\n"
        "Variables:\n"
        "  Lev_{s,t} = A_{s,t} / E_{s,t}  (total assets / equity, from Flow of Funds Z.1)\n"
        "  A_{s,t}   = total assets of sub-sector s at quarter t\n"
        "  X_{s,t-1} = lagged controls: VIX, term spread (10Y-2Y), credit spread, GDP growth\n"
        "  alpha_s   = sub-sector fixed effects (absorb business model differences)\n"
        "  delta_t   = time fixed effects (absorb common macro shocks)\n"
        "  beta_s    = sub-sector-specific procyclicality coefficient (key parameter)\n\n"
        "Expected ranking (H1): beta_HF > beta_LevFunds > beta_BondMF > beta_MMF > beta_IC ~ beta_PF ~ 0")
    pdf.h3("Specification 2: Stress interaction")
    pdf.box("    D log(Lev_{s,t}) = alpha_s + beta_1 * D log(A_{s,t})\n"
        "                        + beta_2 * D log(A_{s,t}) x Stress_t\n"
        "                        + gamma * X_{s,t-1} + delta_t + eps\n\n"
        "Stress_t = dummy (VIX > 75th pctile or NBER recession).\n"
        "If beta_2 > 0: procyclicality intensifies during stress.")
    pdf.h3("Specification 3: Fire-sale simulation")
    pdf.p("Greenwood, Landier & Thesmar (2015) model extended to include NBFI sub-sectors:")
    pdf.b("Initial shock: -5% across all asset classes.")
    pdf.b("Mark-to-market losses proportional to portfolio weights and leverage.")
    pdf.b("Forced selling: sectors with beta_s > 0 sell to restore target leverage.")
    pdf.b("Price impact: Kyle (1985) lambda. Iterate until convergence (< 0.01%).")
    pdf.b("Amplification ratio = Total losses (bank+NBFI) / Total losses (bank-only).")
    pdf.p("Standard errors: clustered at sub-sector level (9 clusters). "
        "Robustness: two-way clustering (sub-sector x year).")
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

    pdf.h2("Data Sources & Sample")
    ws_d2=[45,55,25,65]
    pdf.th(["Source","Variables","Freq.","Coverage"],ws_d2)
    for i,r in enumerate([
        ("Flow of Funds (Fed Z.1)","Sector assets, liabilities, leverage","Quarterly","1980-present"),
        ("ECB Inv. Fund Stats","EU fund AUM, flows, leverage by type","Quarterly","2009-present"),
        ("EPFR Global","Fund flows by type, country, asset class","Monthly","2000-present"),
        ("Bloomberg / Refinitiv","Sector return indices (HF, MMF, etc.)","Daily","2000-present"),
        ("BIS Credit Statistics","Credit to private sector, spreads","Quarterly","1999-present"),
        ("FRED","Fed funds rate, term spreads, GDP, CPI","Mixed","1960-present"),
        ("Banerjee et al. (2025)","BIS Bulletin 116 replication data","Quarterly","2000-2024"),
    ]): pdf.tr(r,ws_d2,s=i%2==1)
    pdf.ln(2)
    pdf.p("Sample: 2000Q1-2024Q4 for most modules. DCC-GARCH uses daily data. Sub-sector classification: "
        "hedge funds, MMFs, bond mutual funds, equity mutual funds, ETFs, insurance, pension funds, "
        "finance companies, securitisation vehicles.")

    pdf.h2("Literature Positioning")
    pdf.ni(1,"MP & financial intermediaries: Extends Adrian & Shin (2010, 2014) VaR-constraint channel from banks to NBFIs.")
    pdf.ni(2,"NBFI amplification: Builds on Banerjee et al. (2025). Sub-sector decomposition and quantile methods address their wide confidence bands.")
    pdf.ni(3,"Quantile VAR: Adapts Ando et al. (2022) from cross-country to cross-sector. First quantile connectedness for MP transmission.")
    pdf.ni(4,"Location-scale: Extends Adrian et al. (2019) GaR by modelling the scale (variance) channel separately.")

    pdf.h2("Identification & Robustness")
    pdf.b("MP shock identification: high-frequency (Gurkaynak et al. 2005); robustness with Romer & Romer (2004), Jarocinski & Karadi (2020).")
    pdf.b("NBFI leverage endogeneity: instrumented with lagged regulatory capital ratios of connected banks.")
    pdf.b("Quantile VAR lag selection: BIC-optimal at each quantile; robustness across p in {1, 2, 4}.")
    pdf.b("Small-sample inference: bootstrap CIs (1000 replications) for quantile IRFs and connectedness.")

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

    pdf.h2("Data Sources & Sample")
    ws_d3=[45,55,25,65]
    pdf.th(["Source","Variables","Freq.","Coverage"],ws_d3)
    for i,r in enumerate([
        ("BIS Locational Banking","Cross-border claims by sector/country","Quarterly","2000-present"),
        ("EPFR Global","Cross-border fund flows by destination","Monthly","2005-present"),
        ("IMF CPIS","Portfolio positions by country pair","Annual","2001-present"),
        ("BIS OTC Derivatives","FX swap/forward by currency","Semiannual","2004-present"),
        ("Bloomberg","CIP basis, VIX, equity indices","Daily","2000-present"),
        ("Miranda-Agrippino & Rey","Global Financial Cycle factor","Monthly","1990-present"),
        ("FSB Global Monitoring","NBFI penetration ratio by country","Annual","2002-present"),
    ]): pdf.tr(r,ws_d3,s=i%2==1)
    pdf.ln(2)
    pdf.p("Sample: 2005Q1-2024Q4 for cross-country quantile connectedness. Country coverage: G20 + "
        "financial centres (US, UK, EA, JP, CH, AU, CA, KR, SG, HK, BR, MX, IN, ZA, TR, RU, CN). "
        "Separate EME sub-sample for GFC amplification tests.")

    pdf.h2("Literature Positioning")
    pdf.ni(1,"Global financial cycle: Extends Rey (2013), Miranda-Agrippino & Rey (2020). First causal evidence of NBFI amplification of GFC via IV.")
    pdf.ni(2,"Cross-border contagion: Complements Forbes & Warnock (2012), Broner et al. (2013). Adds NBFI decomposition and quantile methods.")
    pdf.ni(3,"Dollar funding: Builds on Avdjiev et al. (2019), Eguren-Martin et al. (2024). Tests nonlinear transmission via quantile regression.")
    pdf.ni(4,"Network contagion: Eisenberg & Noe (2001) + Kyle (1985) price impact, extending Cont & Schaanning (2017) to cross-border setting.")

    pdf.h2("Identification & Robustness")
    pdf.b("IV for GFC factor: US MP shocks (Jarocinski & Karadi 2020), addressing reverse causality.")
    pdf.b("NBFI penetration endogeneity: instrumented with legal origin (La Porta et al. 1998) and lagged pension reform dummies.")
    pdf.b("Alternative connectedness: Barunik & Krehlik (2018) frequency-domain as robustness check.")
    pdf.b("EME vs AE heterogeneity: full interaction models allowing different coefficients.")

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

    pdf.h2("Data Sources & Sample")
    ws_d4=[45,55,25,65]
    pdf.th(["Source","Variables","Freq.","Coverage"],ws_d4)
    for i,r in enumerate([
        ("BIS OTC Derivatives","FX swap/forward by currency & sector","Semiannual","2004-present"),
        ("Bloomberg","Cross-currency basis (3M,1Y,5Y), equities","Daily","2000-present"),
        ("Refinitiv","Govt bond yields (2Y,5Y,10Y), 20+ countries","Daily","2000-present"),
        ("EPFR Global","Cross-border bond fund flows by country","Monthly","2005-present"),
        ("IMF CPIS","Cross-border bond holdings by pair","Annual","2001-present"),
        ("Rey et al. (2024)","Currency centrality, replication data","Monthly","1999-2023"),
        ("Nenova et al. (2025)","FX derivatives & NBFI hedging data","Quarterly","2010-2024"),
    ]): pdf.tr(r,ws_d4,s=i%2==1)
    pdf.ln(2)
    pdf.p("Sample: 2005M1-2024M12 for quantile regressions. Currency pairs: G10 majors (USD/EUR, "
        "USD/JPY, USD/GBP, USD/AUD, USD/CAD, USD/CHF) + key EME pairs (USD/KRW, USD/MXN, "
        "USD/BRL, USD/ZAR) with liquid CIP basis data.")

    pdf.h2("Literature Positioning")
    pdf.ni(1,"FX hedging & stability: Integrates Rey et al. (2024) on equity-FX transmission and Nenova et al. (2025) on NBFI hedging. 'Offsetting forces' is our key theoretical contribution.")
    pdf.ni(2,"CIP deviations: Extends Du et al. (2018), Avdjiev et al. (2019). CIP deviations as systemic risk channel, not just anomaly.")
    pdf.ni(3,"Delta-CoVaR: Applies Adrian & Brunnermeier (2016) to a transmission mechanism rather than an institution -- methodological novelty.")
    pdf.ni(4,"Maturity mismatch: Builds on Brunnermeier et al. (2009). NBFI hedging mismatch (3M swaps for 10Y bonds) analogous to bank maturity mismatch.")

    pdf.h2("Identification & Robustness")
    pdf.b("Offsetting forces: Wald test of beta_4(tau=0.05) = beta_4(tau=0.50) with bootstrap p-values.")
    pdf.b("CIP basis endogeneity: instrumented with central bank swap line announcements (exogenous supply shocks).")
    pdf.b("Hedging demand proxy: NBFI cross-border bond holdings (CPIS) x average hedge ratio (BIS survey).")
    pdf.b("Alternative stress measures: robust to MOVE, TED spread, financial conditions indices replacing VIX.")

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

    # ── TIMELINE & DELIVERABLES ──
    pdf.add_page()
    pdf.h1("8. Timeline & Deliverables")
    ws_t=[30,30,35,95]
    pdf.th(["Phase","Period","Projects","Deliverables"],ws_t)
    pdf.tr(("Phase 1","Q1-Q2 2026","P1 + P2","Working papers; implied leverage dataset; QVAR estimates"),ws_t)
    pdf.tr(("Phase 2","Q3-Q4 2026","P3 + P4","Working papers; cross-country connectedness; offsetting forces"),ws_t,s=True)
    pdf.tr(("Phase 3","Q1 2027","Integration","Synthesis paper linking all projects; unified policy brief"),ws_t)
    pdf.tr(("Ongoing","Throughout","All","Conference presentations, seminar feedback, revisions"),ws_t,s=True)
    pdf.ln(2)
    pdf.p("Sequencing rationale: P1 and P2 proceed in parallel (different data, complementary methods). "
        "P3 and P4 benefit from P1/P2 outputs but can begin data assembly immediately. The integration "
        "phase produces the synthesis tying all four dimensions together.")

    # ── POLICY IMPLICATIONS ──
    pdf.h1("9. Policy Implications")
    pdf.p("The research programme speaks directly to ongoing regulatory debates:")
    pdf.ni(1,"NBFI leverage monitoring (P1): The implied leverage measure and HLI provide regulators "
        "with a prototype tool complementing FSB surveillance. Could inform NBFI leverage reporting "
        "requirements under the FSB 2023 NBFI roadmap.")
    pdf.ni(2,"Monetary policy & financial stability (P2): Evidence that NBFI leverage amplifies MP "
        "transmission in the tails has implications for calibrating tightening cycles. The 2022-23 "
        "resilience finding suggests post-GFC bank regulation worked but created new NBFI vulnerabilities.")
    pdf.ni(3,"Cross-border macroprudential coordination (P3): NBFI penetration amplifies GFC "
        "transmission, supporting arguments for cross-border macroprudential coordination (e.g., "
        "reciprocity of countercyclical capital buffers for NBFI exposures).")
    pdf.ni(4,"FX derivatives regulation (P4): NBFI hedging maturity mismatch (3-month swaps for "
        "10-year bonds) creates systemic rollover risk. Supports longer-tenor hedging requirements "
        "or margin buffers calibrated to stress scenarios.")
    pdf.ni(5,"Data gaps (all): All projects highlight inadequate NBFI data. Supports FSB/BIS "
        "initiatives for enhanced reporting on leverage, counterparty exposures, and cross-border linkages.")

    # ── REFERENCES ──
    pdf.add_page()
    pdf.h1("10. References (Selected)")
    refs = [
        "Acemoglu, D., Ozdaglar, A. & Tahbaz-Salehi, A. (2015). Systemic risk and stability in financial networks. AER 105(2), 564-608.",
        "Adrian, T. & Brunnermeier, M.K. (2016). CoVaR. AER 106(7), 1705-1741.",
        "Adrian, T., Boyarchenko, N. & Giannone, D. (2019). Vulnerable growth. AER 109(4), 1263-1289.",
        "Adrian, T. & Shin, H.S. (2010). Liquidity and leverage. J. Financial Intermediation 19(3), 418-437.",
        "Ando, T., Greenwood-Nimmo, M. & Shin, Y. (2022). Quantile connectedness. Management Science 68(4), 2401-2431.",
        "Avdjiev, S., Du, W., Koch, C. & Shin, H.S. (2019). The dollar, bank leverage, and CIP deviations. AER: Insights 1(2), 193-208.",
        "Banerjee, R., Hofmann, B., Ng, A. & Pinter, J. (2025). Non-bank financial intermediaries and financial stability. BIS Bulletin 116.",
        "Du, W., Tepper, A. & Verdelhan, A. (2018). Deviations from CIP. J. Finance 73(3), 915-957.",
        "Eisenberg, L. & Noe, T.H. (2001). Systemic risk in financial systems. Management Science 47(2), 236-249.",
        "Forbes, K.J. & Warnock, F.E. (2012). Capital flow waves. J. International Economics 88(2), 235-251.",
        "Greenwood, R., Landier, A. & Thesmar, D. (2015). Vulnerable banks. JFE 115(3), 471-485.",
        "Miranda-Agrippino, S. & Rey, H. (2020). US monetary policy and the global financial cycle. REStud 87(6), 2754-2776.",
        "Nenova, T., Schrimpf, A. & Shin, H.S. (2025). FX derivatives and NBFI hedging. BIS Working Paper.",
        "Rey, H. (2013). Dilemma not trilemma. Jackson Hole Symposium.",
        "Rey, H., Stavrakeva, V. & Tang, J. (2024). Currency centrality and the exchange rate channel. Working Paper.",
    ]
    for ref in refs:
        pdf.b(ref, indent=10)

    out = "/home/user/SergioSola/reports/research_programme_outline.pdf"
    pdf.output(out)
    print(f"Saved: {out} ({pdf.page_no()} pages)")

if __name__ == "__main__":
    build()
