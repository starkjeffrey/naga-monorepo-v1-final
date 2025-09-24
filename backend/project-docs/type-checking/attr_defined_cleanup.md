# MyPy attr-defined Cleanup Plan

Scope: backend/apps and api (typecheck-core)

Current snapshot (run `make typecheck-core`):
- Total errors: ~960–970 (local variance due to in-flight fixes)
- By code (approx):
  - attr-defined: ~675
  - var-annotated: ~166
  - assignment/arg-type/operator: small tails

Objective: Reduce attr-defined by 60–70% in core business code without masking legitimate issues.

Approach (phased)
- Phase 1: Contain noisy domains
  - Ensure per-module mypy overrides disable `attr-defined` for Django-heavy layers (models/forms/migrations/validators) — already configured in `pyproject.toml`.
  - Exclude examples/legacy/migration backups from typecheck scope (already aligned via `typecheck-core`).

- Phase 2: Services and views (highest value)
  - Prioritize `apps/*/services.py`, `apps/*/views/*.py`, and `apps/common/*`.
  - Replace dynamic attribute access with typed interfaces where feasible.
  - Use `typing.TYPE_CHECKING` imports for cross-domain types.
  - Prefer `from django.contrib.auth import get_user_model` + concrete model import under TYPE_CHECKING.

- Phase 3: Managers and QuerySets
  - Add minimal return type hints for custom managers/querysets.
  - Where `_ST` appears, add `if TYPE_CHECKING:` model imports and annotate variables explicitly (e.g., `user: User | None`).

- Phase 4: Targeted suppressions
  - Add `# type: ignore[attr-defined]` only where Django magic is intentional and annotation is infeasible.

Tooling
- Run: `make typecheck-attr-report` to get a file-wise breakdown at `scripts/utilities/reports/mypy_attr_defined_report.txt`.

Definition of Done (phase milestone)
- attr-defined reduced by at least 60% in services/views/common modules.
- No loosening of mypy config beyond existing overrides for Django layers.
- Add minimal docs inline where `ignore[attr-defined]` is used.

