# User Flow & What the Numbers Mean

A plain-language walkthrough of what AgriSat actually does today, step by step, and — critically — what each output honestly means and doesn't mean. This is the document to hand to anyone (a teammate, an evaluator, a lender pilot partner) who needs to understand the product without reading code. For the technical version of the same flow, see [`ARCHITECTURE.md`](ARCHITECTURE.md#field-processing-data-flow).

## Who uses this

Two roles, both inside a lending/insurance institution — never the farmer directly:

- **Admin** — registers the institution, invites teammates, has full access.
- **Loan officer** — registers fields, views risk, generates reports. Cannot invite other users.

## Step by step

### 1. Institution registers
One person signs up their institution (bank/MFI/insurer) and becomes its admin. This creates a tenant boundary — every field, reading, and report from here on is scoped to this institution and invisible to any other institution using the platform.

**What it means:** this is a multi-tenant SaaS, not a single shared database of fields — Institution A can never see Institution B's data, enforced on every single query (see `ARCHITECTURE.md#tenant-isolation`).

### 2. Admin invites the team
The admin adds loan officers by email. They receive access without needing to be individually approved elsewhere.

### 3. A loan officer registers a field
For a specific farmer/loan, the loan officer either draws the field boundary directly on a satellite basemap or uploads a GeoJSON boundary, then fills in: crop type, sowing date, area, and reference IDs (farmer ref, loan ref) that tie the field back to the institution's own loan records.

**What it means:** this is the only manual data-entry step in the whole flow. Everything downstream — the satellite fetch, the risk score — is fully automated from this point.

### 4. The system processes the field (this is the part that takes time)
Behind the scenes, without the loan officer waiting on a blocked screen:
1. The field's boundary is sent to Google Earth Engine, which pulls Sentinel-1 radar and Sentinel-2 optical imagery (and CHIRPS rainfall) over that exact polygon.
2. If Tier 2 (SEN2SR) is enabled, a local AI model sharpens the Sentinel-2 imagery for more detail.
3. The vegetation/radar signal is compared against a multi-year historical baseline for that crop, at that same point in the growing season, in that district.
4. A statistical anomaly score (explained below) is computed.
5. A machine-learning model double-checks that score and can flag it as more concerning — but never less.
6. The result — a risk tier, a plain-language explanation, and the underlying numbers — is saved.

The UI shows "Satellite analysis in progress" and polls for completion; this typically finishes within a couple of minutes, with an upper bound of about 6 minutes before the UI stops waiting automatically (the loan officer can still check back later — the job keeps running server-side either way, per `docs/AUDIT-FINDINGS.md` item #9's caveat about what happens if this specific screen is left/reloaded).

**What it means:** nothing here is live/streaming. It's a satellite look-back over a fixed window, processed on demand. "Processing" is not a video feed — it's closer to "pulling and analyzing the most recent usable satellite pass."

### 5. The dashboard shows the field's risk tier
Every field lands in one of five tiers:

| Tier | Plain meaning |
|---|---|
| **Normal** | Vegetation/radar signal is close to the historical norm for this crop stage |
| **Watch** | A mild deviation — worth keeping an eye on, not yet actionable |
| **Elevated** | A meaningful deviation from the historical norm |
| **High** | A large deviation from the historical norm |
| **Insufficient data** | The system doesn't have enough reliable information to say anything — this is a deliberate "don't guess" state, not a hidden "normal" |

**What it means (and doesn't):** these tiers describe **how unusual this field's satellite signal is compared to its own crop-stage history** — not a yield forecast, not a loss amount, and not an automated approval/denial. Every risk assessment the system produces carries the line "This is decision-support information only — not an automated loan or claims decision," and that's a load-bearing statement, not boilerplate: see [`FEATURE-ROADMAP.md`](FEATURE-ROADMAP.md#what-not-to-overpromise) for why automated payout specifically stays out of scope.

### 6. The explanation text — how to read it
Each risk assessment includes a generated sentence, e.g. *"Vegetation greenness (NDVI) is 18% below the 5-year average for this crop stage (z-score: -1.4), based on SEN2SR-enhanced Sentinel-2 imagery. Rainfall in this period was below average, consistent with drought stress. This is decision-support information only — not an automated loan or claims decision."*

Breaking that down:
- **"z-score"** — how many standard deviations the current reading is from the historical average at this exact point in the crop's growing cycle. This is the actual statistical basis for the tier; everything else is context around it.
- **Which satellite/index it's based on** is always stated — SEN2SR-enhanced optical, plain Sentinel-2, or Sentinel-1 radar — because they're not interchangeable in reliability. Radar is used specifically when clouds block optical imagery; the explanation says so when that's why radar was used, and adds a note that radar measures surface roughness/moisture, so it should be read alongside optical NDVI when both are available.
- **The rainfall cross-check** either supports the reading ("consistent with drought stress") or questions it ("Rainfall context suggests this anomaly may not be drought-related" — which can actually pull a tier back down from Elevated to Watch, though never all the way to Normal). This exists specifically to reduce false alarms from a single noisy satellite reading.
- **A z-score more extreme than ±8** is treated as a data-quality problem, not a real crop event, and is deliberately routed to "Insufficient data" with a note recommending manual review. In practice, satellite readings that far from a historical norm are far more likely to be a bad pixel, geometry error, or stale baseline than an actual 8-standard-deviation crop event.

### 7. The ML layer — what "it can only make things worse, never better" means
A secondary machine-learning model reviews the same data and can push the risk tier up (e.g. Watch → Elevated) if its own confidence is high enough — but it is structurally not allowed to lower a tier the statistical z-score already flagged. This is a deliberate conservative design: the ML layer can add caution, never remove it. If you're explaining this to a non-technical stakeholder: **the AI model is a second opinion that only ever says "actually, maybe be more worried," never "actually, don't worry."**

### 8. Field imagery — what the picture is and isn't
The dashboard can show an on-demand RGB or NDVI-colored thumbnail of the field, generated fresh from the satellite data. The UI explicitly labels this "processed on-demand … not a live video feed" — worth repeating to anyone who might otherwise assume it's a live camera or drone view. It's a snapshot from the same satellite pass used for the risk calculation, rendered as an image.

**What "clarity" here means and doesn't mean:** Sentinel-2's visible bands are natively ~10m/pixel — real satellite detail doesn't go finer than that no matter how the image is processed. What the app does to make thumbnails look sharp rather than blocky is legitimate display processing on the real sampled pixels: smooth interpolation to a denser grid, contrast normalized to that specific scene's actual reflectance range (so a bright bare-soil scene and a dense-canopy scene both render properly exposed, not one washed out), and a light sharpening pass. None of that invents detail that isn't in the source data — it's the same category of processing any satellite-imagery viewer applies, not a learned/AI reconstruction (that's a meaningfully different thing, and this app doesn't do it for the RGB/NDVI preview images specifically — see `docs/ARCHITECTURE.md` for where a real learned model, SEN2SR, *is* used, which is the vegetation-index pipeline, not these preview thumbnails).

### 9. Reprocessing
A loan officer can manually trigger reprocessing (e.g. after a long gap, or if the field's data looks stale). The system also surfaces a "re-analyze" suggestion when it detects the existing assessment looks stale or was computed under a mismatched baseline.

### 10. Reports
Two export types exist: a single-field PDF (for an individual loan file) and a portfolio-wide PDF/CSV (all of an institution's active fields, with risk-tier counts) — meant to be handed to a credit committee or reinsurer, not just viewed on-screen.

## Accuracy: what today's numbers are actually worth

Being precise here is what makes the rest of this document trustworthy, and it's consistent with the honesty standard set in `FEATURE-ROADMAP.md`:

- **The z-score approach is a relative anomaly detector, not a yield forecaster.** It answers "is this field's vegetation/radar signal unusual for this crop stage, compared to its own district's history" — not "how many bushels/kg will this field produce" or "will this loan default." Treating "High" as "this farmer will default" would be a misreading of what the system computes.
- **There is currently no local ground-truth validation.** AgriSat has not yet been checked against real yield outcomes or real insurance claims for Matiari wheat — the baseline is built from historical satellite data, not historical loss data. Until that validation exists (see `FEATURE-ROADMAP.md` §3.1, the basis-risk dashboard), risk tiers should be presented as **"worth a closer look" signals for a human loan officer**, not as a certified/validated risk score.
- **Optical freshness depends on weather, radar freshness doesn't.** In cloudy/monsoon periods, the "latest reading" behind a risk tier may be a Sentinel-1 radar pass rather than recent optical imagery — still useful, but a different kind of measurement (surface moisture/roughness vs. greenness), and the system says so in the explanation text rather than hiding the substitution.
- **"Insufficient data" is a feature, not a failure.** Roughly a third of the failure modes in `risk_engine.py` route here on purpose (no readings, no baseline, mismatched data-tier baseline, or an implausibly extreme z-score) — the system is designed to say "I don't know" rather than guess, which is the correct behavior for a decision-support tool but does mean not every field will always have a confident answer.
- **The ML layer's confidence threshold is a tuning knob (`ML_RISK_CONFIDENCE_MIN`), not a guarantee.** A higher threshold means fewer ML-driven upgrades but higher confidence in the ones that happen; this should be revisited once real outcome data exists to check whether the threshold is well-calibrated.

## Where this leads next

With this flow and its honesty caveats written down, the natural next steps (per your sequencing) are: (1) work through the fixes already logged in [`AUDIT-FINDINGS.md`](AUDIT-FINDINGS.md), starting with the small/low-risk ones, and (2) start development on the "Now" horizon items in [`FEATURE-ROADMAP.md`](FEATURE-ROADMAP.md#suggested-sequencing) that are free to build per [`FREE-VS-PAID-RESOURCES.md`](FREE-VS-PAID-RESOURCES.md).
