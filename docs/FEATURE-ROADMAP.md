# Feature & Improvement Roadmap

This is a **feasibility-checked** roadmap, meant to be used both as an internal build plan and as pitch material for accelerators/evaluators. Every idea below was checked against current (2026) research and industry practice before being included — several ideas that first looked attractive were kept out, or reframed, because the evidence doesn't support them yet (see [What not to overpromise](#what-not-to-overpromise)). Sources are linked inline; a consolidated list is at the bottom.

## How to read this

Each item is tagged:

- ✅ **Feasible now** — buildable with today's stack/data, no new external dependency or partnership needed.
- ⚠️ **Feasible with investment** — real engineering/data/partnership effort, but grounded in evidence that it works.
- 🔬 **R&D / needs validation** — technically possible per research, but needs a local pilot or ground-truth data before it can be claimed to work for AgriSat specifically.
- ❌ **Not realistic yet** — the research argues against doing this now (or as claimed); listed only to explain why it's deliberately excluded.

---

## 1. Data accuracy & "real-time" improvements

### 1.1 Cloud-aware expectation setting on Tier 3 (✅ feasible now, and should be done regardless of other work)
The current README/guide language should not imply true real-time optical monitoring. Sentinel-2's twin-satellite constellation gives a 2–5 day revisit, but **revisit frequency is not the same as cloud-free observation frequency** — in monsoon-affected regions like Sindh, usable optical scenes during critical growth windows can be weeks apart despite the short revisit cycle [[1]](https://www.sciencedirect.com/science/article/pii/S2772375526006301). This is already why Tier 3 leans on Sentinel-1 SAR (cloud-penetrating) — that design decision is validated by the literature, not just a fallback. Action: state "near-real-time, cloud-dependent for optical / all-weather for SAR" explicitly in product materials rather than "real-time."

### 1.2 SAR-based soil moisture as a new input (✅ feasible now)
AgriSat already pulls Sentinel-1 SAR for the backscatter/vegetation index. The same SAR data supports a **soil moisture index** using well-established retrieval methods (e.g., the TU Wien change-detection algorithm), which recent work shows can reach very high accuracy for irrigation/drought decisions (R²=0.96–0.97, RMSE<0.025 cm³/cm³ in a smallholder maize study using a 10 m daily EO+ML pipeline) [[2]](https://doi.org/10.3390/w18040499). Sentinel-1 offers up to 5 m spatial and ~6-day (improving toward better) temporal resolution for this [[3]](https://www.sciencedirect.com/science/article/pii/S0034425725005504). This is a natural extension of `services/tiers/gee_client.py` — same data source, new derived index — and would let the risk engine cross-check vegetation stress against soil-water stress, not just rainfall (CHIRPS) as it does today.

### 1.3 Cloud-gap-filling for continuous optical NDVI (⚠️ feasible with investment)
Deep-learning gap-filling (fusing SAR + sparse optical observations to reconstruct a continuous NDVI-like signal) is an active, working research direction for grassland/cropland monitoring [[4]](https://arxiv.org/html/2403.09554v1). This would meaningfully close the gap between "SAR available daily-ish, optical available every few weeks in practice" — but it's a real model-training effort (needs a training dataset and validation, not a config change). Recommend scoping as a dedicated M-series module rather than folding into the existing fusion logic.

> **Budget note:** every item below that touches Google Earth Engine is free only under its noncommercial terms — which stop applying the moment a paying institution is billed for a AgriSat output. See [`FREE-VS-PAID-RESOURCES.md`](FREE-VS-PAID-RESOURCES.md) before assuming any GEE-based item stays free at commercial launch.

### 1.4 Higher-resolution optical via PlanetScope (⚠️ feasible with investment — this is exactly what M5 already anticipates)
PlanetScope delivers daily, 3 m, 8-band imagery and is explicitly sold for agriculture with per-hectare/subscription pricing and areas of interest as small as 1 hectare [[5]](https://www.planet.com/pricing/agriculture/). A Malawi smallholder study using PlanetScope reported "up to 60% confidence" in yield prediction accuracy [[6]](https://earth.esa.int/eogateway/success-story/predicting-crop-yield-using-planet-data) — genuinely useful, but **not a precision instrument at the individual-smallholder-field level yet**; treat it as a resolution upgrade for Tier 2/1, not a yield-accuracy silver bullet. `services/tiers/planet.py` is already stubbed for this — the blocker is commercial/licensing (the E&R Program access mentioned in the code), not engineering. Action: pursue either Planet's paid Agriculture plan (budget item) or re-apply to the Education & Research program with a clearer pilot scope, since the current "deferred" status in `MODULE-PLAN.md` is a licensing wait, not a technical one.

### 1.5 Supplementing CHIRPS rainfall with a faster-cadence product (✅ feasible now)
CHIRPS updates are not sub-daily. NASA's IMERG (GPM) product provides half-hourly, near-global precipitation estimates and is also accessible via Google Earth Engine — a straightforward addition alongside the existing CHIRPS call in `services/tiers/gee_client.py` for faster rainfall-anomaly detection between CHIRPS's own update cycles, without adding a new vendor relationship.

### 1.6 Local ground-truth sensor network (🔬 needs validation / pilot)
Low-cost soil-moisture sensors (as little as $2–10 for capacitive sensors, $20–40 for an Arduino-class logger) can calibrate and validate the satellite-derived indices in situ [[7]](https://pmc.ncbi.nlm.nih.gov/articles/PMC12526549/). This is not a software feature — it requires physical hardware, install/maintenance in Matiari fields, and a data-ingestion endpoint. Worth a small pilot (10–20 sensors across the pilot district) specifically to generate the ground-truth data needed for items 1.3 and 3.1 below, rather than a full rollout up front.

### 1.7 Pakistan Meteorological Department (PMD) data partnership (🔬 needs validation)
PMD does run a farmer-facing "Pak Weather" app and a Numerical Weather Prediction pipeline, and a separate Flood Forecasting Division with real-time river-flow data [[8]](https://www.pmd.gov.pk/). No public, documented API for programmatic access surfaced in research — this would need direct outreach/an MOU with PMD, not an integration you can build against today. Worth pursuing for local credibility (a Pakistani product using a Pakistani government data source is a strong pitch point) but budget it as a partnerships task, not an engineering sprint.

---

## 2. ML / analytics feature ideas

### 2.1 Explainability on the existing ML risk layer (✅ feasible now)
`services/ml_risk.py` already does the right structural thing — an elevate-only blend, never overriding the transparent z-score with a black-box downgrade. Regulators and insurance underwriters explicitly expect model transparency (EU AI Act-style transparency obligations, FinRegLab's underwriting-explainability guidance, and insurers' own compliance teams verifying "which factors influenced risk assessment") [[9]](https://finreglab.org/research/ai-faqs-explainability-in-credit-underwriting/) [[10]](https://www.fluxforce.ai/blog/explainable-ai-in-finance). Since `ml_risk.py` uses a gradient-boosted classifier, adding SHAP-style per-feature attribution to the stored `risk_audit_log` entry is a contained, high-value addition — it turns "the model said elevated risk" into "the model said elevated risk because of X, Y, Z," which is exactly what an insurance partner's compliance review will ask for.

### 2.2 Transformer-based crop-stress/yield modeling (🔬 needs validation — do not build yet)
2025–2026 research shows real progress: attention-based multi-modal models beating prior transformer baselines by several points of R² on yield tasks [[11]](https://arxiv.org/html/2604.19217v1), and specialized architectures for field-level yield [[12]](https://doi.org/10.3390/agriengineering8010002). But every one of these was trained on a labeled historical yield dataset. **AgriSat does not currently have local ground-truth yield/loss data for Matiari wheat** — without it, a transformer model would be no more trustworthy than the current z-score approach, just harder to explain. Sequence: get 1–2 seasons of real yield/loss outcomes (from an insurer/lender partner or a small field survey) before investing in this.

### 2.3 Farmer/loan-officer advisory chatbot (⚠️ feasible with investment)
There's a real, funded direction here: IFPRI's GAIA project and CABI are actively building GenAI agricultural advisory tools for smallholders, and Digital Green has shipped a fine-tuned agriculture LLM over WhatsApp [[13]](https://www.ifpri.org/project/generative-ai-for-agriculture-gaia/) [[14]](https://www.frontiersin.org/journals/remote-sensing/articles/10.3389/frsen.2026.1839369/full). For AgriSat this is a genuine differentiator for a loan-officer-facing tool: an LLM grounded (RAG) on the existing `content/guideContent.ts` knowledge base plus the field's own risk explanation, answering "why is this field elevated risk" or "what should the loan officer tell the farmer" in plain language. This needs real investment (LLM API cost, an evaluation harness so it doesn't hallucinate agronomic advice, Urdu-language support) and should stay strictly advisory — never feed its output into the risk score itself.

---

## 3. Insurance / product feature ideas (grounded in parametric-insurance practice)

### 3.1 A basis-risk dashboard (🔬 needs validation, high strategic value)
The core, industry-acknowledged problem with any satellite-index insurance product is **basis risk**: a farmer suffers real loss but the index never crosses the payout trigger, or vice versa [[15]](https://nhess.copernicus.org/articles/25/913/2025/). Best practice explicitly calls for testing "index design, data continuity, basis risk, and regulatory status" before an index goes live [[16]](https://umbrex.com/resources/umbrex-explainers/agriculture-food-explainers/parametric-crop-insurance/). AgriSat's `risk_audit_log` already stores the history needed to build this — once even a small amount of real outcome data exists (claims, field-survey losses), a dashboard comparing "risk tier said X" vs. "actual outcome was Y" would be the single most credible artifact to show an insurance partner or evaluator. This is a data-availability gap today, not an engineering one — the audit trail is already there.

### 3.2 Multi-peril index, formalized (✅ feasible now — mostly a documentation/config exercise)
Modern satellite-based index insurance increasingly blends vegetation health and soil-moisture/rainfall indices rather than relying on one signal, because vegetation indices track crop stress more directly than a single distant weather station [[17]](https://www.swissre.com/reinsurance/property-and-casualty/agriculture-risks/agricultural-insurance-parametric-products.html). AgriSat's fusion of NDVI/EVI + SAR + CHIRPS rainfall is already a multi-peril design — the improvement here is formalizing the per-peril weighting and documenting it as a named "AgriSat Composite Index," which is both a technical improvement (auditable weights instead of implicit logic spread across `fusion.py`/`risk_engine.py`) and a stronger pitch artifact.

### 3.3 Faster settlement signal (✅ already true — make it a headline metric)
2025–2026 market commentary points to AI-driven parametric settlements targeting **under 72 hours** from trigger to payout signal as a competitive benchmark [[18]](https://newspaceeconomy.ca/2026/05/11/satellite-services-for-parametric-insurance-market-analysis-2026/). AgriSat's async pipeline already produces a risk assessment within minutes of a GEE job completing (not days) — this is a real, already-built advantage worth quantifying and stating explicitly in pitch materials rather than left implicit.

---

## 4. Closing feature gaps vs. established platforms

Research on CropIn, Taranis, and comparable platforms [[19]](https://www.taranis.com/) [[20]](https://gitnux.org/best/crop-monitoring-software/) surfaced three capability gaps worth naming honestly:

- **Pest/disease detection** (Taranis's core strength, via drone-level imagery) — ❌ not realistic via satellite resolution; ⚠️ feasible at lower cost via farmer-submitted phone photos + an image-classification model (well-trodden ground, e.g. PlantVillage-style disease classifiers) rather than drones, which don't fit AgriSat's remote/lender-facing model.
- **IoT sensor ingestion and crop-calendar-driven advisory workflows** (CropIn) — ⚠️ feasible with investment; overlaps directly with items 1.6 and 2.3 above.
- **Multi-crop, multi-district generalization** — ⚠️ feasible with moderate backend work. Today `pilot_crop`/`pilot_district` are effectively hardcoded pilot defaults (`config.py`, `constants.ts`). Generalizing baseline-building and risk thresholds to be config-driven per district/crop (rather than assuming Matiari wheat) is a prerequisite for any "scalability" story told to an evaluator — see §6.

---

## 5. Platform maturity needed to look "fully-fledged" to evaluators

These aren't new user-facing features, but they're what a technical due-diligence reviewer or accelerator judge checks before trusting the accuracy/impact claims above:

- **Automated tests + CI** — already tracked as the #1 item in [`docs/AUDIT-FINDINGS.md`](AUDIT-FINDINGS.md). No serious technical evaluator will take reliability claims at face value without this.
- **Config-driven multi-district/multi-crop support** (§4) — directly maps to the "scalability" criterion that recurs across every accelerator's judging rubric found in this research (see §6).
- **i18n / Urdu support** — already named as a design principle in `docs/UI-UX-INSPIRATION.md` (NFR-1/local credibility) but not yet implemented anywhere in the frontend.
- **Offline-tolerant / low-bandwidth UI mode** — matches the existing NFR-8 ("usable on tablet in branch office or field visit") design principle; a basic PWA cache-and-sync layer would make that real rather than aspirational.
- **Open API / webhook for lender core-systems integration** — turns AgriSat from a standalone dashboard into something a bank's existing loan-origination system can consume automatically; a common ask in ag-fintech partnership conversations.
- **Defined impact metrics** — evaluators and accelerators consistently score on measurable impact (see §6); AgriSat currently collects no aggregate metrics (fields onboarded, risk tiers issued, estimated basis-risk reduction vs. a rainfall-only baseline). Instrumenting these is cheap and directly feeds pitch decks.

---

## 6. Where to take this (accelerators / "world-class evaluators")

Research into 2026 agritech/climate-fintech competitions surfaced a consistent judging pattern — **innovation, scalability, technical feasibility, team, and measurable impact** — across every program checked [[21]](https://opportunitydesk.org/2026/07/21/kcic-cleantech-innovation-competition-2026/) [[22]](https://www.fao.org/e-agriculture/event/global-agriinno-challenge-2026). Ranked by fit for AgriSat specifically:

| Program | Why it fits | Focus |
|---|---|---|
| **Karandaaz Pakistan — Digital Financing for Agriculture Challenge (DFAC)** | Best fit by far: Pakistan-based, explicitly targets digital financing solutions for smallholder farmers, aimed at fintechs/banks/MFIs [[23]](https://karandaaz.com.pk/our-programs/karandaaz-digital/private-sector-engagements/digital-financing-agriculture/) | Ag finance inclusion |
| **Ignite National Incubation Center — Faisalabad (agritech-focused NIC)** | Pakistan-government-backed, sector-specific incubator [[24]](https://moitt.gov.pk/ProjectDetail/ZDZjYzY3ZDAtZTQ2OS00NGRhLTliNmItMzJmMzdiYTY3ZDE0) | Local agritech incubation |
| **FAO Global AgriInno Challenge** | Strong global credibility; verify eligibility carefully — recent cycles have been scoped to Small Island Developing States, so confirm Pakistan qualifies for the specific year applied to [[22]](https://www.fao.org/e-agriculture/event/global-agriinno-challenge-2026) | Global agrifood innovation |
| **THRIVE Global Impact Challenge (SVG Ventures)** | Aspirational — global ag-tech, Silicon Valley pitch stage, real investment on the table, but a higher competitive bar [[25]](https://thriveagrifood.com/thrive-global-impact-challenge-2026/) | Global agtech investment |
| **KCIC Cleantech Innovation Competition** | Relevant if AgriSat is positioned as *climate-adaptation* infrastructure (drought/risk resilience) rather than pure fintech [[26]](https://opportunitydesk.org/2026/07/21/kcic-cleantech-innovation-competition-2026/) | Climate adaptation/mitigation |

**Before applying to any of these**, the honest gaps to close first: real (even small-scale) outcome validation data (§3.1), a defined impact-metrics dashboard (§5), and the config-driven scalability story (§4) — "scalability" and "impact" are named criteria in essentially every program above, and today AgriSat can't yet quantify either beyond "MVP complete."

---

## What not to overpromise

Being credible with evaluators means being precise about limits, not just capabilities:

- **"Real-time"** — say "near-real-time, cloud-dependent for optical / all-weather via SAR," not "real-time." The cloud-cover research is unambiguous that optical revisit ≠ cloud-free observation frequency [[1]](https://www.sciencedirect.com/science/article/pii/S2772375526006301).
- **Automated payout** — stays out of scope. This isn't just a product choice; basis risk is described in the literature as "the central design problem for satellite-enabled insurance," unresolved even by mature players [[15]](https://nhess.copernicus.org/articles/25/913/2025/). Reversing "decision-support only" would need a validated index, a regulated insurance partner, and much more outcome data than AgriSat has today.
- **Yield-prediction accuracy** — a smallholder PlanetScope study reported "up to 60% confidence" [[6]](https://earth.esa.int/eogateway/success-story/predicting-crop-yield-using-planet-data) — respectable for research, not a number to present as production-grade precision. Keep framing risk *tiers* (directional) rather than implying precise yield forecasts.
- **LLM advisory output** — must stay grounded/RAG-based and clearly advisory; generative agriculture advice research explicitly flags accuracy, gender-responsiveness, and ethical governance as open evaluation problems, not solved ones [[27]](https://www.ifpri.org/project/generative-ai-for-agriculture-gaia/).

---

## Suggested sequencing

| Horizon | Items |
|---|---|
| **Now (0–3 months, ✅ items)** | 1.1 cloud-aware messaging, 1.2 SAR soil-moisture index, 1.5 IMERG rainfall supplement, 2.1 SHAP explainability on ML risk layer, 3.2 formalize the composite index, 3.3 quantify settlement-speed as a metric, start §5 impact-metrics instrumentation |
| **Next (3–9 months, ⚠️ items)** | 1.4 PlanetScope licensing/budget decision, 1.3 cloud-gap-filling R&D spike, 2.3 advisory chatbot MVP (RAG-grounded), §4 config-driven multi-district/crop refactor, i18n (Urdu), CI/test suite (cross-ref `AUDIT-FINDINGS.md`) |
| **Later (9+ months, 🔬 items, gated on data/partnerships)** | 1.6 ground-truth sensor pilot, 1.7 PMD data partnership, 2.2 transformer yield model (only once local yield data exists), 3.1 basis-risk dashboard (only once outcome data exists) |

---

## Sources

1. [Sentinel-2 for crop yield estimation: A systematic review — ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2772375526006301)
2. [AI-Driven Integration of Sentinel-1 SAR for High-Resolution Soil Water Content Estimation, Vhembe District](https://doi.org/10.3390/w18040499)
3. [Soil moisture retrieval from Sentinel-1: Lessons learned after more than a decade in orbit — ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0034425725005504)
4. [Cloud gap-filling with deep learning for improved grassland monitoring](https://arxiv.org/html/2403.09554v1)
5. [Planet Agriculture Pricing](https://www.planet.com/pricing/agriculture/)
6. [Predicting crop yield using Planet data — ESA Earth Online](https://earth.esa.int/eogateway/success-story/predicting-crop-yield-using-planet-data)
7. [The Potential of Low-Cost IoT-Enabled Agrometeorological Stations: A Systematic Review — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12526549/)
8. [Pakistan Meteorological Department — Official Website](https://www.pmd.gov.pk/)
9. [AI FAQS: Explainability in Credit Underwriting — FinRegLab](https://finreglab.org/research/ai-faqs-explainability-in-credit-underwriting/)
10. [Explainable AI in Finance: What Regulators Actually Require in 2026](https://www.fluxforce.ai/blog/explainable-ai-in-finance)
11. [Attention-based Multi-modal Deep Learning Model of Spatio-temporal Crop Yield Prediction](https://arxiv.org/html/2604.19217v1)
12. [FARM: Crop Yield Prediction via Regression on Prithvi's Encoder for Satellite Sensing](https://doi.org/10.3390/agriengineering8010002)
13. [Generative AI for Agriculture (GAIA) — IFPRI](https://www.ifpri.org/project/generative-ai-for-agriculture-gaia/)
14. [Leveraging LLMs for GeoAI-enabled digital agro-advisory — Frontiers](https://www.frontiersin.org/journals/remote-sensing/articles/10.3389/frsen.2026.1839369/full)
15. [Satellite-based data for agricultural index insurance: a systematic quantitative literature review — NHESS](https://nhess.copernicus.org/articles/25/913/2025/)
16. [What is parametric crop insurance? — Umbrex Explainers](https://umbrex.com/resources/umbrex-explainers/agriculture-food-explainers/parametric-crop-insurance/)
17. [Triggering change: parametric insurance for farmers — Swiss Re](https://www.swissre.com/reinsurance/property-and-casualty/agriculture-risks/agricultural-insurance-parametric-products.html)
18. [Satellite Services for Parametric Insurance Market Analysis 2026 — New Space Economy](https://newspaceeconomy.ca/2026/05/11/satellite-services-for-parametric-insurance-market-analysis-2026/)
19. [Taranis — Leading Crop Management Software](https://www.taranis.com/)
20. [Top 10 Best Crop Monitoring Software of 2026](https://gitnux.org/best/crop-monitoring-software/)
21. [KCIC Cleantech Innovation Competition 2026](https://opportunitydesk.org/2026/07/21/kcic-cleantech-innovation-competition-2026/)
22. [Global AgriInno Challenge 2026 — FAO](https://www.fao.org/e-agriculture/event/global-agriinno-challenge-2026)
23. [Digital Financing for Agriculture — Karandaaz Pakistan](https://karandaaz.com.pk/our-programs/karandaaz-digital/private-sector-engagements/digital-financing-agriculture/)
24. [National Incubation Centers (NICs) — MoITT](https://moitt.gov.pk/ProjectDetail/ZDZjYzY3ZDAtZTQ2OS00NGRhLTliNmItMzJmMzdiYTY3ZDE0)
25. [THRIVE Global Impact Challenge 2026](https://thriveagrifood.com/thrive-global-impact-challenge-2026/)
26. [KCIC Cleantech Innovation Competition 2026](https://opportunitydesk.org/2026/07/21/kcic-cleantech-innovation-competition-2026/)
27. [Generative AI for Agriculture (GAIA) — IFPRI](https://www.ifpri.org/project/generative-ai-for-agriculture-gaia/)

For the current known-issues backlog (not new features — existing bugs/gaps), see [`AUDIT-FINDINGS.md`](AUDIT-FINDINGS.md). For the system architecture referenced throughout, see [`ARCHITECTURE.md`](ARCHITECTURE.md).
