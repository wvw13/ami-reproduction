"""Deployment-only persistent phase ceiling; no AMI changes."""
import json
import os
from pathlib import Path


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def restrict_budget(base, root):
    directory = Path(root) / 'run/windows-real-e2e'
    permit_path = directory / 'server-phase-budget.json'
    state_path = directory / 'phase-cost.json'

    class PhaseBudget(base):
        def request(self, request, model, endpoint):
            with self.lock:
                self.check()
                permit = json.loads(permit_path.read_text())
                if permit.get('enabled') is not True or permit.get('limit_RMB') != .02:
                    self.halt('phase_budget_not_authorized')
                baseline = float(permit['baseline_RMB'])
                # CacheBudget sums float ledger rows; compare at the ledger's
                # persisted 10-decimal RMB precision to avoid false stops.
                total = round(self.total, 10)
                if not 0 <= baseline <= total:
                    self.halt('phase_baseline_invalid')
                previous = json.loads(state_path.read_text()) if state_path.exists() else {}
                if previous and (previous['baseline_RMB'] != baseline or previous['limit_RMB'] != .02):
                    self.halt('phase_baseline_changed')
                if previous.get('pending_reservation_RMB', 0):
                    self.halt('phase_previous_request_unresolved')
                spent = max(round(total - baseline, 10), previous.get('spent_RMB', 0))
                payload = json.loads(request.content)
                reserve = ((len(request.content) + 1024) * (.5 if model == 'text-embedding-v4' else .15)
                           + payload.get('max_tokens', 0) * .6) / 1e6
                if self.total + reserve > .05:
                    self.halt('local_RMB_0.05_budget_limit')
                if spent + reserve > .02:
                    self.halt('phase_RMB_0.02_reservation_exceeded')
                state = dict(baseline_RMB=baseline, limit_RMB=.02, spent_RMB=spent,
                             cumulative_RMB=self.total, pending_reservation_RMB=reserve)
                # Persist the reservation before any provider send. An interrupted
                # request remains fail-closed across service restarts.
                atomic_json(state_path, state)
                before = self.total
                try:
                    result = super().request(request, model, endpoint)
                except Exception:
                    # The underlying ledger charges network errors conservatively.
                    # If no charge was recorded, retain the unresolved reservation.
                    if self.total > before:
                        state.update(spent_RMB=max(spent, self.total-baseline),
                                     cumulative_RMB=self.total, pending_reservation_RMB=0)
                        atomic_json(state_path, state)
                    raise
                state.update(spent_RMB=max(spent, self.total-baseline),
                             cumulative_RMB=self.total, pending_reservation_RMB=0)
                atomic_json(state_path, state)
                return result
    return PhaseBudget
