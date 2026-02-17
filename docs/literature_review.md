# Literature Review: Bank–Non-Bank Interlinkages, Systemic Risk, and the Global Financial Cycle

## 1. Non-Bank Financial Intermediation: Scope and Growth

Non-bank financial intermediaries (NBFIs) now account for roughly half of global
financial assets (FSB 2023). The sector includes:

- **Investment funds** (mutual funds, ETFs): Offer liquidity transformation by
  providing daily redemptions against illiquid portfolios (Goldstein, Jiang &
  Ng 2017). Run risk arises when outflows force fire sales.
- **Money market funds (MMFs)**: Provide bank-like services (deposits, payments)
  without deposit insurance. The Reserve Primary Fund break-the-buck episode in
  2008 demonstrated the systemic consequences (Kacperczyk & Schnabl 2013).
- **Hedge funds**: Use significant leverage (often through prime brokerage from
  banks), concentrate positions, and can transmit shocks through margin spirals
  (Brunnermeier & Nagel 2004; Patton, Ramadorai & Streatfield 2015).
- **Pension funds and insurance companies**: Long-term investors but increasingly
  engaged in repo markets, derivatives, and alternative assets. LDI strategies
  in UK pension funds created a gilt-market crisis in 2022.
- **Direct credit / private debt funds**: Rapidly growing since 2010, now
  competing with banks in leveraged lending. Opacity and illiquidity create
  valuation and contagion risks.

Key references:
- FSB (2023), *Global Monitoring Report on Non-Bank Financial Intermediation*.
- Claessens, Pozsar, Ratnovski & Singh (2012), "Shadow Banking: Economics and
  Policy," IMF Staff Discussion Note.
- Stein (2012), "Monetary Policy as Financial-Stability Regulation," QJE.
- Pozsar, Adrian, Ashcraft & Boesky (2013), "Shadow Banking," FRBNY Economic
  Policy Review.

## 2. Bank–NBFI Interlinkages: Channels and Evidence

Banks and non-banks are connected through multiple channels:

### 2.1 Asset-side linkages
- Banks lend to NBFIs (fund finance, subscription lines, NAV facilities).
- Banks hold bonds issued by non-bank entities.
- Both sectors hold common assets, creating indirect contagion via fire-sale
  price impact (Cont & Schaanning 2017; Greenwood, Landier & Thesmar 2015).

### 2.2 Liability-side linkages
- NBFIs place deposits and short-term funding with banks.
- Repo and securities lending: Banks provide financing to hedge funds and dealers
  against collateral; haircut spirals amplify deleveraging (Gorton & Metrick
  2012).
- Derivatives: Banks are counterparties to NBFI derivative positions. Margin
  calls create procyclical cash demands.

### 2.3 Ownership and sponsorship
- Banks sponsor MMFs, securitization vehicles, and structured investment vehicles
  (SIVs). Implicit guarantees create step-in risk (Acharya, Schnabl & Suarez
  2013).

### 2.4 Empirical evidence
- Abad, Aldasoro, Aymanns, D'Errico, Fache Rousová, Hoffmann, Hüser,
  Langfield, Neychev & Roukny (2022) map the euro-area OTC derivatives network
  and show that banks are central nodes linking different NBFI types.
- Aldasoro, Huang & Kemp (2020) use BIS data to show cross-border bank
  lending to NBFIs has grown faster than bank-to-bank lending since 2008.

## 3. Systemic Risk: Theory and Measurement

### 3.1 VaR Constraints and Procyclical Leverage

Adrian & Shin (2010, 2014) show that when intermediaries manage balance sheets
to maintain a target VaR (or equivalently, a regulatory capital ratio), leverage
moves *with* asset prices rather than against them:

- Asset prices rise → measured risk falls → VaR constraint loosens → firm
  expands balance sheet → further price increases.
- Asset prices fall → measured risk rises → VaR constraint binds → forced
  deleveraging → fire sales → further price declines.

This creates a **leverage cycle** (Geanakoplos 2010) and endogenous volatility.
Brunnermeier & Pedersen (2009) formalize the interaction between market liquidity
and funding liquidity, showing how margin requirements create destabilizing
feedback loops.

**Extension to NBFIs**: The same mechanism applies to any entity subject to VaR
or margin constraints:
- Hedge funds face margin calls from prime brokers.
- Insurance companies face solvency capital requirements (Solvency II) that
  are risk-sensitive.
- Investment funds face redemption-driven liquidation that mimics forced
  deleveraging.
- Pension funds using LDI face margin calls on interest-rate derivatives.

The amplification is *larger* when multiple heterogeneous intermediaries with
correlated constraints liquidate simultaneously.

### 3.2 Systemic Risk Measures

| Measure | Reference | Idea |
|---------|-----------|------|
| CoVaR | Adrian & Brunnermeier (2016) | VaR of the system conditional on an institution being in distress |
| MES | Acharya et al. (2017) | Expected loss of firm i when the market falls below its VaR |
| SRISK | Brownlees & Engle (2017) | Capital shortfall of firm i under a prolonged market decline |
| DY Connectedness | Diebold & Yilmaz (2012, 2014) | Generalized FEVD from VAR; total and directional spillover indices |
| Granger-causality networks | Billio, Getmansky, Lo & Pelizzon (2012) | Pairwise Granger-causality tests to build return-spillover networks across banks, hedge funds, insurance, broker-dealers |

Billio et al. (2012) is especially relevant because they explicitly study
four financial sectors (banks, broker-dealers, insurance companies, hedge funds)
and show that connectedness increased dramatically before the 2008 crisis,
with hedge funds being important transmitters.

### 3.3 Fire Sales and Common Asset Holdings

Greenwood, Landier & Thesmar (2015) develop a model of fire-sale externalities
based on overlapping portfolios. The "aggregate vulnerability" of the system
depends on:
- Concentration of asset holdings.
- Leverage of institutions holding those assets.
- Illiquidity of the assets.

When NBFIs and banks hold the same assets (e.g., corporate bonds, CLOs), a
shock to one sector's balance sheets can trigger fire sales that spill over
to the other.

## 4. The Global Financial Cycle

### 4.1 A Single Global Factor

Rey (2015) argues that capital flows, asset prices, and credit growth across
countries are driven by a single global factor closely linked to the VIX and
US monetary policy. This "global financial cycle" implies that the traditional
trilemma (open capital account, independent monetary policy, fixed exchange
rate—pick two) collapses to a dilemma: countries with open capital accounts
cannot have independent monetary policy regardless of their exchange-rate
regime.

Miranda-Agrippino & Rey (2020) extract this global factor using a dynamic
factor model on a large panel of risky asset returns and show it is driven
by US monetary policy.

### 4.2 The Role of Intermediaries

Bruno & Shin (2015) formalize how global banks transmit US monetary policy
to the rest of the world through cross-border lending. Their leverage channel
works through the same VaR-constraint mechanism:

- US rates fall → measured risk falls → global banks expand cross-border
  lending → capital inflows to EMEs → local asset prices rise.

**The NBFI extension**: Non-banks increasingly operate globally:
- International bond funds channel portfolio flows to emerging markets
  (Cerutti, Claessens & Puy 2019).
- CLO managers and direct-lending funds have global portfolios.
- Hedge funds arbitrage cross-border yield differentials.

These flows are *more* procyclical than bank lending because:
1. Fund flows respond to past returns (Coval & Stafford 2007).
2. Benchmark-driven investment creates herding (Raddatz & Schmukler 2012).
3. Swing pricing and redemption gates are imperfect tools against run dynamics.

### 4.3 Amplification Hypothesis

The central hypothesis of this project is that the growth of NBFIs and their
linkages with banks *amplifies* the global financial cycle through:

1. **Leverage co-movement**: VaR/margin constraints bind simultaneously across
   banks and NBFIs during stress, creating larger aggregate deleveraging.
2. **Common-asset fire sales**: Overlapping portfolios transmit shocks between
   sectors and across borders.
3. **Funding fragility**: NBFI dependence on short-term bank funding (repo,
   fund finance) creates a contagion channel from NBFI stress to bank balance
   sheets and vice versa.
4. **Regulatory arbitrage**: Activities migrate from regulated banks to less
   regulated NBFIs, increasing aggregate risk without reducing it.

## 5. Empirical Strategy

### 5.1 Panel Construction

Build a quarterly panel of:
- Major global banks (G-SIBs and other large banks, ~50 institutions).
- Publicly listed NBFIs (asset managers, hedge fund platforms, insurance
  companies, private credit BDCs, ~50 institutions).
- Country-level NBFI sector sizes from FSB data.
- Bilateral bank-NBFI exposure data from BIS and ECB.

### 5.2 Identification

1. **Systemic risk and interlinkages**: Estimate CoVaR, MES, and DY
   connectedness for the full cross-section of banks and NBFIs. Test whether
   bank-NBFI connectedness predicts future systemic risk (following Billio
   et al. 2012).

2. **VaR amplification**: Regress changes in leverage on changes in asset
   values for banks vs. different NBFI types. Test for asymmetry (stronger
   effect in downturns) and interaction with interconnectedness.

3. **Global financial cycle**: Estimate the global factor. Regress local
   credit growth and asset prices on the global factor, interacted with
   country-level NBFI penetration and bank-NBFI connectedness. Instrument
   for NBFI penetration using pre-sample regulatory variation.

## 6. Key References

1. Acharya, V., Pedersen, L., Philippon, T., & Richardson, M. (2017). Measuring systemic risk. *Review of Financial Studies*, 30(1), 2–47.
2. Acharya, V., Schnabl, P., & Suarez, G. (2013). Securitization without risk transfer. *Journal of Financial Economics*, 107(3), 515–536.
3. Adrian, T., & Brunnermeier, M. K. (2016). CoVaR. *American Economic Review*, 106(7), 1705–1741.
4. Adrian, T., & Shin, H. S. (2010). Liquidity and leverage. *Journal of Financial Intermediation*, 19(3), 418–437.
5. Adrian, T., & Shin, H. S. (2014). Procyclical leverage and value-at-risk. *Review of Financial Studies*, 27(2), 373–403.
6. Aldasoro, I., Huang, W., & Kemp, E. (2020). Cross-border links between banks and non-bank financial institutions. *BIS Quarterly Review*, September.
7. Billio, M., Getmansky, M., Lo, A., & Pelizzon, L. (2012). Econometric measures of connectedness and systemic risk in the finance and insurance sectors. *Journal of Financial Economics*, 104(3), 535–559.
8. Brownlees, C., & Engle, R. F. (2017). SRISK: A conditional capital shortfall measure of systemic risk. *Review of Financial Studies*, 30(1), 48–79.
9. Brunnermeier, M. K., & Pedersen, L. H. (2009). Market liquidity and funding liquidity. *Review of Financial Studies*, 22(6), 2201–2238.
10. Bruno, V., & Shin, H. S. (2015). Cross-border banking and global liquidity. *Review of Economic Studies*, 82(2), 535–564.
11. Cerutti, E., Claessens, S., & Puy, D. (2019). Push factors and capital flows to emerging markets. *Journal of International Money and Finance*, 96, 18–37.
12. Claessens, S., Pozsar, Z., Ratnovski, L., & Singh, M. (2012). Shadow banking: Economics and policy. *IMF Staff Discussion Note* 12/12.
13. Cont, R., & Schaanning, E. (2017). Fire sales, indirect contagion and systemic stress testing. *Norges Bank Working Paper* 2/2017.
14. Diebold, F. X., & Yilmaz, K. (2012). Better to give than to receive: Predictive directional measurement of volatility spillovers. *International Journal of Forecasting*, 28(1), 57–66.
15. Diebold, F. X., & Yilmaz, K. (2014). On the network topology of variance decompositions. *Journal of Econometrics*, 182(1), 119–134.
16. FSB (2023). *Global Monitoring Report on Non-Bank Financial Intermediation*.
17. Geanakoplos, J. (2010). The leverage cycle. *NBER Macroeconomics Annual*, 24(1), 1–66.
18. Goldstein, I., Jiang, H., & Ng, D. T. (2017). Investor flows and fragility in corporate bond funds. *Journal of Financial Economics*, 126(3), 592–613.
19. Greenwood, R., Landier, A., & Thesmar, D. (2015). Vulnerable banks. *Journal of Financial Economics*, 115(3), 471–485.
20. Miranda-Agrippino, S., & Rey, H. (2020). US monetary policy and the global financial cycle. *Review of Economic Studies*, 87(6), 2754–2776.
21. Rey, H. (2015). Dilemma not trilemma: The global financial cycle and monetary policy independence. *NBER Working Paper* 21162.
22. Stein, J. C. (2012). Monetary policy as financial-stability regulation. *Quarterly Journal of Economics*, 127(1), 57–95.
