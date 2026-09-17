# Local equivalents of every CI gate. `make ci` replays the pipeline under act.
#
# Anything CI does that act cannot (artifact upload, and the clean-install job
# that consumes the uploaded artifact) has a local substitute here, so no gate
# is reachable only on a runner.

UV ?= uv
ACT ?= act
# --concurrent-jobs 1 is required locally, not a preference. act defaults to one
# job per CPU and runs the job container with --network host, so every parallel
# matrix leg's service container tries to bind host port 3306 and all but the
# first fail with "port is already allocated". On GitHub each leg gets its own
# runner, so the conflict does not exist there.
# -W pins act to ci.yml. act has no OIDC and ignores job.permissions, so it
# must never pick up publish.yml; file separation plus this flag is the boundary.
ACT_FLAGS ?= --var-file .act.vars --concurrent-jobs 1 -W .github/workflows/ci.yml

# ~/.actrc declares secrets as bare `-s NAME`, which act resolves from the
# environment; `infisical run` is what puts them there. act prompts for any
# that are unset OR empty and then fails on a non-interactive terminal, so the
# secrets have to be present even though ci.yml uses none of them.
#
# Do NOT substitute placeholder values. A bogus GITHUB_TOKEN is worse than an
# absent one: act passes it to git as a credential when fetching actions, and
# the fetch fails with "authentication required" instead of proceeding
# anonymously. Verified the hard way.
INFISICAL ?= infisical
INFISICAL_PROJECT ?= 45365f20-36e8-4d4d-87f3-1554c5ae0615
INFISICAL_ENV ?= prod
ACT_RUNNER ?= $(INFISICAL) run --projectId $(INFISICAL_PROJECT) --env $(INFISICAL_ENV) --

.DEFAULT_GOAL := help
.PHONY: help sync check lint format types test test-db contracts namespace-check build verify-wheel ci ci-job ci-list clean

help: ## Show this help
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-16s %s\n", $$1, $$2}'

sync: ## Install the locked environment
	$(UV) sync --locked --all-extras --dev

check: lint format types test contracts ## Every gate that needs no database

lint: ## ruff check
	$(UV) run ruff check .

format: ## ruff format --check
	$(UV) run ruff format --check .

types: ## mypy --strict
	$(UV) run mypy --strict

test: ## Unit tests (integration skips without DB_HOST)
	$(UV) run pytest -q

test-db: ## Integration tests against a server; set DB_HOST first
	@test -n "$(DB_HOST)" || { echo "set DB_HOST (and DB_PORT/DB_ADMIN_USER/DB_ADMIN_PASSWORD)"; exit 1; }
	$(UV) run pytest -q tests/test_integration.py

contracts: ## Architecture contracts (AD-27, AD-28)
	$(UV) run pytest -q tests/test_architecture.py tests/test_identifiers.py

namespace-check: ## AD-27 alone, including sibling coexistence
	$(UV) run pytest -q tests/test_architecture.py -k "namespace or coexist"

build: ## Build wheel and sdist without development sources
	rm -rf dist
	$(UV) build --no-sources
	$(UV) run python tools/check_dist_metadata.py

verify-wheel: build ## Install the BUILT wheel into an isolated env and import it
	@# A fast standalone equivalent of CI's verify-install job. That job now
	@# runs under act too, so this is convenience rather than the only local
	@# coverage -- `make ci` exercises the same checks across the pipeline.
	@set -eu; \
	wheel=$$(ls dist/*.whl); \
	$(UV) run --isolated --no-project --with "$$wheel" \
	    python -c "from l3io.wp import database; print('import ok', database.__version__)"; \
	$(UV) run --isolated --no-project --with "$$wheel" python -c "\
import importlib.util, sys; \
[sys.exit('base install pulled ' + m) for m in ('boto3','botocore','l3io.wp.config') if importlib.util.find_spec(m) is not None]; \
print('base install is clean')"; \
	$(UV) run --isolated --no-project --with "$$wheel" l3io-wp-database --version

ci: ## Replay the CI pipeline locally under act
	$(ACT_RUNNER) $(ACT) $(ACT_FLAGS)

ci-job: ## Replay one job under act, e.g. make ci-job JOB=static
	@test -n "$(JOB)" || { echo "set JOB, e.g. make ci-job JOB=static"; exit 1; }
	$(ACT_RUNNER) $(ACT) $(ACT_FLAGS) -j $(JOB)

ci-list: ## List the jobs act would run
	$(ACT_RUNNER) $(ACT) $(ACT_FLAGS) -l

clean: ## Remove build output
	rm -rf dist .pytest_cache .mypy_cache .ruff_cache
