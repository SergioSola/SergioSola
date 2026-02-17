"""
Generate a standalone PDF outline for Project 4:
FX Hedging as a Contagion Channel.

Follows the same professional formatting as generate_project_outlines.py.
"""

from fpdf import FPDF
from datetime import date


class Project4Report(FPDF):
    """Custom PDF class with professional formatting."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "Project 4 - FX Hedging as a Contagion Channel", align="L")
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
        self.set_y(65)
        self.set_font("Helvetica", "B", 24)
        self.set_text_color(20, 40, 80)
        self.multi_cell(
            0, 11,
            "FX Hedging as a\nContagion Channel",
            align="C",
        )

        self.ln(4)
        self.set_font("Helvetica", "", 15)
        self.set_text_color(40, 100, 160)
        self.multi_cell(
            0, 8,
            "How NBFI Currency Risk Management\nTransmits Global Financial Shocks",
            align="C",
        )

        self.ln(4)
        self.set_draw_color(40, 100, 160)
        self.line(55, self.get_y(), 155, self.get_y())
        self.ln(8)

        # Project label box
        self.set_fill_color(240, 243, 248)
        self.set_draw_color(40, 100, 160)
        y = self.get_y()
        self.rect(25, y, 160, 18, "FD")
        self.set_xy(30, y + 2)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(20, 40, 80)
        self.cell(30, 6, "Project 4", new_x="END")
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 6, "FX Hedging Amplification Channel")
        self.set_xy(60, y + 9)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(80, 80, 80)
        self.cell(0, 6, "Combining Rey et al. (2024) and Nenova, Schrimpf & Shin (2025)")
        self.set_y(y + 25)

        # Key references box
        self.ln(4)
        self.set_fill_color(245, 248, 252)
        self.set_draw_color(40, 100, 160)
        y2 = self.get_y()
        self.rect(25, y2, 160, 32, "FD")
        self.set_xy(30, y2 + 2)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(20, 40, 80)
        self.cell(0, 5, "Key References:")
        self.set_xy(30, y2 + 8)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(50, 50, 50)
        self.multi_cell(
            150, 4,
            "Rey, Stavrakeva & Tang (2024). Currency centrality in equity markets. NBER WP 33003.\n"
            "Nenova, Schrimpf & Shin (2025). Global portfolio investments and FX derivatives. BIS WP 1273.\n"
            "Ando, Greenwood-Nimmo & Shin (2022). Quantile connectedness. Management Science.",
        )
        self.set_y(y2 + 38)

        # Author / Date
        self.ln(6)
        self.set_font("Helvetica", "", 12)
        self.set_text_color(50, 50, 50)
        self.cell(0, 8, "Sergio Sola", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 11)
        self.cell(
            0, 8, f"{date.today().strftime('%B %Y')}",
            align="C", new_x="LMARGIN", new_y="NEXT",
        )

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
    pdf = Project4Report()

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
        ("1.", "Motivation & Research Gap", 2),
        ("2.", "Research Questions", 3),
        ("3.", "The Economic Mechanism", 4),
        ("", "3.1 Transmission Chain", 4),
        ("", "3.2 The Offsetting Forces Hypothesis", 5),
        ("4.", "Data Requirements", 6),
        ("5.", "Empirical Framework", 7),
        ("", "5.1 Layer 1: Quantile Regression", 7),
        ("", "5.2 Layer 2: Delta-CoVaR", 8),
        ("", "5.3 Layer 3: Quantile Connectedness", 8),
        ("", "5.4 NBFI Penetration Regressions", 9),
        ("", "5.5 IV Estimation", 9),
        ("6.", "Expected Contributions", 10),
        ("7.", "References", 11),
    ]
    for num, title, page in toc:
        pdf.set_font("Helvetica", "B" if num else "", 9.5 if num else 9)
        pdf.set_text_color(20, 40, 80)
        indent = 15 if not num else 10
        pdf.set_x(indent)
        label = f"{num} {title}" if num else f"    {title}"
        pdf.cell(0, 6, label, new_x="LMARGIN", new_y="NEXT")

    # ════════════════════════════════════════════════════════════════════
    # 1. MOTIVATION
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("1. Motivation & Research Gap")

    pdf.body_text(
        "The global FX derivatives market has grown to $75 trillion in outstanding notional "
        "(BIS OTC statistics, end-2024), driven primarily by non-bank financial intermediaries "
        "(NBFIs) -- investment funds, pension funds, and insurance companies -- hedging "
        "cross-border bond investments. This growth has created a powerful but underappreciated "
        "channel for the international transmission of financial shocks."
    )
    pdf.body_text(
        "Two recent papers illuminate complementary pieces of this mechanism. Rey, Stavrakeva & "
        "Tang (2024) show that equity market shocks drive exchange rate movements through a "
        "'currency centrality' network, explaining 95% of monthly FX variation vs the USD. "
        "Nenova, Schrimpf & Shin (2025) show that FX swap volumes are a barometer of NBFI "
        "risk-taking, with yield curve slopes determining hedging demand and costs."
    )
    pdf.body_text(
        "This project combines both frameworks to identify a complete contagion channel: "
        "equity shocks move exchange rates (Rey et al.), which alter FX hedging costs for "
        "NBFIs (Nenova et al.), triggering portfolio adjustments that feed back to asset "
        "prices. Crucially, we show this channel exhibits tail asymmetry -- it self-stabilizes "
        "in normal times but amplifies during stress."
    )

    pdf.section_heading("Research Gap", level=2)
    pdf.bullet(
        "Rey et al. (2024) focus on equity-FX transmission but do not trace the effect "
        "through to hedging costs and bond flows."
    )
    pdf.bullet(
        "Nenova et al. (2025) study FX swap activity and yield curves but use OLS/linear "
        "methods that cannot capture tail amplification."
    )
    pdf.bullet(
        "No existing work applies quantile methods (quantile connectedness, Delta-CoVaR) "
        "to the equity-FX-hedging-bonds transmission chain."
    )
    pdf.bullet(
        "The offsetting forces hypothesis (yield curve vs FX effects on hedging costs) "
        "has not been formally tested across the quantile spectrum."
    )

    # ════════════════════════════════════════════════════════════════════
    # 2. RESEARCH QUESTIONS
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("2. Research Questions")

    pdf.section_heading("Primary Research Question", level=3)
    pdf.body_text(
        "RQ1: Does the FX hedging activity of NBFIs constitute a contagion channel that "
        "transmits equity market shocks to cross-border bond flows? Specifically, does "
        "the transmission chain (equity shocks -> FX movements -> hedging cost changes -> "
        "bond flow reversals -> feedback) exhibit tail asymmetry -- self-stabilizing at "
        "the median but amplifying in the tails?"
    )

    pdf.section_heading("Secondary Questions", level=3)
    pdf.bullet(
        "RQ2: Do yield curve movements offset FX-driven hedging cost changes in normal times, "
        "and does this offset break down during stress? (Quantile regression test.)"
    )
    pdf.bullet(
        "RQ3: What is the systemic risk contribution of the FX hedging channel? How much does "
        "the tail risk of cross-border bond flows increase when hedging conditions deteriorate? "
        "(Delta-CoVaR framework.)"
    )
    pdf.bullet(
        "RQ4: Is the FX hedging transmission chain dormant in normal times but active during "
        "stress? (Quantile connectedness comparison: tau=0.05 vs tau=0.50.)"
    )
    pdf.bullet(
        "RQ5: Does NBFI penetration in a country amplify its vulnerability to FX hedging "
        "cost shocks? (Panel regression with NBFI interaction, IV with MP shocks.)"
    )
    pdf.bullet(
        "RQ6: Are spillovers bi-directional? Do European/Japanese NBFIs investing in US "
        "Treasuries on a hedged basis create reverse spillovers to the US?"
    )

    # ════════════════════════════════════════════════════════════════════
    # 3. THE ECONOMIC MECHANISM
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("3. The Economic Mechanism")

    pdf.section_heading("3.1 Transmission Chain", level=2)
    pdf.body_text("The contagion operates through six sequential steps:")

    pdf.numbered_item(1,
        "Shock hits equity markets (e.g., US rate hike, risk-off event, geopolitical shock)."
    )
    pdf.numbered_item(2,
        "Exchange rates move: The USD appreciates as foreign investors rebalance toward US "
        "equities (Rey, Stavrakeva & Tang 2024 -- 'currency centrality' mechanism). The USD "
        "plays a uniquely central role in this network."
    )
    pdf.numbered_item(3,
        "FX hedging costs spike: CIP deviations widen as the FX swap basis blows out. "
        "NBFIs using short-term FX swaps to hedge long-term bond positions face rollover "
        "risk (Nenova, Schrimpf & Shin 2025)."
    )
    pdf.numbered_item(4,
        "NBFIs deleverage: Faced with higher hedging costs and potential margin calls on "
        "FX derivatives, NBFIs reduce hedged cross-border bond positions."
    )
    pdf.numbered_item(5,
        "Bond sell-off: Cross-border bond outflows push up yields in the destination country, "
        "further widening the CIP basis and tightening financial conditions."
    )
    pdf.numbered_item(6,
        "Feedback: Higher yields and wider spreads feed back to equity markets, restarting "
        "the cycle with geometric dampening."
    )

    pdf.section_heading("3.2 The Offsetting Forces Hypothesis", level=2)
    pdf.body_text(
        "A critical insight is that equity shocks and yield curve movements create opposing "
        "forces on FX hedging costs in normal times:"
    )

    cols = ["Force", "Normal Times", "Stress"]
    widths = [50, 65, 75]
    pdf.table_header(cols, widths)
    rows = [
        ("Equity -> FX\n(Rey et al.)", "USD appreciates\nmoderately", "USD appreciates\nviolently (safe haven)"),
        ("Yield curve\n(Nenova et al.)", "Steepens -> attractive\nhedged carry", "Flattens/inverts ->\ncarry disappears"),
        ("CIP deviations", "Small -> manageable\nhedging cost", "Blow out -> prohibitive\nhedging cost"),
        ("Net effect", "Partially offsetting\n-> self-stabilizing", "All reinforcing\n-> amplification"),
    ]
    for i, (f, n, s) in enumerate(rows):
        shade = i % 2 == 1
        if shade:
            pdf.set_fill_color(245, 247, 250)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(50, 12, f, border=1, fill=shade)
        pdf.cell(65, 12, n, border=1, fill=shade)
        pdf.cell(75, 12, s, border=1, fill=shade)
        pdf.ln()

    pdf.ln(3)
    pdf.grey_box(
        "Key prediction: The interaction term (equity_return x VIX) in a quantile "
        "regression of CIP basis is insignificant at the median but large and significant "
        "in the tails. This is the formal test of tail amplification."
    )

    # ════════════════════════════════════════════════════════════════════
    # 4. DATA REQUIREMENTS
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("4. Data Requirements")

    cols = ["Source", "Variables", "Use"]
    widths = [40, 70, 80]
    pdf.table_header(cols, widths)
    rows = [
        ("Bloomberg / Refinitiv", "Cross-currency basis\n(EUR, GBP, JPY, CHF, AUD vs USD)", "CIP deviations / hedging costs"),
        ("FRED / ECB / BoJ", "Yield curve slopes\n(10Y - 2Y) by economy", "Hedging demand determinants"),
        ("MSCI / S&P", "Equity index returns\n(US + foreign)", "Equity shock identification"),
        ("TIC (US Treasury)", "Cross-border bond flows\nby investor type", "Portfolio flow channel"),
        ("BIS OTC Derivatives", "FX swap outstanding\nby counterparty sector", "NBFI hedging volume proxy"),
        ("FSB NBFI Monitor", "Sector-level assets\nby jurisdiction", "NBFI penetration variable"),
        ("CBOE", "VIX", "Global risk appetite"),
        ("High-frequency MP", "Gurkaynak et al. shocks,\nKearns et al. (2023)", "IV for yield curves / CIP"),
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
    pdf.body_text(
        "For the prototype implementation, we generate synthetic data that mirrors the "
        "structure, temporal patterns, and cross-sectional variation of these real sources. "
        "The synthetic DGP embeds the tail asymmetry mechanism to validate the econometric "
        "approach. All synthetic data uses fixed random seeds for reproducibility."
    )

    # ════════════════════════════════════════════════════════════════════
    # 5. EMPIRICAL FRAMEWORK
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("5. Empirical Framework")
    pdf.body_text(
        "The framework has three integrated empirical layers, each targeting a different "
        "aspect of the FX hedging contagion channel, plus panel regressions and IV estimation."
    )

    pdf.section_heading("5.1 Layer 1: Quantile Regression -- Offsetting Forces Test", level=2)
    pdf.body_text("Quantile regression of CIP basis on equity returns, yield slopes, and VIX:")
    pdf.grey_box(
        "    Q_tau(CIP_basis_t) = alpha + beta_1 * Equity_t + beta_2 * SlopeDiff_t\n"
        "                         + beta_3 * VIX_t + beta_4 * (Equity_t x VIX_t) + epsilon_t\n\n"
        "Estimated at tau = {0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95}.\n\n"
        "Key test: beta_4 (interaction) is small at the median but large in the tails."
    )
    pdf.bullet(
        "Formal asymmetry test: Wald test of H0: beta_4(tau=0.05) = beta_4(tau=0.50)."
    )
    pdf.bullet(
        "Coefficient profile plots across the full quantile spectrum, with 95% confidence bands."
    )
    pdf.bullet(
        "Cross-currency comparison to test robustness (EUR, GBP, JPY, CHF, AUD vs USD)."
    )

    pdf.section_heading("5.2 Layer 2: Delta-CoVaR (Adrian & Brunnermeier 2016)", level=2)
    pdf.body_text(
        "Estimate the systemic risk contribution of the FX hedging channel:"
    )
    pdf.grey_box(
        "    Delta-CoVaR = CoVaR(bond_flows | CIP_basis = stressed)\n"
        "                 - CoVaR(bond_flows | CIP_basis = median)\n\n"
        "A large negative Delta-CoVaR means FX hedging stress significantly amplifies\n"
        "the tail risk of cross-border bond flows."
    )
    pdf.bullet(
        "Step 1: Estimate VaR of CIP basis using quantile regression on VIX and equity returns."
    )
    pdf.bullet(
        "Step 2: Estimate CoVaR of bond flows conditioned on CIP basis, VIX, and equity returns."
    )
    pdf.bullet(
        "Step 3: Compute Delta-CoVaR as difference between stressed and normal conditions."
    )

    pdf.section_heading("5.3 Layer 3: Quantile Connectedness [Key Innovation]", level=2)
    pdf.body_text(
        "Apply the Ando, Greenwood-Nimmo & Shin (2022) quantile connectedness framework "
        "to the 4-variable system:"
    )
    pdf.grey_box(
        "    System: {US equity return, FX return, CIP basis, Bond flows}\n"
        "    Estimated at tau = {0.05, 0.50, 0.95}\n\n"
        "Generalized FEVD from QVAR yields quantile-specific connectedness.\n"
        "Key prediction: Total connectedness at tau=0.05 >> tau=0.50."
    )
    pdf.bullet(
        "FEVD heatmaps at each quantile showing directional spillovers."
    )
    pdf.bullet(
        "Cross-currency comparison of tail vs median connectedness."
    )
    pdf.bullet(
        "Rolling quantile connectedness to track time-varying tail spillovers."
    )

    pdf.section_heading("5.4 NBFI Penetration Panel Regressions", level=2)
    pdf.grey_box(
        "    bond_flows_{c,t} = alpha_c + beta_1 * CIP_basis_{c,t}\n"
        "                       + beta_2 * NBFI_{c,t}\n"
        "                       + beta_3 * (CIP_{c,t} x NBFI_{c,t})\n"
        "                       + gamma * X_{c,t} + epsilon_{c,t}\n\n"
        "If beta_3 < 0: higher NBFI penetration amplifies the negative effect of\n"
        "hedging cost shocks on cross-border bond flows."
    )

    pdf.section_heading("5.5 IV Estimation", level=2)
    pdf.body_text(
        "Instrument CIP basis / yield curve slopes with high-frequency monetary policy shocks "
        "(Gurkaynak et al. 2005, Kearns et al. 2023, Jarocinski 2024) and monetary "
        "policy-induced 'risk shifts' (Kroencke et al. 2021, Bauer et al. 2023). This follows "
        "Nenova et al. (2025) who use these instruments to identify causal effects of "
        "central bank announcements on FX hedging demand."
    )

    # ════════════════════════════════════════════════════════════════════
    # 6. EXPECTED CONTRIBUTIONS
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("6. Expected Contributions")

    pdf.numbered_item(1,
        "First complete model of the equity-FX-hedging-bonds contagion chain, combining "
        "Rey et al. (2024) and Nenova et al. (2025) into a unified empirical framework."
    )
    pdf.numbered_item(2,
        "Discovery of the 'offsetting forces' mechanism: yield curve and FX effects on "
        "hedging costs partially cancel at the median but reinforce in the tails, creating "
        "nonlinear amplification detectable only with quantile methods."
    )
    pdf.numbered_item(3,
        "First application of quantile connectedness (Ando et al. 2022) to the FX hedging "
        "transmission chain, showing that contagion activates asymmetrically during stress."
    )
    pdf.numbered_item(4,
        "Evidence that the maturity mismatch in NBFI FX hedging (3-month swaps hedging "
        "10-year bonds) creates systemic rollover risk visible in Delta-CoVaR measures."
    )
    pdf.numbered_item(5,
        "Evidence on bi-directional spillovers: the FX hedging channel operates not only "
        "from the US outward but also in reverse, through European and Japanese NBFIs "
        "investing in US Treasuries on a hedged basis."
    )
    pdf.numbered_item(6,
        "Policy-relevant finding: FX swap volumes should be monitored as a systemic risk "
        "indicator, and central bank FX swap lines can break the contagion cascade."
    )

    pdf.section_heading("Positioning", level=2)
    pdf.body_text(
        "This project directly extends the BIS research programme led by Hyun Song Shin. "
        "Nenova, Schrimpf & Shin (2025) establish the facts; we add the nonlinear "
        "econometric machinery (quantile methods) to detect tail amplification that their "
        "linear framework cannot capture. This positions the paper as a natural complement "
        "to BIS research, suitable for a BIS Working Paper or a finance journal."
    )

    # ════════════════════════════════════════════════════════════════════
    # 7. REFERENCES
    # ════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_heading("7. References")

    refs = [
        "Adrian, T. & Brunnermeier, M. (2016). CoVaR. American Economic Review, 106(7), 1705-1741.",
        "Ando, T., Greenwood-Nimmo, M. & Shin, Y. (2022). Quantile connectedness: Modeling tail behavior in the topology of financial networks. Management Science, 68(4), 2401-2431.",
        "Bacchetta, P., Tieche, S. & van Wincoop, E. (2024). International portfolio choice with frictions: Evidence from mutual funds. Review of Financial Studies, 37(11), 3456-3501.",
        "Bauer, M., Bernanke, B. & Milstein, E. (2023). Risk appetite and the risk-taking channel of monetary policy. Journal of Economic Perspectives, 37(1), 77-100.",
        "Brauer, L. & Hau, H. (2024). Can currency management by international funds improve risk-adjusted returns? Working paper.",
        "Bruno, V. & Shin, H.S. (2015). Cross-border banking and global liquidity. Review of Economic Studies, 82(2), 535-564.",
        "Du, W. & Huber, A. (2024). Dollar asset holding and hedging around the globe. Working paper.",
        "Du, W., Im, J. & Schreger, J. (2018). The US Treasury premium. Journal of International Economics, 112, 167-181.",
        "Gurkaynak, R.S., Sack, B. & Swanson, E. (2005). Do actions speak louder than words? International Journal of Central Banking, 1(1), 55-93.",
        "Hacioglu-Hoke, S., Ostry, D.A. & Rey, H. (2024). The hedging channel of exchange rate determination. Working paper.",
        "Jarocinski, M. (2024). Estimating the Fed's unconventional policy shocks. Working paper.",
        "Kearns, J., Schrimpf, A. & Xia, D. (2023). Explaining monetary spillovers: The matrix reloaded. Journal of Money, Credit and Banking, 55(6), 1535-1568.",
        "Kroencke, T.A., Schmeling, M. & Schrimpf, A. (2021). The FOMC risk shift. Journal of Monetary Economics, 120, 21-39.",
        "Miranda-Agrippino, S. & Rey, H. (2020). US monetary policy and the global financial cycle. Review of Economic Studies, 87(6), 2754-2776.",
        "Nenova, T., Schrimpf, A. & Shin, H.S. (2025). Global portfolio investments and FX derivatives. BIS Working Paper No. 1273, June 2025.",
        "Rey, H. (2013). Dilemma not trilemma: The global financial cycle and monetary policy independence. Proceedings of the Federal Reserve Bank of Kansas City Jackson Hole Symposium.",
        "Rey, H., Stavrakeva, V. & Tang, J. (2024). Currency centrality in equity markets, exchange rates and global financial cycles. NBER Working Paper No. 33003.",
    ]
    for ref in refs:
        pdf.reference(ref)

    # ── Save ────────────────────────────────────────────────────────────
    output = "/home/user/SergioSola/reports/project4_fx_hedging_outline.pdf"
    pdf.output(output)
    print(f"Report saved to: {output}")
    print(f"Pages: {pdf.page_no()}")
    return output


if __name__ == "__main__":
    build_report()
