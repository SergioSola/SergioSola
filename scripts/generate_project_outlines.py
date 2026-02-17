"""
Generate a professional PDF report outlining all three BIS research projects.

Covers: research questions, data needs, empirical framework, and project structure
for each of the three NBFI/systemic risk research proposals.
"""

from fpdf import FPDF
from datetime import date


class ProjectReport(FPDF):
    """Custom PDF class with professional formatting."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)

    # ── Header / Footer ─────────────────────────────────────────────────
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "NBFI & Systemic Risk - Research Project Outlines", align="L")
        self.cell(0, 8, "Sergio Sola, 2026", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-20)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 10, f"Page {self.page_no() - 1}", align="C")

    # ── Title page ──────────────────────────────────────────────────────
    def title_page(self):
        self.add_page()

        # Top band
        self.set_fill_color(20, 40, 80)
        self.rect(0, 0, 210, 50, "F")
        self.set_fill_color(40, 100, 160)
        self.rect(0, 50, 210, 4, "F")

        # Title
        self.set_y(70)
        self.set_font("Helvetica", "B", 26)
        self.set_text_color(20, 40, 80)
        self.multi_cell(0, 12, "Non-Bank Financial Intermediation\nand Systemic Risk", align="C")

        self.ln(6)
        self.set_font("Helvetica", "", 16)
        self.set_text_color(40, 100, 160)
        self.cell(0, 10, "Research Project Outlines", align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(4)
        self.set_draw_color(40, 100, 160)
        self.line(60, self.get_y(), 150, self.get_y())
        self.ln(10)

        # Three project boxes
        projects = [
            ("Project 1", "The Shadow Leverage Map", "Repo & Derivatives Network Analysis"),
            ("Project 2", "Mapping the Channels", "NBFI Amplification of Monetary Policy"),
            ("Project 3", "Contagion Across Borders", "NBFI Stress & the Global Financial Cycle"),
        ]
        for label, title, subtitle in projects:
            self.set_fill_color(240, 243, 248)
            self.set_draw_color(40, 100, 160)
            x = self.get_x()
            y = self.get_y()
            self.rect(25, y, 160, 18, "FD")
            self.set_xy(30, y + 2)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(20, 40, 80)
            self.cell(30, 6, label, new_x="END")
            self.set_font("Helvetica", "B", 10)
            self.cell(0, 6, title)
            self.set_xy(60, y + 9)
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(80, 80, 80)
            self.cell(0, 6, subtitle)
            self.set_y(y + 22)

        # Author / Date
        self.ln(10)
        self.set_font("Helvetica", "", 12)
        self.set_text_color(50, 50, 50)
        self.cell(0, 8, "Sergio Sola", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 11)
        self.cell(0, 8, f"{date.today().strftime('%B %Y')}", align="C", new_x="LMARGIN", new_y="NEXT")

        # Bottom band
        self.set_fill_color(20, 40, 80)
        self.rect(0, 277, 210, 20, "F")

    # ── Helpers ─────────────────────────────────────────────────────────
    def section_heading(self, text, level=1):
        if level == 1:
            self.ln(3)
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(20, 40, 80)
            self.cell(0, 9, text, new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(40, 100, 160)
            self.line(10, self.get_y(), 100, self.get_y())
            self.ln(4)
        elif level == 2:
            self.ln(2)
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(40, 100, 160)
            self.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
            self.ln(2)
        elif level == 3:
            self.set_font("Helvetica", "BI", 10)
            self.set_text_color(60, 60, 60)
            self.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
            self.ln(1)

    def body_text(self, text):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def bullet(self, text, indent=15):
        x = self.get_x()
        self.set_x(x + indent)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(30, 30, 30)
        w = self.w - self.r_margin - self.get_x()
        self.cell(4, 5, "-")
        self.multi_cell(w - 4, 5, text)
        self.set_x(x)
        self.ln(1)

    def numbered_item(self, num, text, indent=15):
        x = self.get_x()
        self.set_x(x + indent)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(40, 100, 160)
        self.cell(8, 5, f"{num}.")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(30, 30, 30)
        w = self.w - self.r_margin - self.get_x()
        self.multi_cell(w - 8, 5, text)
        self.set_x(x)
        self.ln(1)

    def grey_box(self, text):
        self.set_fill_color(242, 244, 248)
        x, y = self.get_x(), self.get_y()
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5, text, fill=True)
        self.ln(3)

    def table_header(self, cols, widths):
        self.set_font("Helvetica", "B", 8.5)
        self.set_fill_color(20, 40, 80)
        self.set_text_color(255, 255, 255)
        for col, w in zip(cols, widths):
            self.cell(w, 7, col, border=1, align="C", fill=True)
        self.ln()

    def table_row(self, cells, widths, shade=False):
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(30, 30, 30)
        if shade:
            self.set_fill_color(245, 247, 250)
        else:
            self.set_fill_color(255, 255, 255)
        for cell, w in zip(cells, widths):
            self.cell(w, 6, cell, border=1, fill=True)
        self.ln()

    def reference(self, text):
        self.set_font("Helvetica", "", 8)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 4.5, text)
        self.ln(1)


def build_report():
    pdf = ProjectReport()

    # ════════════════════════════════════════════════════════════════════
    # TITLE PAGE
    # ════════════════════════════════════════════════════════════════════
    pdf.title_page()

    # ════════════════════════════════════════════════════════════════════
    # TABLE OF CONTENTS
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("Table of Contents")
    toc = [
        ("1.", "Executive Summary", 2),
        ("2.", "Project 1 --The Shadow Leverage Map", 3),
        ("", "2.1 Research Questions", 3),
        ("", "2.2 Data Requirements", 4),
        ("", "2.3 Empirical Framework", 5),
        ("", "2.4 Expected Contributions", 6),
        ("3.", "Project 2 --Mapping the Channels", 7),
        ("", "3.1 Research Questions", 7),
        ("", "3.2 Data Requirements", 8),
        ("", "3.3 Empirical Framework", 9),
        ("", "3.4 Expected Contributions", 10),
        ("4.", "Project 3 --Contagion Across Borders", 11),
        ("", "4.1 Research Questions", 11),
        ("", "4.2 Data Requirements", 12),
        ("", "4.3 Empirical Framework", 13),
        ("", "4.4 Expected Contributions", 14),
        ("5.", "Shared Econometric Toolkit", 15),
        ("6.", "Implementation Status & Codebase", 16),
        ("7.", "References", 17),
    ]
    for num, title, page in toc:
        pdf.set_font("Helvetica", "B" if num else "", 9.5 if num else 9)
        pdf.set_text_color(20, 40, 80)
        indent = 15 if not num else 10
        pdf.set_x(indent)
        label = f"{num} {title}" if num else f"    {title}"
        pdf.cell(0, 6, label, new_x="LMARGIN", new_y="NEXT")

    # ════════════════════════════════════════════════════════════════════
    # 1. EXECUTIVE SUMMARY
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("1. Executive Summary")

    pdf.body_text(
        "This document outlines three complementary research projects investigating the role of "
        "non-bank financial intermediaries (NBFIs) in systemic risk and financial stability. Together, "
        "they form a unified research programme that addresses key gaps identified by the BIS, FSB, "
        "and academic literature on the growing role of shadow banking in the global financial system."
    )
    pdf.body_text(
        "The projects share a common methodological foundation --combining network analysis, "
        "time-varying econometrics (DCC-GARCH), and cutting-edge tail-risk tools (quantile VARs, "
        "location-scale models, Growth-at-Risk) --but each targets a distinct policy question:"
    )

    pdf.numbered_item(1,
        "Project 1 (Shadow Leverage Map) asks: How much hidden leverage exists in the NBFI sector, "
        "and can we detect it from publicly available repo and derivatives data?"
    )
    pdf.numbered_item(2,
        "Project 2 (Mapping the Channels) asks: How do NBFIs amplify monetary policy transmission, "
        "and why was the real economy resilient despite amplified financial tightening in 2022-23? "
        "This directly extends BIS Bulletin 116 (Banerjee, Hofmann, Ng & Pinter, 2025)."
    )
    pdf.numbered_item(3,
        "Project 3 (Contagion Across Borders) asks: How does NBFI stress in one jurisdiction spill "
        "over to others via dollar funding channels, portfolio flows, and the global financial cycle?"
    )

    pdf.body_text(
        "Each project is implemented as a self-contained Jupyter notebook with full synthetic data, "
        "econometric estimation, and publication-quality visualizations, supported by a shared Python "
        "codebase. The synthetic data mirrors the structure of real data sources (OFR, DTCC, ECB, BIS IBS, "
        "FSB) to facilitate seamless transition to live data."
    )

    # ════════════════════════════════════════════════════════════════════
    # 2. PROJECT 1 --SHADOW LEVERAGE MAP
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("2. Project 1 --The Shadow Leverage Map")
    pdf.grey_box(
        "Tracing Hidden Non-Bank Exposures Through Repo and Derivatives Data"
    )

    pdf.section_heading("2.1 Research Questions", level=2)
    pdf.body_text("This project addresses three interconnected questions:")

    pdf.section_heading("Primary Research Question", level=3)
    pdf.body_text(
        "RQ1: Can we construct a reliable estimate of the hidden leverage embedded in NBFI balance "
        "sheets using publicly available market data (repo volumes, derivatives notionals, counterparty "
        "concentration metrics)?"
    )

    pdf.section_heading("Secondary Questions", level=3)
    pdf.bullet(
        "RQ2: What is the network topology of bank-NBFI exposures through repo and derivatives "
        "markets, and how has it evolved since the GFC?"
    )
    pdf.bullet(
        "RQ3: Do clusters of interconnected NBFIs create systemic exposure that individual "
        "balance sheets fail to reveal? Can we detect these 'hidden leverage clusters' from "
        "eigenvalue analysis of the exposure network?"
    )
    pdf.bullet(
        "RQ4: Does shadow leverage predict worse tail outcomes (Growth-at-Risk)? Is the relationship "
        "nonlinear --i.e., does it matter more during stress?"
    )

    pdf.section_heading("2.2 Data Requirements", level=2)

    # Data table
    cols = ["Source", "Variables", "Frequency", "Coverage"]
    widths = [35, 70, 25, 60]
    pdf.table_header(cols, widths)
    rows = [
        ("OFR US Repo", "Bilateral volumes, rates, haircuts\nby counterparty type", "Daily", "US tri-party & bilateral, 2013-present"),
        ("DTCC Derivatives", "CDS/IRS notional, counterparty\nconcentration", "Weekly", "US OTC derivatives, 2010-present"),
        ("ECB MMSR", "Secured/unsecured money\nmarket volumes & rates", "Daily", "Euro area, 2016-present"),
        ("FSB NBFI", "Sector-level assets by\njurisdiction", "Annual", "29 jurisdictions, 2002-present"),
        ("BIS Derivatives", "OTC notional outstanding by\ncounterparty sector", "Semi-ann.", "Global, 1998-present"),
    ]
    for i, (s, v, f, c) in enumerate(rows):
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(30, 30, 30)
        shade = i % 2 == 1
        if shade:
            pdf.set_fill_color(245, 247, 250)
        else:
            pdf.set_fill_color(255, 255, 255)
        y0 = pdf.get_y()
        pdf.cell(35, 12, s, border=1, fill=shade)
        pdf.cell(70, 12, v, border=1, fill=shade)
        pdf.cell(25, 12, f, border=1, fill=shade, align="C")
        pdf.cell(60, 12, c, border=1, fill=shade)
        pdf.ln()

    pdf.ln(3)
    pdf.body_text(
        "For the prototype implementation, we generate synthetic data that mirrors the structure, "
        "temporal patterns, and cross-sectional variation of these real sources, including crisis "
        "episodes (March 2020, September 2022). All synthetic data uses fixed random seeds for "
        "reproducibility."
    )

    pdf.section_heading("2.3 Empirical Framework", level=2)

    pdf.section_heading("Step 1: Implied Leverage Estimation", level=3)
    pdf.body_text(
        "We estimate implied leverage for each NBFI type from observable market data. For an entity i "
        "with estimated equity E_i, observed repo borrowing R_i, and derivative notional exposure D_i:"
    )
    pdf.grey_box(
        "    Implied_Leverage_i = (E_i + R_i + delta * D_i) / E_i\n\n"
        "where delta is a notional-to-exposure conversion factor calibrated by derivative type "
        "(CDS vs. IRS vs. FX). This extends the BIS approach of using gross notional as a "
        "leverage proxy (BIS 2025, Chapter II)."
    )

    pdf.section_heading("Step 2: Network Construction", level=3)
    pdf.body_text(
        "We build quarterly bipartite bank-NBFI networks from counterparty exposure data. "
        "Edge weights represent bilateral exposure amounts. We compute: degree/strength centrality, "
        "eigenvector centrality, betweenness, PageRank, and one-mode projections (Abad et al. 2022)."
    )

    pdf.section_heading("Step 3: Hidden Leverage Detection", level=3)
    pdf.body_text(
        "We use eigenvalue analysis of the exposure-weighted adjacency matrix. The largest eigenvalue "
        "of the bank-NBFI network tracks aggregate systemic exposure: when it rises, the system is "
        "becoming more interconnected and amplification risk increases. We also identify clusters "
        "of NBFIs whose combined leverage creates systemic risk invisible at the individual level."
    )

    pdf.section_heading("Step 4: Tail-Risk Econometrics", level=3)
    pdf.bullet(
        "Quantile connectedness (Ando et al. 2022): Compare network connectedness at tau=0.05 "
        "(left tail / stress) vs tau=0.50 (median). Higher tail connectedness = more contagion in crises."
    )
    pdf.bullet(
        "Growth-at-Risk (Adrian et al. 2019): Quantile regression of future economic outcomes on "
        "the shadow leverage index. Tests whether hidden leverage predicts worse tail outcomes."
    )
    pdf.bullet(
        "Tail risk amplification: Does the interaction of stress x shadow_leverage worsen the "
        "5th percentile of outcomes? Estimated across the full quantile spectrum."
    )
    pdf.bullet(
        "Variance ratio test: Do countries/periods with higher shadow leverage exhibit "
        "significantly more volatile outcomes?"
    )

    pdf.section_heading("2.4 Expected Contributions", level=2)
    pdf.numbered_item(1,
        "First working prototype for estimating NBFI leverage from publicly available data --"
        "addresses the key data gap identified by the FSB and BIS."
    )
    pdf.numbered_item(2,
        "A 'Shadow Leverage Index' that can serve as an early warning indicator for systemic "
        "build-up in the non-bank sector."
    )
    pdf.numbered_item(3,
        "Evidence on whether hidden leverage is a tail-risk amplifier --directly relevant "
        "for macroprudential policy calibration."
    )

    # ════════════════════════════════════════════════════════════════════
    # 3. PROJECT 2 --MAPPING THE CHANNELS
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("3. Project 2 --Mapping the Channels")
    pdf.grey_box(
        "Network Analysis of Non-Bank Amplification in Monetary Policy Transmission\n"
        "Building on BIS Bulletin 116 (Banerjee, Hofmann, Ng & Pinter, December 2025)"
    )

    pdf.section_heading("3.1 Research Questions", level=2)

    pdf.section_heading("Primary Research Question", level=3)
    pdf.body_text(
        "RQ1: Banerjee et al. (2025) show that OFIs amplify monetary policy transmission to "
        "long-term yields, financial conditions, and GDP --but with wide confidence bands and "
        "at an aggregate sector level. Can we decompose this effect: WHICH types of OFIs amplify "
        "most, THROUGH WHICH channels, and UNDER WHAT conditions?"
    )

    pdf.section_heading("Secondary Questions", level=3)
    pdf.bullet(
        "RQ2: Is amplification nonlinear? Does it intensify in the tails of the distribution "
        "(quantile VAR) or only under specific states (high leverage, low liquidity)?"
    )
    pdf.bullet(
        "RQ3 (The Puzzle): Why was the real economy resilient during the 2022-23 hiking cycle "
        "despite financial conditions tightening more than in previous cycles? Can network "
        "topology explain the containment of amplification within the financial sector?"
    )
    pdf.bullet(
        "RQ4: Does the NBFI sector affect the conditional variance (not just the mean) of "
        "economic outcomes? If so, NBFIs create fatter tails even when mean transmission "
        "appears moderate."
    )

    pdf.section_heading("Positioning Relative to Banerjee et al. (2025)", level=3)
    pdf.body_text(
        "We explicitly build on --rather than compete with --BIS Bulletin 116. Their paper "
        "establishes the aggregate fact (OFIs amplify, ICPFs dampen). We provide the micro-level "
        "decomposition that their framework cannot offer. Our value-add:"
    )
    pdf.bullet("Their approach: sector-level cross-country panels with linear local projections.")
    pdf.bullet("Our approach: entity-level network analysis + quantile methods for nonlinearity.")
    pdf.bullet("Their gap: 'considerable uncertainty about the extent of this effect remains.'")
    pdf.bullet("Our contribution: decompose that uncertainty into identifiable channels.")

    pdf.section_heading("3.2 Data Requirements", level=2)

    cols = ["Source", "Variables", "Use"]
    widths = [40, 70, 80]
    pdf.table_header(cols, widths)
    rows = [
        ("Central bank rates", "Policy rates (Fed, ECB, BoE,\nBoJ), forward guidance dates", "Monetary policy shock identification"),
        ("Financial returns", "Daily returns: banks, HFs, bond\nfunds, MMFs, insurance, pensions", "DCC-GARCH, QVAR, connectedness"),
        ("Financial conditions", "FCI (Goldman, Chicago Fed),\nVIX, credit spreads, term premium", "State variables, GaR regressions"),
        ("Balance sheet data", "NBFI leverage ratios, AUM,\nrepo borrowing by sector", "VaR-constraint model calibration"),
        ("Real economy", "GDP growth, credit growth,\ninvestment, unemployment (Q)", "Outcome variables for transmission"),
        ("FSB NBFI Monitor", "Sector assets by jurisdiction", "Cross-country NBFI penetration"),
    ]
    for i, (s, v, u) in enumerate(rows):
        shade = i % 2 == 1
        if shade:
            pdf.set_fill_color(245, 247, 250)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(40, 12, s, border=1, fill=shade)
        pdf.cell(70, 12, v, border=1, fill=shade)
        pdf.cell(80, 12, u, border=1, fill=shade)
        pdf.ln()

    pdf.ln(3)

    pdf.section_heading("3.3 Empirical Framework", level=2)
    pdf.body_text("The framework has five integrated modules, each targeting a link in the transmission chain:")

    pdf.section_heading("Module 1: VaR-Constraint Channel (Adrian & Shin 2010)", level=3)
    pdf.body_text(
        "Estimate procyclicality of leverage by sector. Run fire-sale counterfactuals comparing "
        "bank-only vs. bank+NBFI systems. Key prediction: hedge funds exhibit the highest "
        "procyclicality (beta > 1), followed by finance companies."
    )

    pdf.section_heading("Module 2: DCC-GARCH Dynamic Correlations (Engle 2002)", level=3)
    pdf.body_text(
        "Estimate time-varying correlations between bank and NBFI sector returns. Test for "
        "correlation breakdown during the hiking cycle (Forbes & Rigobon 2002 style). Track "
        "bank-HF, bank-MMF, bank-insurance correlation paths."
    )

    pdf.section_heading("Module 3: Quantile VAR [Key Innovation]", level=3)
    pdf.body_text(
        "Estimate a QVAR system [policy_rate, HF_returns, bond_fund_returns, bank_returns, FCI, "
        "GDP_growth] at tau = {0.05, 0.25, 0.50, 0.75, 0.95}. Compute quantile impulse response "
        "functions (Montes-Rojas 2019) and quantile connectedness (Ando, Greenwood-Nimmo & Shin 2022)."
    )
    pdf.grey_box(
        "Key hypothesis: At the 5th percentile (stress), the IRF of HF returns to a policy rate "
        "shock is 2-3x larger than at the median. This is the nonlinear amplification that "
        "Banerjee et al.'s linear framework cannot capture."
    )

    pdf.section_heading("Module 4: Location-Scale Growth-at-Risk", level=3)
    pdf.body_text(
        "Model both the conditional mean AND conditional variance of future GDP growth as functions "
        "of financial conditions and NBFI variables. If NBFI leverage increases the conditional "
        "variance, NBFIs create fatter tails even when mean transmission appears moderate."
    )

    pdf.section_heading("Module 5: Solving the Banerjee et al. Puzzle", level=3)
    pdf.body_text(
        "Use sector-level connectedness decomposition to show that amplification was contained "
        "within OFI clusters. The Diebold-Yilmaz network reveals high within-OFI connectedness "
        "but low OFI-to-real-economy spillovers, explaining the resilience puzzle."
    )

    pdf.section_heading("3.4 Expected Contributions", level=2)
    pdf.numbered_item(1,
        "Decomposition of the aggregate OFI amplification documented by Banerjee et al. (2025) "
        "into entity-level and channel-level components."
    )
    pdf.numbered_item(2,
        "First application of quantile connectedness (Ando et al. 2022) to monetary policy "
        "transmission --capturing nonlinear/tail dynamics."
    )
    pdf.numbered_item(3,
        "Resolution of the 2022-23 resilience puzzle through network topology analysis."
    )
    pdf.numbered_item(4,
        "Evidence that NBFIs affect the conditional variance of outcomes (location-scale), "
        "not just the conditional mean --a distinction with direct macroprudential implications."
    )

    # ════════════════════════════════════════════════════════════════════
    # 4. PROJECT 3 --CONTAGION ACROSS BORDERS
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("4. Project 3 --Contagion Across Borders")
    pdf.grey_box(
        "How NBFI Stress in One Jurisdiction Spills Over via the Global Financial Cycle"
    )

    pdf.section_heading("4.1 Research Questions", level=2)

    pdf.section_heading("Primary Research Question", level=3)
    pdf.body_text(
        "RQ1: Through which channels does NBFI stress in one jurisdiction transmit to financial "
        "conditions in other countries? Specifically, how do (a) dollar funding, (b) portfolio "
        "rebalancing, and (c) the global financial cycle interact to create cross-border contagion?"
    )

    pdf.section_heading("Secondary Questions", level=3)
    pdf.bullet(
        "RQ2: Is cross-border contagion asymmetric --stronger during stress episodes than during "
        "calm periods? (Quantile connectedness across countries.)"
    )
    pdf.bullet(
        "RQ3: Does NBFI penetration in a country increase its vulnerability to external shocks "
        "transmitted through the global financial cycle (Miranda-Agrippino & Rey 2020)?"
    )
    pdf.bullet(
        "RQ4: How does a major NBFI failure (e.g., Archegos-style event) cascade across borders? "
        "What is the role of prime brokerage concentration?"
    )
    pdf.bullet(
        "RQ5: Do NBFI-related capital flows increase the conditional variance (fat tails) of "
        "emerging market financial variables?"
    )

    pdf.section_heading("4.2 Data Requirements", level=2)

    cols = ["Source", "Variables", "Use"]
    widths = [40, 70, 80]
    pdf.table_header(cols, widths)
    rows = [
        ("BIS IBS", "Cross-border claims by\ncountry x sector (bank/NBFI)", "Exposure network construction"),
        ("BIS Derivatives", "OTC notional by counterparty\ncountry and sector", "Derivative exposure mapping"),
        ("Portfolio flows", "Gross in/outflows by investor\ntype (EPFR, IMF BoP)", "Portfolio flow channel analysis"),
        ("FX swap basis", "USD vs EUR, GBP, JPY, CHF\ncross-currency basis", "Dollar funding stress indicator"),
        ("Equity indices", "MSCI country indices\n(10+ countries)", "GFC extraction, return spillovers"),
        ("Bond yields", "10Y government bond yields\nacross countries", "Yield spillover analysis"),
        ("Fed swap lines", "Swap line usage by central\nbank counterparty", "Dollar liquidity provision"),
    ]
    for i, (s, v, u) in enumerate(rows):
        shade = i % 2 == 1
        if shade:
            pdf.set_fill_color(245, 247, 250)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(40, 12, s, border=1, fill=shade)
        pdf.cell(70, 12, v, border=1, fill=shade)
        pdf.cell(80, 12, u, border=1, fill=shade)
        pdf.ln()

    pdf.ln(3)

    pdf.section_heading("4.3 Empirical Framework", level=2)
    pdf.body_text(
        'The framework is organized around the "Triple Helix" of cross-border NBFI contagion:'
    )

    pdf.section_heading("Channel 1: Dollar Funding", level=3)
    pdf.body_text(
        "NBFIs borrow in USD via repo and FX swaps. When funding tightens (wider FX swap basis), "
        "they deleverage, creating fire-sale pressure. We estimate quantile regressions of local "
        "financial conditions on USD funding stress, interacted with the country's NBFI exposure. "
        "The relationship is expected to be nonlinear: much stronger in the left tail."
    )

    pdf.section_heading("Channel 2: Portfolio Flows", level=3)
    pdf.body_text(
        "Global investment funds rebalance portfolios across borders. NBFI flows are more volatile "
        "and procyclical than bank flows. We compute Diebold-Yilmaz connectedness on portfolio "
        "flow data to measure cross-border flow co-movement, and show NBFI flows are more connected."
    )

    pdf.section_heading("Channel 3: Global Financial Cycle", level=3)
    pdf.body_text(
        "We extract the global factor (Miranda-Agrippino & Rey 2020) from a panel of risky asset "
        "returns using PCA. Panel regressions test whether NBFI penetration amplifies GFC "
        "transmission to local credit/asset prices. IV estimation instruments the GFC with US "
        "monetary policy shocks (Bruno & Shin 2015)."
    )
    pdf.grey_box(
        "y_{c,t} = alpha_c + beta_1 * GFC_t + beta_2 * NBFI_{c,t}\n"
        "          + beta_3 * (GFC_t x NBFI_{c,t}) + gamma * X_{c,t} + epsilon_{c,t}\n\n"
        "If beta_3 is significant, NBFI penetration amplifies the global financial cycle."
    )

    pdf.section_heading("Cross-Country Quantile Connectedness [Key Innovation]", level=3)
    pdf.body_text(
        "We estimate a quantile VAR across country equity returns + USD funding at "
        "tau = {0.05, 0.50, 0.95}. Left-tail connectedness is expected to be substantially "
        "higher than median connectedness --contagion is asymmetric and activates during stress."
    )

    pdf.section_heading("Contagion Cascade Simulation", level=3)
    pdf.body_text(
        "We simulate a specific scenario: a major US hedge fund collapse. The cascade propagates "
        "through prime brokerage losses, reduced credit to other HFs, cross-border deleveraging, "
        "EME capital outflows, and currency depreciation --creating a multi-round feedback loop."
    )

    pdf.section_heading("4.4 Expected Contributions", level=2)
    pdf.numbered_item(1,
        "A complete model of the cross-border NBFI contagion network --going beyond the "
        "US-to-EME focus of Banerjee et al. (2025) to map the full bilateral structure."
    )
    pdf.numbered_item(2,
        "Evidence on asymmetric contagion: quantile connectedness reveals that cross-border "
        "spillovers are much stronger during stress (tau=0.05) than in normal times."
    )
    pdf.numbered_item(3,
        "Location-scale evidence that NBFI-related capital flows increase the conditional "
        "variance of EME financial variables --creating fatter tails."
    )
    pdf.numbered_item(4,
        "A scenario-based cascade model calibrated to the Archegos/LTCM template, showing "
        "how prime brokerage concentration creates cross-border propagation channels."
    )

    # ════════════════════════════════════════════════════════════════════
    # 5. SHARED ECONOMETRIC TOOLKIT
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("5. Shared Econometric Toolkit")
    pdf.body_text(
        "All three projects draw on a common econometric toolkit implemented in Python. "
        "The toolkit provides two main modules:"
    )

    pdf.section_heading("5.1 Quantile VAR Module (src/econometrics/quantile_var.py)", level=2)
    pdf.bullet("Quantile VAR estimation at arbitrary tau (Cecchetti & Li 2008, Montes-Rojas 2019)")
    pdf.bullet("Quantile impulse response functions (QIRFs) via companion-form representation")
    pdf.bullet("Quantile connectedness: Diebold-Yilmaz at tail quantiles (Ando et al. 2022)")
    pdf.bullet("Rolling quantile connectedness for tracking tail-risk evolution over time")
    pdf.bullet("Growth-at-Risk regressions (Adrian, Boyarchenko & Giannone 2019)")
    pdf.bullet("GaR term structure across horizons and quantiles")

    pdf.section_heading("5.2 Location-Scale Module (src/econometrics/location_scale.py)", level=2)
    pdf.bullet("Two-step location-scale: OLS for E[y|X], then OLS for log Var[y|X]")
    pdf.bullet("Conditional quantile construction from fitted location and scale")
    pdf.bullet("Skewed-t location-scale density by MLE (Hansen 1994 / Adrian et al. 2022)")
    pdf.bullet("Tail risk amplification tests: interaction effects across the quantile spectrum")
    pdf.bullet("Variance ratio tests (Levene, Brown-Forsythe) for heterogeneous volatility")
    pdf.bullet("Location-scale Growth-at-Risk with NBFI amplification channel")

    pdf.section_heading("5.3 Existing Modules (from Phase 1)", level=2)
    pdf.bullet("Network analysis: centrality, contagion matrices, bipartite projections (src/analysis/network.py)")
    pdf.bullet("Systemic risk: CoVaR, MES, SRISK, Diebold-Yilmaz connectedness (src/analysis/systemic_risk.py)")
    pdf.bullet("DCC-GARCH: dynamic correlations, sector averages, breakdown tests (src/models/dcc_garch.py)")
    pdf.bullet("VaR-constraint: procyclicality, fire-sale simulation (src/models/var_amplification.py)")
    pdf.bullet("NBFI subsectors: LDI spirals, MMF runs, prime brokerage contagion (src/models/nbfi_subsectors.py)")
    pdf.bullet("Global financial cycle: PCA, panel regressions, IV estimation (src/analysis/global_financial_cycle.py)")

    # ════════════════════════════════════════════════════════════════════
    # 6. IMPLEMENTATION STATUS
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("6. Implementation Status & Codebase")

    pdf.section_heading("Repository Structure", level=2)
    pdf.set_font("Courier", "", 8)
    pdf.set_text_color(30, 30, 30)
    tree = (
        "SergioSola/\n"
        "  src/\n"
        "    analysis/          # Network, systemic risk, GFC modules\n"
        "    models/            # DCC-GARCH, VaR-constraint, NBFI subsectors\n"
        "    econometrics/      # [NEW] Quantile VAR, location-scale\n"
        "    data/              # Data loaders and builders\n"
        "    utils/             # Configuration\n"
        "  notebooks/\n"
        "    project1_shadow_leverage/   # Project 1 notebook\n"
        "    project2_mp_transmission/   # Project 2 notebook\n"
        "    project3_cross_border/      # Project 3 notebook\n"
        "  reports/             # PDF reports\n"
        "  scripts/             # Report generation scripts\n"
        "  tests/               # Unit tests\n"
    )
    pdf.multi_cell(0, 4, tree)
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 9.5)
    pdf.section_heading("Module Summary", level=2)

    cols = ["Module", "Lines", "Key Functions", "Used By"]
    widths = [42, 15, 65, 68]
    pdf.table_header(cols, widths)
    rows = [
        ("quantile_var.py", "~380", "estimate_quantile_var, quantile_irf,\nquantile_connectedness, growth_at_risk", "P1, P2, P3"),
        ("location_scale.py", "~380", "location_scale_model, tail_risk_\namplification, skewt_fit, variance_ratio", "P1, P2, P3"),
        ("systemic_risk.py", "~470", "estimate_covar, compute_connectedness,\nrolling_connectedness, granger_network", "P1, P2, P3"),
        ("network.py", "~210", "build_exposure_network, centrality,\nbipartite_projection, contagion_matrix", "P1, P3"),
        ("dcc_garch.py", "~345", "fit_all_garch, estimate_dcc,\nsector_correlations, breakdown_test", "P2"),
        ("var_amplification.py", "~455", "procyclicality, fire_sale_simulation,\nrun_counterfactual, amplification_ratio", "P2"),
        ("global_financial_cycle.py", "~370", "extract_global_factor, panel_gfc_reg,\niv_gfc_regression, connectedness_amp", "P3"),
        ("nbfi_subsectors.py", "~550", "LDI_spiral, MMF_run, PB_contagion,\nbuild_hedge_fund_sector", "P3"),
    ]
    for i, (m, l, f, u) in enumerate(rows):
        shade = i % 2 == 1
        if shade:
            pdf.set_fill_color(245, 247, 250)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(42, 12, m, border=1, fill=shade)
        pdf.cell(15, 12, l, border=1, fill=shade, align="C")
        pdf.cell(65, 12, f, border=1, fill=shade)
        pdf.cell(68, 12, u, border=1, fill=shade, align="C")
        pdf.ln()

    # ════════════════════════════════════════════════════════════════════
    # 7. REFERENCES
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("7. References")

    refs = [
        "Abad, J., Aldasoro, I., Aymanns, C., D'Errico, M., Fache Rousova, L., Hoffmann, P., ... & Roukny, T. (2022). Mapping the interconnectedness between EU banks and shadow banking entities. Journal of Banking & Finance, 134, 106315.",
        "Adrian, T. & Brunnermeier, M. (2016). CoVaR. American Economic Review, 106(7), 1705-1741.",
        "Adrian, T., Boyarchenko, N. & Giannone, D. (2019). Vulnerable growth. American Economic Review, 109(4), 1263-1289.",
        "Adrian, T. & Shin, H.S. (2010). Financial intermediaries and monetary economics. Handbook of Monetary Economics, Vol. 3, Ch. 12.",
        "Aldasoro, I., Huang, W. & Kemp, E. (2020). Cross-border links between banks and non-bank financial institutions. BIS Quarterly Review, September.",
        "Ando, T., Greenwood-Nimmo, M. & Shin, Y. (2022). Quantile connectedness: Modeling tail behavior in the topology of financial networks. Management Science, 68(4), 2401-2431.",
        "Banerjee, R., Hofmann, B., Ng, D.X. & Pinter, G. (2025). The rise of non-bank financial institutions: implications for monetary policy. BIS Bulletin No. 116, December.",
        "Bruno, V. & Shin, H.S. (2015). Cross-border banking and global liquidity. Review of Economic Studies, 82(2), 535-564.",
        "Diebold, F.X. & Yilmaz, K. (2014). On the network topology of variance decompositions. Journal of Econometrics, 182(1), 119-134.",
        "Engle, R. (2002). Dynamic conditional correlation: A simple class of multivariate generalized autoregressive conditional heteroskedasticity models. JBES, 20(3), 339-350.",
        "Financial Stability Board (2024). Global Monitoring Report on Non-Bank Financial Intermediation. December.",
        "Miranda-Agrippino, S. & Rey, H. (2020). US monetary policy and the global financial cycle. Review of Economic Studies, 87(6), 2754-2776.",
        "Montes-Rojas, G. (2019). Multivariate quantile impulse response functions. JBES, 37(4), 546-555.",
        "Rey, H. (2013). Dilemma not trilemma: The global financial cycle and monetary policy independence. Proceedings of the Federal Reserve Bank of Kansas City Jackson Hole Symposium.",
    ]
    for ref in refs:
        pdf.reference(ref)

    # ── Save ────────────────────────────────────────────────────────────
    output = "/home/user/SergioSola/reports/project_outlines.pdf"
    pdf.output(output)
    print(f"Report saved to: {output}")
    print(f"Pages: {pdf.page_no()}")
    return output


if __name__ == "__main__":
    build_report()
