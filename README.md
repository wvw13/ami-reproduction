# ActiveMemoryIndex reproduction — deployed API candidate

Candidate release **ami-deployment-v1.0-rc1**, algorithm **ami_baseline_v1**, continuing [wvw13/ami-reproduction](https://github.com/wvw13/ami-reproduction) from reproduction-v1.1. This is a reproduction of **Xuhao Lin's [ActiveMemoryIndex](https://github.com/linxuhao/ActiveMemoryIndex)**, not an original memory algorithm. MIT attribution and supplied rc3 provenance remain in LICENSE, ATTRIBUTION.md and upstream/.

The public v1.1 tag did not include the deployed Token API adapter, durable payload conflict checks, provider cache transport or dual budget guard. This candidate supplies those required sources without tuning AMI, prompts, models or retrieval. It is a reviewable release, not a Full-readiness claim and not an OurMemory method.

## Install / free reproduction

Python3.10, user permissions, no sudo:

```bash
python3.10 -m venv .venv
.venv/bin/python -m pip install -r requirements-academic.lock.txt
.venv/bin/python -m pip check
.venv/bin/python deployment/tests/release_mock.py
.venv/bin/python deployment/tests/test_phase_budget_guard.py
.venv/bin/python -m unittest reproduction.test_baseline_cache
```

Only isolated synthetic fakes are used in the listed tests. See [deployment instructions](docs/DEPLOYMENT.md) for mock launch, environment templates, persistence, budget rules and the unresolved fresh real-cache initialization step. These commands do not run official Smoke/Full or publish a tunnel. Provider traffic requires separate explicit authorization.

## Source and deployed behavior

- app/: unchanged from reproduction-v1.1 / frozen ami_baseline_v1; upstream main.py's earlier Textual input-validation patch remains disclosed.
- reproduction/: previously published launcher/fakes/model whitelist, plus the deployed baseline_cache.py and its free tests.
- deployment/: curated service/bootstrap/control/phase guard, scripts, non-secret frozen profile, templates and isolated tests. No data, cache, logs, private config, ngrok binary/token or Windows permits are included.
- docs/DEPLOYED_SOURCE_MANIFEST.json: deployed-to-candidate SHA256 mapping. All nine app files, three required reproduction modules, API service, provider entry, phase guard and profile match their deployed sources. Five deployment launch/import paths are adjusted solely for this repository's layout.
- upstream/: attributed historical materials, not our authorship or reproduced performance claims.

Models: gpt-4o-mini and text-embedding-v4, dimensions1024; raw+facts, recall fusion0.5, raw-first, update version7. Add admission16, Search admission unlimited, one worker, serialized provider calls. No model/retrieval enhancement is claimed.

API: GET /health anonymous; POST /add and /search use **Authorization: Token**. Add returns synchronous200 with exact request/user/session echo and immediate searchability. Same user/request changed payload409; Search top_k100 returns ranked stable id/content evidence, no final answer. Dual guards retain cumulative¥0.05 and phase¥0.02, persistent reservations and first-error stops. These small limits cannot support Full.

## Evidence and limitations

Local contract/persistence and a Cloudflare Windows true synthetic E2E passed previously. Current fixed ngrok domain passed independent Windows Health200 / anonymous Add401 / anonymous Search401 with no login, challenge or redirect. **ngrok correct-Token full Add/Search E2E has not passed yet.** No official Smoke/Full score is claimed.

Current Full is NO-GO: free ngrok quota/idle limits, long Add tails, fault recovery, backpressure, transaction-error handling and joint backup require further work. The unloaded storage-repair candidate is not part of this release, so source fidelity is preserved. Review for Eval Key application is distinct from permission/readiness to run Full.

See [application draft](EVALUATION_ACCESS_DRAFT.md), [changes](CHANGELOG.md) and [attribution](ATTRIBUTION.md). Existing REPRODUCTION_STATUS/TEAM_HANDOFF are historical v1.1 notes, not current production claims. Never publish credentials, runtime files, evaluation memories/questions or private provider endpoints. Future OurMemory algorithm changes must be separately disclosed and validated.
