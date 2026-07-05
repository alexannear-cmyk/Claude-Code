# Strategy Assessment: India Labor Arbitrage Tracking Approach

**Prepared for:** Finance Senior Manager, Technology Finance (CTO Organization)
**Purpose:** Evaluate the proposed two-metric tracking framework for the India Global Capability Center (GCC) ramp-up and labor arbitrage program; recommend any additions before templates are distributed to the ~8 org finance partners.

---

## Bottom line

Your two headline metrics — **India hires** and **labor arbitrage achievement (LE reductions vs. monthly commitment)** — are the right ones. They cover the two halves of the program's economics: the build side (are we standing up the India capability on pace and on cost?) and the payoff side (are the committed reductions actually being realized in the P&L?). They also map directly to what leadership committed to and what corporate reporting will ask for. Keep them as the headline pair.

The refinement is not to add more headline metrics, but to (a) make one structural distinction inside the savings metric, and (b) surround the pair with a small set of **diagnostic / leading indicators** that explain variances and give you early warning — collected in the same monthly template so they cost the orgs almost nothing extra.

---

## 1. Why the two metrics are correct

- **They are the program's cause and effect.** India hiring is the input; labor arbitrage is the output. Every other measure (comp variance, attrition, training ramp) is a driver of one of these two.
- **They are the commitment currency.** You pushed monthly targets for exactly these items into org forecasts. Tracking anything else as "headline" would dilute accountability against what was committed.
- **They are independently sourced, which is a control.** Hires come from PlanIt (system of record, you can pull it yourself); arbitrage realization comes from org attestation. Where the two stories diverge — hiring on track, savings lagging — you have a genuine finding, not a data question.

## 2. The one structural distinction to build in: in-year savings vs. exit run-rate

"Labor arbitrage achievement" should be tracked two ways from day one — but with a clear hierarchy between them:

- **In-year (period) savings $ — the commitment.** The technology enterprise committed in-year savings targets by year for 2025–2029, now allocated as commitments by sub-organization. In-year achievement vs. those targets is the accountability metric, full stop. This is what corporate reporting and the quarterly forecast measure.
- **Exit run-rate $ — a diagnostic.** The annualized value of reductions in place at period end. It tells you whether the mix shift is durable and whether a recovery plan is credible — but it is context, never a substitute.

The distinction matters because timing slips destroy in-year savings while leaving run-rate intact (a reduction landing in November instead of March is ~90% gone for the year but 100% intact as run-rate). Tracking both lets you separate a timing problem from a structural one. The critical guardrail — written into the Guiding Principles (§6.2) — is that **run-rate can never offset or excuse an in-year miss**: an org may not argue it is "a little behind but fine because exit rate is on track." A behind org is behind; run-rate belongs in the recovery-plan commentary, not in the scorekeeping. The prototype workbook carries both views with in-year as the headline.

## 3. The decoupling risk your net metric already covers — keep it net

The single most dangerous pattern in GCC programs is **hiring on pace while reductions lag**. For that period, the program is a cost *increase*: you're paying India comp plus the undiminished legacy cost. Because you chose to have orgs report gross reductions by labor type *and* India cost adds, with the tracker computing **net labor arbitrage**, this pattern is exposed automatically every month. Resist any future simplification to a single self-reported "savings" number — the gross/net decomposition is what tells you *why* a month missed.

## 4. Recommended secondary (diagnostic) metrics

Collected in the same template, not new commitments. Ordered by importance:

| # | Metric | Why it matters | Source |
|---|--------|----------------|--------|
| 1 | **Reduction "leakage" flag** — professional services or contractor spend reappearing in other cost centers / expense lines after a claimed reduction | The #1 realization risk in these programs. A reduction isn't real if the work (and spend) migrated elsewhere in the org. Ask orgs to attest monthly; audit via expense-line trend when you suspect it. | Org attestation + your spot checks |
| 2 | **India loaded comp vs. plan** (avg per hire) | Comp inflation in India tech hubs is real; 10–15% drift on 1,500 heads materially erodes the arbitrage math. You can pull this from PlanIt. | PlanIt |
| 3 | **India attrition / regretted attrition** | High attrition silently converts "1,500 hires" into 1,900 requisitions and stretches time-to-productivity. Early-tenure attrition is the leading indicator. | PlanIt / HR |
| 4 | **Time-to-productivity / training ramp status** | Determines when a hire actually displaces a legacy resource. If ramp runs long, reductions slip even with hiring on pace. | Org input (months, or % of hires "productive") |
| 5 | **One-time transition costs** (severance, knowledge transfer, parallel-run, seat/facility build-out) | Needed for the true net program economics and to prevent orgs from netting these against gross savings inconsistently. Track separately; never inside the run-rate savings number. | Org input |
| 6 | **Monthly RAG + mandatory commentary on material variances** | The qualitative early-warning layer; makes the consolidation a management tool rather than a scorecard. | Org input |
| 7 | **Offer acceptance rate / pipeline health** (optional, from TA) | Leading indicator 1–2 quarters ahead of a hiring miss. Worth a quarterly pull rather than monthly org input. | Talent Acquisition |

Items 1, 5, and 6 are input fields in the prototype workbook. Items 2 and 3 you can populate centrally from PlanIt (the workbook has rows for them marked "central fill"). Items 4 and 7 are lightweight org inputs you can drop if the template feels heavy.

## 5. Watch-outs on the operating model

- **Baseline discipline.** The monthly targets you pushed to forecasts are the baseline. All variances measure against *that*, never against prior year or against a re-forecast — otherwise the target quietly walks. Changes to the baseline only via a formal change request (covered in the Guiding Principles draft).
- **Attestation, not aspiration.** Because arbitrage realization is self-reported, require the org finance partner to attest that reported reductions are visible in the GL (cost center + expense line identified), not just "planned." The Guiding Principles draft makes this a rule.
- **Don't let the template grow.** Two headline metrics, ~5 diagnostic rows, one commentary box. Every additional field lowers submission quality and timeliness across 8 orgs.
- **Plan the handoff now.** Since you intend to push this to the broader technology finance team, the workbook is built so org tabs are identical and org names live in one Setup cell each — a teammate can take over consolidation without reverse-engineering formulas.

---

*Companion documents: `India_Labor_Arbitrage_Tracker.xlsx` (prototype consolidation workbook) and `Guiding_Principles_DRAFT.md` (rules of the road for review before leadership discussion).*
