"""Historical astronomy controversies with known outcomes (as of 2026-10).

Each case: arXiv onset date of the first claim (v1), a regex that finds the
case in title+abstract, the outcome label and a one-line justification.
Outcome labels (fixed before any feature is computed):
  dissolved  - by 2026-10 the claim is attributed to systematics, instruments,
               data processing or a mundane cause, or it failed confirmation
               with more sensitive data;
  confirmed  - the claimed signal/phenomenon is accepted as real;
  open       - still contested in 2026 (neither dissolved nor settled).
`provisional` marks labels a reasonable expert could dispute; the primary
analysis is repeated without them.
"""

CASES = [
    # ---- dissolved
    dict(key="bicep2", onset="2014-03-17", query=r"BICEP2", outcome="dissolved", provisional=False,
         note="B-mode signal explained by Galactic dust (BICEP2/Keck+Planck 2015)."),
    dict(key="line_3p5kev", onset="2014-02-10", query=r"3\.5\d?\s?keV", outcome="dissolved", provisional=False,
         note="Unidentified X-ray line not seen in Hitomi Perseus and deep blank-sky searches."),
    dict(key="fermi_130gev", onset="2012-04-12", query=r"130\s?GeV", outcome="dissolved", provisional=False,
         note="Gamma-ray line faded with more Fermi-LAT data; instrumental/statistical."),
    dict(key="dark_flow", onset="2008-09-22", query=r"dark flow", outcome="dissolved", provisional=False,
         note="Bulk flow from kSZ not confirmed by Planck (2013)."),
    dict(key="alpha_dipole", onset="2010-08-19", query=r"fine.structure constant.{0,80}(dipole|spatial)|(dipole|spatial variation).{0,80}fine.structure constant",
         outcome="dissolved", provisional=False, note="Spatial alpha dipole attributed to wavelength-calibration systematics."),
    dict(key="perytons", onset="2010-09-28", query=r"peryton", outcome="dissolved", provisional=False,
         note="Parkes perytons traced to an on-site microwave oven (2015)."),
    dict(key="alpha_cen_bb", onset="2012-10-17", query=r"(Alpha|α|\\alpha)\s?Cen(tauri)?\s?B\s?b", outcome="dissolved", provisional=False,
         note="Radial-velocity planet shown to be a sampling artefact (2015)."),
    dict(key="gj581g", onset="2010-09-29", query=r"(GJ|Gliese)\s?581\s?g|(GJ|Gliese)\s?581.{0,60}(habitable|planets?)", outcome="dissolved", provisional=False,
         note="Planet signals attributed to stellar activity (2014)."),
    dict(key="gbm_gw150914", onset="2016-02-14", query=r"GW150914.{0,200}(GBM|gamma.ray)|(GBM|gamma.ray).{0,200}GW150914", outcome="dissolved", provisional=False,
         note="Weak Fermi-GBM transient not confirmed (INTEGRAL, later events)."),
    dict(key="tabby_star", onset="2015-09-11", query=r"KIC\s?8462852|Boyajian'?s star|Tabby'?s star", outcome="dissolved", provisional=False,
         note="Dimmings explained by circumstellar dust (chromatic dips, 2018)."),
    dict(key="kepler1625_moon", onset="2017-07-26", query=r"Kepler.1625", outcome="dissolved", provisional=True,
         note="Exomoon candidate not supported by independent reanalyses."),
    dict(key="barnard_b", onset="2018-11-14", query=r"Barnard'?s star", outcome="dissolved", provisional=False,
         note="233-day super-Earth refuted as stellar activity (2021)."),
    dict(key="venus_phosphine", onset="2020-09-14", query=r"phosphine.{0,200}Venus|Venus.{0,200}phosphine", outcome="dissolved", provisional=True,
         note="Signal largely attributed to data processing / SO2; disputed by the discovery team."),
    dict(key="closed_universe", onset="2019-11-05", query=r"closed universe|curvature tension|positive(ly)? curv", outcome="dissolved", provisional=True,
         note="Planck-preferred closed geometry removed by lensing/BAO and Planck PR4."),
    dict(key="edges_21cm", onset="2018-02-28", query=r"(?-i:EDGES)", outcome="dissolved", provisional=True,
         note="Absorption profile rejected by SARAS 3 (2021); not settled."),
    dict(key="auger_agn", onset="2007-11-09", query=r"Auger.{0,150}(AGN|active galactic|correlat)|(AGN|active galactic).{0,150}Auger", outcome="dissolved", provisional=False,
         note="UHECR-AGN correlation fell from 69% to chance-level ~33% with more data."),
    dict(key="dampe_1p4tev", onset="2017-11-29", query=r"1\.4\s?TeV.{0,120}(electron|peak|excess|spectral|line)|(electron|peak|excess|spectral|line).{0,120}1\.4\s?TeV|DAMPE.{0,120}(peak|excess|line)", outcome="dissolved", provisional=False,
         note="Electron spectral peak not confirmed by CALET or later DAMPE data."),
    dict(key="fomalhaut_b", onset="2008-11-13", query=r"Fomalhaut\s?b", outcome="dissolved", provisional=False,
         note="Directly imaged planet re-interpreted as an expanding dust cloud (2020)."),
    dict(key="gw_echoes", onset="2016-12-27", query=r"echo(es)?.{0,100}(gravitational.wave|horizon|ringdown)|(gravitational.wave|ringdown).{0,100}echo(es)?", outcome="dissolved", provisional=True,
         note="Claimed post-merger echoes not confirmed by LIGO/Virgo searches."),
    # ---- confirmed
    dict(key="frb", onset="2007-09-27", query=r"fast radio bursts?|Lorimer burst|millisecond radio burst|extragalactic radio burst|(?-i:\bFRBs?\b)", outcome="confirmed", provisional=False,
         note="Population confirmed (Thornton 2013), localised hosts (2017)."),
    dict(key="fermi_bubbles", onset="2010-05-28", query=r"Fermi bubbles?|Fermi lobes?|Fermi haze", outcome="confirmed", provisional=False,
         note="Bipolar gamma-ray structures confirmed (eROSITA bubbles, 2020)."),
    dict(key="pta_gwb", onset="2020-09-10", query=r"common.(spectrum|red).process|stochastic gravitational.wave background.{0,120}(pulsar timing|PTA|NANOGrav)|(pulsar timing|PTA|NANOGrav).{0,120}gravitational.wave background",
         outcome="confirmed", provisional=False, note="Hellings-Downs correlation evidence from NANOGrav/EPTA/PPTA/CPTA (2023)."),
    dict(key="odd_radio_circles", onset="2020-06-27", query=r"odd radio circles?|(?-i:\bORCs?\b)", outcome="confirmed", provisional=False,
         note="Confirmed with MeerKAT and additional surveys."),
    dict(key="icecube_astro_nu", onset="2013-04-26", query=r"IceCube.{0,120}(PeV|astrophysical neutrino)|(PeV|astrophysical) neutrinos?.{0,120}IceCube", outcome="confirmed", provisional=False,
         note="Astrophysical neutrino flux established (2013-2014)."),
    dict(key="pamela_positrons", onset="2008-10-28", query=r"positron (fraction|excess)|PAMELA", outcome="confirmed", provisional=False,
         note="Rising positron fraction confirmed by Fermi-LAT and AMS-02; origin still debated."),
    # ---- open
    dict(key="h0_tension", onset="2013-03-20", query=r"Hubble (constant )?tension|H_?\{?0\}? tension|tension.{0,60}(Hubble constant|H_?\{?0\}?)", outcome="open", provisional=False,
         note="Distance-ladder vs CMB H0 discrepancy persists."),
    dict(key="gc_gev_excess", onset="2009-10-15", query=r"(Galactic Cent(er|re)|inner Galaxy).{0,120}(gamma.ray|GeV).{0,40}excess|(gamma.ray|GeV).{0,40}excess.{0,120}(Galactic Cent(er|re)|inner Galaxy)|Galactic Cent(er|re) excess", outcome="open", provisional=False,
         note="Millisecond pulsars vs dark matter still debated."),
    dict(key="arcade2_radio", onset="2009-01-05", query=r"(?-i:ARCADE)|radio (background|synchrotron background) excess|excess radio background", outcome="open", provisional=False,
         note="Radio background excess unexplained."),
    dict(key="cosmic_birefringence", onset="2020-11-23", query=r"(cosmic|isotropic) birefringence", outcome="open", provisional=False,
         note="Hint persists, limited by polarisation-angle calibration."),
    dict(key="quasar_dipole", onset="2020-09-30", query=r"(quasar|number.count|radio source).{0,80}dipole|dipole.{0,80}(quasar|number.count)|cosmic dipole anomal", outcome="open", provisional=False,
         note="Matter dipole excess vs CMB kinematic dipole still debated."),
    dict(key="planet_nine", onset="2016-01-20", query=r"Planet Nine|Planet 9|ninth planet|distant (giant )?planet.{0,80}(clustering|TNO|Kuiper)", outcome="open", provisional=False,
         note="Clustering of distant TNOs and the planet remain unresolved."),
    dict(key="df2_no_dm", onset="2018-03-28", query=r"NGC\s?1052.DF[24]|galax(y|ies) (lacking|without) dark matter", outcome="open", provisional=True,
         note="Distance and dynamics still disputed."),
    dict(key="s8_tension", onset="2013-03-20", query=r"S_?\{?8\}? tension|\\sigma_?\{?8\}? tension|tension.{0,60}(S_?\{?8\}?|\\sigma_8|weak lensing|CFHTLenS|cluster counts)|(CFHTLenS|cluster counts|weak lensing).{0,80}(tension|discrepan)", outcome="open", provisional=True,
         note="Partly relieved by KiDS-Legacy (2025) but not resolved."),
]

# Live controversies (outcome unknown in 2026): scored by the frozen model for a sealed forecast.
PROSPECTIVE = [
    dict(key="jwst_early_massive", onset="2022-07-25", query=r"(JWST|James Webb).{0,200}(massive|bright|luminous) galax|(massive|bright|luminous) galax.{0,200}(JWST|James Webb)"),
    dict(key="little_red_dots", onset="2023-06-01", query=r"little red dots?|(?-i:\bLRDs?\b)"),
    dict(key="desi_evolving_de", onset="2024-04-04", query=r"(DESI).{0,200}(dynamical|evolving|time.varying) dark energy|(dynamical|evolving|time.varying) dark energy.{0,200}DESI|w_?0\s?w_?a"),
    dict(key="k2_18b_dms", onset="2023-09-11", query=r"K2.18\s?b"),
    dict(key="km3net_220pev", onset="2025-02-12", query=r"KM3.230213A|KM3NeT.{0,120}(PeV|ultra.high.energy)"),
]
