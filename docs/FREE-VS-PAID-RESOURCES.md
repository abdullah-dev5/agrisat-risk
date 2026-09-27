# Free vs. Paid Resources

Everything in [`FEATURE-ROADMAP.md`](FEATURE-ROADMAP.md) is tagged by engineering feasibility. This doc tags the same landscape by **cost** — what's genuinely free to build on today with zero budget, and what to swap in once there's money. Read the first section before anything else: it's a licensing boundary on the *existing, already-shipped* pipeline, not a future feature.

## 0. The one that isn't optional to know: Google Earth Engine's commercial boundary

**Current decision (2026-09-27):** AgriSat is operating in a research/development phase with no paying institution yet, so using Earth Engine's noncommercial tier is the correct and compliant choice right now — no action needed today. Revisit this the moment a real institution is signed as a paying customer, not before. The rest of this section stays as a reference for that future trigger point.

AgriSat's Tier 3 pipeline (Sentinel-1/2 + CHIRPS) runs entirely on Google Earth Engine. Earth Engine's noncommercial tiers are genuinely free, but scoped:

| Tier | Quota | Requirements | Fits AgriSat today? |
|---|---|---|---|
| **Community** (default) | 150 EECU-hours/month | None — automatic for any verified noncommercial project | ✅ Fine for local dev + demoing to evaluators |
| **Contributor** | 1,000 EECU-hours/month | A billing account attached (Earth Engine itself stays free) | ✅ Good next step once dev usage grows — still no cost |
| **Partner** | 100,000 EECU-hours/month | Separate application; limited to orgs doing high-impact climate/sustainability work | ⚠️ Possible if positioned as climate-adaptation infrastructure (ties into the KCIC angle in the roadmap), but not guaranteed |

The line that actually matters: **noncommercial-tier users may not charge or receive compensation from a commercial entity for applications or outputs built with Earth Engine.** The moment a lender or insurer pays for a AgriSat risk report, that condition is violated — Earth Engine at that point requires the **paid commercial plan** (pay-as-you-go compute, no more free quota).

**What this means practically:**
- **Now (pilot/demo/pitch phase, no paying customer yet): free tier is completely fine and correctly used.** No action needed.
- **Before signing a first paying institution: budget for Earth Engine commercial**, or pursue one of the two hedges below.
- **Hedge 1 — apply for Partner tier** if you can credibly frame AgriSat as climate-adaptation infrastructure for smallholder resilience, not purely commercial fintech. Free, but not guaranteed and re-verified annually.
- **Hedge 2 — migrate the raw Sentinel-1/2 pull off Earth Engine onto the Copernicus Data Space Ecosystem** (ESA/EU, see §1 below), which is free for *all* users including commercial ones, with quotas rather than a commercial-use ban. This is a real migration (Earth Engine's Python `ee.Image` API would be replaced by openEO/Sentinel Hub/STAC calls in `services/tiers/gee_client.py`), not a config flag — worth scoping once you're closer to a paying pilot, not urgent today.

## 1. Satellite/weather data

| Resource | Free today? | Condition that changes that | Paid/alternative path |
|---|---|---|---|
| Sentinel-1/2 + CHIRPS via **Google Earth Engine** | ✅ free (noncommercial tiers) | Stops being compliant once a paying customer is billed for outputs | Earth Engine commercial pay-as-you-go, **or** migrate to Copernicus Data Space Ecosystem |
| **Copernicus Data Space Ecosystem** (Sentinel Hub / openEO / STAC APIs) | ✅ free for all users, commercial included, with usage quotas | Only if you need large-scale bulk processing beyond the free quota | Paid Sentinel Hub plan (pay-as-you-go, no free-tier commercial ban) — the resilient long-term alternative to Earth Engine |
| **CHIRPS rainfall** | ✅ free regardless of path — public-domain climate data, pullable directly from CHIRPS' own servers, not exclusively tied to Earth Engine | Never really stops being free | N/A |
| **NASA IMERG rainfall** (roadmap item 1.5, faster cadence than CHIRPS) | ✅ free via NASA GES DISC or Earth Engine's public IMERG mirror | Never really stops being free | N/A |
| **PlanetScope** (Tier 1, roadmap item 1.4) | ❌ never free for a commercial deliverable | N/A — always paid | Planet's Agriculture plan (per-hectare/subscription pricing) once a lender partner or grant funds it. No 3 m-resolution free substitute exists; keep deferred until funded. |
| **Sentinel-1 SAR soil moisture** (roadmap item 1.2) | ✅ free — same GEE/Copernicus source already used, no new vendor | Same as the GEE line above | Same as the GEE/Copernicus line above |

## 2. ML / AI

| Resource | Free today? | Paid upgrade path |
|---|---|---|
| **SHAP explainability** (roadmap item 2.1) | ✅ fully free, open-source Python, runs locally — no external service at all | None needed, ever |
| **Existing z-score risk engine + gradient-boosted ML layer** | ✅ fully free — scikit-learn, runs in-process on your own hardware | None needed |
| **LLM advisory chatbot** (roadmap item 2.3) | ✅ prototype for $0: Google Gemini API has a standing free tier (no credit card), OpenRouter offers free access to large open-weight models (e.g. Llama 3.1 405B), Groq's free tier, or self-host an open-weight model with Ollama | Once past prototyping: open-weight models are cheap even paid (~$0.02–0.10 per 1M tokens on OpenRouter for Llama-class models) — low-regret to start free and pay only if/when volume needs it |
| **Cloud-gap-filling model** (roadmap item 1.3) | ✅ free to build — open research method, trainable on your own GEE/Copernicus data with open-source deep learning libraries | Only cost is your own compute time/GPU if you don't already have one |
| **Transformer yield model** (roadmap item 2.2 — gated on data, not budget) | ✅ free to build once you have labeled data | Same — the blocker is data, not money |

## 3. Ground-truth / hardware

| Resource | Free today? | Notes |
|---|---|---|
| **DIY soil-moisture sensors** (roadmap item 1.6) | ⚠️ low-cost, not free — capacitive sensors ~$2–10 each, an Arduino-class controller ~$20–40 | Real hardware cost, but small — a 10–20 sensor pilot is a few hundred dollars, not a grant-sized ask |
| **Commercial ag-sensor systems** | ❌ paid, $150–5,000 per unit | Only worth it once the DIY pilot proves the value and you need field durability/support contracts |
| **PMD data partnership** (roadmap item 1.7) | Unknown — no public free API found; likely requires an MOU | Treat as a relationship to build, not a budget line yet |

## 4. Engineering infrastructure

| Resource | Free today? | Notes |
|---|---|---|
| **pytest / Vitest / ESLint / Prettier** (closing the testing/CI gap in `AUDIT-FINDINGS.md`) | ✅ fully free, open-source | No cost ever |
| **GitHub Actions CI** | ✅ free tier is generous at this project's scale (public repos: unlimited; private repos: a large monthly minutes allowance) | Only becomes a cost center at a scale far beyond a pilot |
| **Hosting/compute for the backend** | Depends on where it's deployed — not researched here since it's deployment-specific | Budget this separately when picking a production host |

## Bottom line

Everything on the **"Now" and most of the "Next" horizon** in `FEATURE-ROADMAP.md` can be built and even demoed to evaluators at $0 — the free tiers above are real, current, and not artificially crippled for prototyping. The two genuine budget lines to plan for, in order of urgency, are:

1. **Earth Engine commercial billing (or the Copernicus migration)** — triggered by your first paying institution, not by technical scale. This is the one to flag to any accelerator/investor conversation as "known cost at commercial launch," so it doesn't look like an oversight later.
2. **PlanetScope licensing** — only needed if a lender partner specifically requires 3 m-resolution imagery; otherwise stays deferred indefinitely with no loss of core functionality.

Everything else (DIY sensors, LLM prototyping, ML/explainability work, testing/CI) is a rounding error by comparison.
