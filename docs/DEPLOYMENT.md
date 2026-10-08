# Rootless deployment and reproduction

This release reproduces the **existing** `ami_baseline_v1` service. It is not a production reliability upgrade. `app/`, `service.py`, `run_service.py`, `phase_budget_guard.py` and `baseline_cache.py` retain their deployed behavior. Five import/interpreter path changes support the repository layout; exact source mapping is in DEPLOYED_SOURCE_MANIFEST.json.

## Install and free checks

From this repository root, using Python 3.10:

```bash
python3.10 -m venv .venv
.venv/bin/python -m pip install -r requirements-academic.lock.txt
.venv/bin/python -m pip check
.venv/bin/python deployment/tests/release_mock.py
.venv/bin/python deployment/tests/test_phase_budget_guard.py
.venv/bin/python -m unittest reproduction.test_baseline_cache
```

No sudo, Docker or local model weights are required. Installation needs a package index or an authorized wheelhouse; no private pip credentials are supplied. The release HTTP test uses SDK fakes and an isolated temporary repository/runtime copy, permits loopback client traffic only, checks restart/persistence/idempotency/isolation, and stops only its own mock process. It never contacts the live service or a provider.

For a persistent **synthetic mock instance only**, at a separate unused port:

```bash
.venv/bin/python deployment/prepare_runtime.py --mock
./deployment/start.sh --mock --port 18012
./deployment/check.sh --mock
./deployment/stop.sh --mock
```

Use Token authentication with the clearly marked fixture token in your private mock file, never a real Memory System Key. Fakes do not demonstrate model accuracy.

## Existing real instance / future authorized installation

Do not point this checkout at research data or an existing production runtime. Do not replace the running instance as part of publishing this release. The production server retains its current private data/cache/namespace, historical ledgers and stop records.

1. Use `prepare_runtime.py` to create missing directories only. Templates are under `deployment/templates/`; securely prepare private/provider.env and private/memory.env with mode0600 and directory0700. Provider endpoint and keys are intentionally blank. `MEMORY_SYSTEM_KEY` can instead be supplied through a protected environment.
2. Preserve deployed algorithm settings from profile.env in provider.env; credentials and actual endpoints remain private. Models are gpt-4o-mini / text-embedding-v4, dimensions1024; exact accepted response identities are in reproduction/real_minimal.py.
3. The cumulative ceiling is ¥0.05 and the independent phase ceiling ¥0.02. The server-phase template is deliberately disabled. Enabling a phase or setting its baseline requires separate cost authorization and truthful ledger reconciliation; never copy baseline=0 onto an existing ledger, clear a stop or remove an unresolved reservation.
4. **Cold real startup is not yet a one-command workflow:** the deployed entry warms up cache-only before enabling provider traffic. A fresh empty cache fails closed. An explicitly authorized budgeted warm-up initialization procedure is still required; no real cache is published and no bypass is added here. This release test does not spend money to validate cold startup.
5. For an already correctly provisioned independent real runtime, start/check/stop use the same scripts without --mock, always loopback and one worker. Choosing a production port and loading a release into the real server requires separate approval. The existing instance continues on38563.

The real provider adapter remains first-error stop / zero retry. The candidate does not include the unloaded transaction-repair wrapper, budget increases, supervision or new algorithm switches. API Health is liveness, not a promise of provider/budget readiness. Authenticated requests cost money; do not use upstream scripts/smoke_contract.py as an unapproved paid probe.

## API and operations

- GET /health: anonymous200.
- POST /add: request_id/messages/user_id/session_id; success200 after durable write and immediate searchability; exactecho; same user/request changed payload409.
- POST /search: query/user_id/top_k, optional options; ranked stable id/content records, formal top_k100, no final answer.
- Authorization: Token, not the older Bearer launcher's default. Namespace: aml-local-ami-baseline-v1:; internal persistence paths are confined to deployment/data and cache.
- SQLite memory database uses WAL; the contract database uses DELETE journal. Preserve both and their journal files, and coordinate backup with budget state. No backup/recovery automation is claimed.
- Add is serial, admission16, Search admission unlimited; the provider budget lock further serializes calls. These are settings, not measured Full capacity. No multiworker launch is supported by this release.

Current public ngrok domain is separately operated, not bundled or started by these scripts. ngrok credentials/binary/state and Windows permits are excluded. It has5-minute idle limits and free quotas; current Full remains NO-GO. The repository version supports review for Eval Key application, not an automatic Full run.
