# UI/UX Direction — Inspiration & Options

> **Superseded / historical.** M9 shipped as the "Canopy" design system (see `docs/MODULE-PLAN.md`, commit `b20f435`) — the direction chosen was closest to Direction A below. This document is kept for its design rationale and inspiration links, not as a description of the current UI. For the shipped design, read the components under `frontend/src/components` and `frontend/src/index.css` directly.

AgriSat Risk serves **loan officers and underwriters**, not farmers. The UI should feel like a **professional geospatial risk console** — credible to a microfinance bank or insurer — not a generic AI startup dashboard.

**Original state (pre-M9):** Functional dark theme with standard layout. Redesign was **M9** in `MODULE-PLAN.md`.

---

## Design principles (from SRS)

1. **Decision-support framing** — risk outputs never look like automated verdicts (NFR-6)
2. **No GIS expertise assumed** — plain language, obvious next actions (NFR-1)
3. **Map-first** — fields and risk tiers visible at a glance (FR-6.1)
4. **Field-staff context** — usable on tablet in branch office or field visit (NFR-8)
5. **Pakistan / ag-lending credibility** — local context without cliché stock imagery

---

## Direction A — **Institutional GIS console**

*Best for: credibility with banks, SUPARCO-adjacent narrative*

- Large map canvas (~60% viewport), slim data panel on the right
- Muted navy/slate base, risk tiers as saturated pin colors on map
- Typography: strong sans (e.g. **IBM Plex Sans**, **Source Sans 3**)
- Reference feel: Esri ArcGIS Dashboard, Copernicus Browser, NASA Harvest

**Inspiration:**
- [Copernicus Browser](https://browser.dataspace.copernicus.eu/) — clean geospatial chrome
- [NASA Harvest](https://harvest-hub.org/) — ag monitoring, institutional tone
- [Mapbox Studio](https://studio.mapbox.com/) — map + panel balance

---

## Direction B — **Climate fintech / parametric insurance**

*Best for: pitch competitions, global parametric insurance narrative*

- Card-based portfolio summary above fold; map as drill-down
- Light background option with deep green accent (ag + finance trust)
- Risk tiers as labeled chips, not just color dots
- Typography: **DM Sans** + **Fraunces** or **Libre Franklin** for headings

**Inspiration:**
- [IBISA](https://ibisa.cover/) — parametric ag insurance positioning
- [Descartes Underwriting](https://descartesunderwriting.com/) — climate risk B2B
- [Stripe Dashboard](https://dashboard.stripe.com/) — clarity of dense data (adapt palette)

---

## Direction C — **Regional ag-lending ops tool**

*Best for: HBL Microfinance / local MFI pilot story*

- Warm off-white background, earth-tone accents (wheat gold, Punjab green)
- Urdu/English toggle placeholder in header (future i18n)
- Farmer ref ID and loan ref prominent in field list — matches how MFIs work
- Typography: **Noto Sans** (Latin + Urdu ready), **Inter** for UI

**Inspiration:**
- [Kiva](https://www.kiva.org/) — microfinance familiarity (not farmer app — admin tone)
- [One Acre Fund](https://oneacrefund.org/) — smallholder ag, professional not playful
- Pakistan gov / SUPARCO public portals — regional seriousness (avoid cluttered gov UI)

---

## Direction D — **Editorial / report-first**

*Best for: committee demos, PDF export as hero workflow*

- Field detail page reads like a structured risk memo (sections, pull quotes for explanation)
- Chart secondary to narrative text (FR-6.4 plain-language flag)
- Print-friendly CSS for PDF alignment
- Typography: **Georgia** or **Literata** for body, sans for chrome

**Inspiration:**
- [Linear Docs](https://linear.app/docs) — readable structured documents
- Insurance underwriting worksheet layouts (internal tools, not consumer)

---

## Components to rethink (avoid “AI default”)

| Element | Avoid | Prefer |
|---------|-------|--------|
| Sidebar | Generic dark nav with green buttons | Contextual top bar + map tools, or collapsible inspector |
| Stats row | 4 identical cards | Single portfolio strip + map legend integrated |
| Charts | Default Recharts blue/green | Tier-colored points, baseline band as subtle fill |
| Map | OSM only | Custom styled tiles (Carto Positron, Stadia Alidade) + field labels |
| Empty states | Generic illustration | One-line instruction: “Draw boundary or upload GeoJSON” |
| Risk badge | Pill on every row | Map color + tier label in detail only |

---

## Resource links (browse before choosing)

| Resource | URL | Use for |
|----------|-----|---------|
| Landbook (ag/geospatial UI) | https://landbook.net/ | Layout patterns |
| Mobbin (B2B dashboards) | https://mobbin.com/ | Dashboard flows |
| SaaSFrame | https://www.saasframe.io/ | Fintech admin panels |
| Map UI patterns | https://www.mapbox.com/showcase | Map + data pairing |
| Refactoring UI (free) | https://refactoringui.com/ | Spacing, hierarchy, color |
| Laws of UX | https://lawsofux.com/ | Loan-officer usability |
| WCAG contrast checker | https://webaim.org/resources/contrastchecker/ | Risk tier colors |

---

## Map tile options (free tier friendly)

- **CARTO Positron** — light, professional, good for colored risk polygons
- **Stadia Alidade Smooth** — soft neutral base
- **OpenTopoMap** — if terrain context matters for committee story

---

## Outcome (for the record)

M9 implemented a direction close to **A — Institutional GIS console** (large map canvas, slim data panel, satellite basemaps, WCAG AA risk colors) as the "Canopy" design system, without changing backend contracts. Future redesign work should start from the shipped components rather than this brief.
