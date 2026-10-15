# Forecast: prospective2026

Cutoff 2026-10-14; questions and scores frozen in `data/prospective2026/FREEZE.json`.
`p_attention` = probability (Paper 3 logistic, trained on all 980 labelled questions) that the question is *substantively addressed* by arXiv astro-ph papers in 2026-10-15 .. 2031-10-14, under Paper 3's L1 label.

Calibration warning: on the 2021 backtest the absolute probabilities are only roughly calibrated (see results/backtest2021); read them as a ranking first.

Out-of-distribution: 94 of 200 questions have at least one feature outside the training 1st-99th percentile (column `ood_features` in the CSV); questions marked † below have 2+ such features and their probability should not be trusted.

## Mean forecast by subfield and source

| subfield              |   control |   direct_llm |   evidence_tension |   future_work |
|:----------------------|----------:|-------------:|-------------------:|--------------:|
| compact_objects       |      0.59 |         0.69 |               0.48 |          0.64 |
| cosmology_tensions    |      0.51 |         0.86 |               0.69 |          0.63 |
| exoplanet_atmospheres |      0.58 |         0.74 |               0.33 |          0.48 |
| fast_radio_bursts     |      0.39 |         0.7  |               0.48 |          0.56 |
| galaxy_evolution      |      0.41 |         0.6  |               0.55 |          0.67 |
| gravitational_waves   |      0.44 |         0.66 |               0.58 |          0.66 |
| protoplanetary_disks  |      0.41 |         0.72 |               0.58 |          0.71 |
| stellar_activity      |      0.45 |         0.72 |               0.32 |          0.36 |

## Top 25 — most likely to be taken up

| # | p | subfield | source | question | Paper 4 next step |
|---|---|---|---|---|---|
| 1 | 0.94 | cosmology_tensions | direct_llm | What is the precise nature of dark energy, and how can we distinguish between different models of dark energy dynamics? | — |
| 2 | 0.94 | cosmology_tensions | direct_llm | How can we resolve the Hubble tension between local measurements and those derived from the cosmic microwave background? | — |
| 3 | 0.93 | cosmology_tensions | direct_llm | What are the implications of potential modifications to gravity on cosmological observations, and how can we test these theories against current data? | — |
| 4 | 0.92 | exoplanet_atmospheres | direct_llm | What are the long-term stability and evolution of atmospheres on rocky exoplanets, particularly those in the habitable zone, under varying stellar activity and environmental conditions? | — |
| 5 | 0.91 | stellar_activity | direct_llm | What is the role of coronal mass ejections in shaping the long-term magnetic activity cycles of solar-type stars, and how do these cycles compare to those of other stellar types? | — |
| 6 | 0.90 † | gravitational_waves | future_work | What are the origins of binary black hole mergers? | — |
| 7 | 0.90 | gravitational_waves | future_work | What are the astrophysical sources of the rapid neutron-capture process (r process) that formed many elements heavier than iron? | — |
| 8 | 0.90 | fast_radio_bursts | future_work | What are the underlying mechanisms and progenitors of fast radio bursts (FRBs)? | — |
| 9 | 0.87 | cosmology_tensions | evidence_tension | What is the underlying cause of the discrepancy in the Hubble constant measurements between local observations and those inferred from the cosmic microwave background (CMB) within the framework of $ ext{ΛCDM}$? | simulation / modelling test; archival / survey search |
| 10 | 0.87 | galaxy_evolution | evidence_tension | What are the underlying causes of the discrepancies in Ly$eta$ escape fractions and equivalent widths (EW$_0$) of Ly$eta$ emitters (LAEs) observed between JWST and ground-based measurements, and how do these discrepancies relate to the IGM opacity at redshift $z=5.8-5.9$? | simulation / modelling test; archival / survey search |
| 11 | 0.86 † | compact_objects | direct_llm | How do gravitational wave signals from binary neutron star mergers inform us about the internal structure and composition of neutron stars, particularly in relation to phenomena like strange quark matter? | — |
| 12 | 0.86 | cosmology_tensions | control | What is the nature of the underlying mechanisms that govern the observed tensions in cosmological parameters? | — |
| 13 | 0.86 | fast_radio_bursts | direct_llm | How do the host galaxy environments influence the dispersion measures and scattering properties of fast radio bursts? | — |
| 14 | 0.85 | stellar_activity | direct_llm | What are the long-term effects of stellar magnetic activity on the evolution of planetary systems, especially regarding the stability and dynamics of orbits in the presence of stellar wind and radiation? | — |
| 15 | 0.85 | protoplanetary_disks | direct_llm | What role do magnetic fields play in the evolution of protoplanetary disks and the formation of planets within them? | — |
| 16 | 0.85 | fast_radio_bursts | control | What is the nature of the mechanisms underlying the generation and propagation of fast radio bursts? | — |
| 17 | 0.85 | exoplanet_atmospheres | direct_llm | How can we effectively distinguish between abiotic and biotic signatures in the atmospheres of potentially habitable exoplanets, especially in the presence of complex chemical interactions? | — |
| 18 | 0.84 | gravitational_waves | direct_llm | What are the implications of ultralight scalar dark matter on the frequency modulation of gravitational waves, and how can we effectively test these theories with current and future detectors? | — |
| 19 | 0.83 | galaxy_evolution | evidence_tension | What mechanisms can effectively mitigate strong dust attenuation in star-forming regions to reconcile the observed discrepancies in star formation rates and dust attenuation results? | simulation / modelling test; archival / survey search |
| 20 | 0.82 | cosmology_tensions | evidence_tension | How does the inclusion of decaying dark matter or early dark energy affect the reconciliation of the Hubble constant ($H_0$) measurements from the cosmic microwave background (CMB) and local distance ladder observations? | simulation / modelling test; archival / survey search |
| 21 | 0.82 | galaxy_evolution | future_work | What are the mechanisms that fuel AGN activity in galaxy evolution? | — |
| 22 | 0.82 † | compact_objects | future_work | What is the underlying physics connecting high-energy neutrinos and TDEs in dusty environments? | — |
| 23 | 0.82 | protoplanetary_disks | future_work | What are the mechanisms responsible for disk polarization at millimeter and submillimeter wavelengths? | — |
| 24 | 0.82 | cosmology_tensions | evidence_tension | What new physics in the early universe could reconcile the discrepancy between the Hubble constant measurements, $H_0$, derived from Planck data and those from the SH0ES collaboration? | simulation / modelling test; archival / survey search |
| 25 | 0.82 | gravitational_waves | evidence_tension | How do the tidal Love numbers in scalar-tensor theories compare to those predicted by General Relativity, and what implications do these differences have for the radiative stability and observational viability of these theories in cosmological contexts? | simulation / modelling test; archival / survey search |

## Bottom 15 — least likely

| # | p | subfield | source | question |
|---|---|---|---|---|
| 186 | 0.19 | stellar_activity | control | In what ways could the increase in the number of Hyads with periods by 50% influence the effectiveness of the proposed methods combined with the ZTF's cadence strategy for identifying M-dwarf flares and other fast transients? |
| 187 | 0.19 | galaxy_evolution | evidence_tension | What are the underlying reasons for the discrepancy between the dynamically inferred stellar-to-dark matter ratios of massive spirals and those inferred from abundance matching, and how do these ratios compare with the predictions of the standard $ ext{ΛCDM}$ model? |
| 188 | 0.18 | exoplanet_atmospheres | control | What implications does the high-resolution transit time-series of HD 189733b have for the imaging of lower-mass exoplanets in the mid-infrared under conditions of mitigated thermal background? |
| 189 | 0.17 | galaxy_evolution | control | How does the spatial distribution and kinematics of cold molecular gas in Mrk 996 reflect the underlying dynamics of low-mass Wolf-Rayet galaxies in a broader cosmological context? |
| 190 | 0.15 | exoplanet_atmospheres | evidence_tension | How do the aerosol distributions in the atmospheres of super-puff exoplanets like Kepler 51b and 51d affect the observed transmission spectra, and can future observations quantify the scale height and metallicity of these atmospheres? |
| 191 | 0.14 | stellar_activity | evidence_tension | How do the levels of unocculted stellar spots and faculae on the surface of HAT-P-12b compare to the photometric observations of spot coverage, specifically in terms of the percentage of spot coverage revealed by spectra versus the actual coverage? |
| 192 | 0.13 | exoplanet_atmospheres | evidence_tension | What are the specific temperature variations in the dayside atmosphere of WASP-12b that could explain the discrepancies in the observed thermal emission and the presence of a thermal inversion, as well as the retrieved carbon-to-oxygen ratio (C/O) and the bump in the spectrum at 1.25 micron? |
| 193 | 0.13 | exoplanet_atmospheres | evidence_tension | How do the abundances of sodium, water, titanium oxide, and vanadium oxide in the atmospheres of hot Jupiters, specifically HAT-P-32b, affect the observed emission spectrum and geometric albedo, and can future observations resolve the discrepancies between non-inverted atmosphere models and solar composition radiative convective equilibrium predictions? |
| 194 | 0.13 † | gravitational_waves | control | How might the comparison of BBH merger populations detected by LIGO/Virgo with long GRB world models reveal insights into the underlying principles of stellar mass black hole formation? |
| 195 | 0.12 | fast_radio_bursts | control | How do the extreme $ au_{ m RM}$ values observed in FRBs with compact persistent radio sources relate to the credibility levels of ruling out uncorrelated reionization in high redshift FRB samples? |
| 196 | 0.10 | fast_radio_bursts | future_work | Can the expulsion of magnetic flux associated with superconductivity be effective in neutron stars? |
| 197 | 0.04 | stellar_activity | future_work | What is the average coverage area of spots on Pleiades members, given that the observed luminosities have a standard deviation of 0.05 dex and can be explained by a star-to-star standard deviation of spot coverage of 10%? |
| 198 | 0.02 † | stellar_activity | evidence_tension | What is the nature of the X-ray emission from the source observed with XMM-Newton, and how does it relate to the anomalously blue Gaia counterpart identified as a WD+dM pair, particularly in terms of luminosity and duration compared to typical stellar flares? |
| 199 | 0.02 † | stellar_activity | evidence_tension | What are the underlying reasons for the discrepancy in spot coverage fractions inferred from photometric observations during the extit{Kepler} era (10--20%) compared to the lower values observed from TESS in the mid 2020s (1--10%)? |
| 200 | 0.01 | cosmology_tensions | control | How does the construction of the YONSEI SN catalog inform our understanding of supernova evolution in a theoretical context? |

Full ranked table: `results/prospective2026/forecast.csv`.
