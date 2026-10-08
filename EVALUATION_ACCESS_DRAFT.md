# Evaluation Access application — not submitted

System: **ActiveMemoryIndex Reproduction**. Candidate version/tag: **ami-deployment-v1.0-rc1**; algorithm profile: **ami_baseline_v1**. The tag is a proposal pending owner approval; use the final resolved public commit, never an unpublished hash as if already available.

Track/group: **Textual Memory / Open-source Methods**.

- Add: https://commute-scarecrow-passenger.ngrok-free.dev/add
- Search: https://commute-scarecrow-passenger.ngrok-free.dev/search
- Health: https://commute-scarecrow-passenger.ngrok-free.dev/health (anonymous GET)
- Authentication: Authorization: Token <Memory System Key>. Supply the actual Memory System Key only through the official protected credential field, not this draft/repository/email/chat. ngrok Authtoken and provider keys are not supplied to AML.
- Repository: https://github.com/wvw13/ami-reproduction ; continue the existing project, not a new repository. Candidate branch task-b/deployment-v1.0-rc1; after approval publish and resolve the immutable commit/tag.
- Deployment source mapping: docs/DEPLOYED_SOURCE_MANIFEST.json. Existing live instance retains its own paths/private state; candidate relocates five import/interpreter paths, while app/API/provider/phase logic remains unchanged. No online restart is implied.
- Original work: Xuhao Lin's ActiveMemoryIndex, MIT Copyright(c)2026 Xuhao Lin; supplied academic-v4-20261005-rc3 snapshot pinned by file hashes, exact upstream commit not recovered. Technical-report title/DOI and verification limits are disclosed in ATTRIBUTION.md.
- Method: AMI raw turns + facts, recall fusion, neighbors/raw-first selection and explicit-update withholding. No new algorithm contribution claimed. Current engineering additions are validation, Token transport, payload conflict protection, namespace, provider cache, persistent dual-budget reservations and rootless launch. Future OurMemory needs a separate version and method disclosure.
- Models: gpt-4o-mini; text-embedding-v4,1024 dimensions. Exact response whitelist retained, no provider fallback/model switching.
- Verified: local free contract/idempotency/isolation/restart tests; prior Cloudflare Windows correct-Token real Add/Search E2E; ngrok independent Windows Health200/anonymous Add401/Search401 with no login/challenge/redirect.
- Not verified: **ngrok correct-Token complete Add/Search E2E**, official AML Smoke/Full, long-history tail and Full capacity. Do not label previous tests as official Smoke or ngrok real E2E.
- Limits: one worker, global serial Add;16 admitted Add, Search admission unlimited, provider calls serialized; queue/backup/recovery not production-qualified. ngrok free20k requests/month,1GB outbound,5-minute idle timeout. Cumulative¥0.05 plus phase¥0.02 guards remain; no formal run budget authorized. Health is liveness only; provider first-error stop and crash reservation are fail-closed.
- Installation: Python3.10, locked lightweight dependencies; see docs/DEPLOYMENT.md. Mock works without provider credentials; real cold cache warm-up still needs separately authorized initialization. No datasets/runtime state are published.
- Contact/team/organization/public display permissions: **owner must supply and confirm**.

## A — Before applying for Eval Key

Owner reviews candidate/security notes and author disclosure; approves publishing into this existing repository; finalizes immutable commit/tag and matching source manifest; confirms contact/system name. Submit stable URLs, secure authentication, honest limited capacity and Full-NO-GO disclosure. Ask reviewers whether these limited integration conditions are acceptable; approval is not guaranteed. A bounded correct-Token free invalid-payload check would strengthen auth evidence but requires separate permission because this task does not read keys. Completing real ngrok E2E before application is recommended, not asserted here as a universal official eligibility requirement.

## B — After Eval Key, before Smoke

Obtain explicit Smoke and model-cost authorization; estimate Smoke payload/cost against both existing budget layers, never reset/bypass either. Complete ngrok correct-Token chain/authorized minimal E2E if not done, confirm cloud Full Capture off, fixed version, health/readiness, stop handling and privacy. Choose conservative concurrency supported by tests; do not use Smoke to debug an unstable interface. If budget cannot cover Smoke, seek approval for a separately tracked phase, not an automatic increase.

## C — Before Full

Resolve request/byte quotas,5-minute idle risk,long Add tails,backpressure,provider bounded recovery,write-error transactions,joint backup/recovery,supervision and resources. Agree full capacity and budget; freeze public/deployed version before formal acceptance. Official Smoke must pass first. No Full run is authorized by publication or Eval Key issuance.

Current production decision is NO-GO for Full, **not a claim that material preparation or an Eval Key application is forbidden**. All submissions, paid tests, budget changes and Smoke/Full require separate owner authorization.
