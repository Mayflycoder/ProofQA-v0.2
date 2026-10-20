# ChangeRipple v0.1 — synthetic cross-functional impact explorer

**Status: prototype only.** ChangeRipple is a browser-only, localStorage-persisted demonstration built inside the existing ProofQA v0.2 repository at `apps/changeripple/`. It is **not** a certified QMS, compliance/validation tool, a production record system, or part of the ProofQA Python CLI.

## The problem

Internal procedure changes, supplier changes, and NC/CAPA actions often have dependencies spanning PQA, Warehouse, QA, Process Engineering, Quality NPI, Technical Support, Supplier Quality, Validation, QC Lab, Training, and Regulatory. A review process can miss untracked test methods, procedures, training, products or owners.

## What works in this prototype

- Three seeded fictional scenarios: supplier material formulation, internal procedure revision, and NC/CAPA.
- A synthetic, directional dependency graph; deterministic up-to-three-hop impact propagation on *explicitly mapped* links.
- Exact provenance paths for every candidate impact; direct explicitly required mappings distinguished from suggested reviews.
- Departmental review-action tracking, impact dispositions, evidence notes, and an NC/CAPA completeness checklist.
- Closure blocked by pending impacts, missing review evidence, unreviewed coverage warnings, or incomplete CAPA verification.
- Coverage checks for unowned/disconnected nodes and missing supplier/test/risk relationships.
- Add a synthetic graph edge and recompute existing assessments while preserving recorded reviewer decisions.
- Browser-local state, reset demo, printable assessment report, JSON and CSV export.
- All data is invented; no login, API, hosted database, document import, or external AI calls.

## Run

Open `apps/changeripple/index.html` through a local HTTP server (ES modules require HTTP, not file://).

```bash
cd apps/changeripple
python -m http.server 8765 --bind 127.0.0.1
# open http://127.0.0.1:8765
```

Run deterministic domain tests (Node.js 22+):

```bash
node --test apps/changeripple/engine.test.mjs
```

The repository root contains `netlify.toml`, setting the Netlify publish folder to `apps/changeripple` with no build command. In Netlify, connect **Mayflycoder/ProofQA-v0.2**, production branch `main`, and use the root settings. A branch must be merged to `main` before a production Git-connected Netlify site receives this app.

## Safety limits

**Do not enter employer records, confidential SOPs, supplier data or actual patient/product information.** Everything remains in the browser's localStorage but the application has no enterprise access controls or validated retention, and browser data is not a controlled quality record. The absence of a mapped relationship is not evidence of no impact.

The graph is incomplete by design. A "required" review reflects only a configured link, not a regulatory determination. Any real deployment for enterprise quality use would require proven source connections, roles, authentication, tenant isolation, data lineage, e-signatures where needed, audit trails, change management, model-validation studies and human quality approval.

The existing ProofQA browser QA scanner remains separate; no claim is made that ChangeRipple uses the CLI to validate regulated workflows.
