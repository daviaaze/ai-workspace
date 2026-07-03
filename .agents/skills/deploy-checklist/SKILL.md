---
name: deploy-checklist
description: Generate deployment readiness and post-deploy verification checklists. Use when the user says deploy checklist, ready to deploy, release, staging, production, or post-deploy verification.
---

# Deploy Checklist Workflow

## Trigger
Deploy, release, staging, production, deploy checklist, post-deploy verification.

## Workflow

### 1. Risk + Context Assessment

Analyze changes since last release and identify high-risk areas: DB, infra,
dependencies, feature flags, external services.

**Assign risk score** using `review-risk-framework` — this determines
checklist depth:

- Score 1-2: light checklist (smoke test, error rates, quick eyeball)
- Score 3: standard checklist (staging smoke, critical journeys, latency)
- Score 4-5: full checklist (rollback rehearsed, DR reviewed, team on standby)

### 2. Pre-Deploy Checklist

- **No junk in trunk** — every commit merged to main must be planned for
  release. If anything merged isn't ready to go to prod, **roll it back** —
  do not leave code hanging around in main for someone else to pick up.
- **Tests green** — CI passing on the merge commit to main.
- **Review approved** — at least one human reviewer has approved. Claude bot
  reviews are supplementary.
- **Dependencies in-place** — per the Engineering Principles, all dependencies
  must be live in production BEFORE code is merged to main. Never merge code
  that depends on unreleased services.
- **Migrations tested** — DB migrations have been run against staging and
  verified. For risk-4+ changes, test migration rollback.
- **Feature flags ready** — if this is behind a flag, the flag is configured
  in all environments and defaults to OFF.
- **Rollback documented** — for risk-4+ changes, a rollback plan is written
  and accessible to the on-call engineer.

### 3. Deploy Order (cross-service changes)

When changes span multiple services, deploy in dependency order as per the
Engineering Principles:

1. Contract/schema changes first
2. Upstream services (connectors, data pipelines)
3. Backend API services
4. Admin/internal tools
5. Customer-facing frontends

**Never deploy a consumer before its upstream dependencies are live.**

### 4. Deploy Execution

- **Staging first** — deploy to staging, smoke test, confirm behavior.
- **Service owner releases** — the service owner (or team lead with admin
  access) should execute the production deployment.
- **Zero-downtime** — any change that locks a database table can only be
  released if the lock will be short enough to not impact customer requests.
- **Infrastructure changes** — test infrastructure changes in staging first,
  then roll to production as if they were code.
- **Smoke test** — after deploy, verify critical paths work:
  - `/up` and `/health` endpoints
  - Core user journeys
  - Error rates and latency

### 5. Post-Deploy Verification

- **Critical journeys** — verify the deployed feature works in production
  (both automated smoke tests + manual spot-check).
- **Error rates** — check Datadog for any spike in 5xx errors, latency
  degradation, or unexpected log patterns.
- **Staging AND production** — per the Principles, changes must be checked in
  both environments. This doesn't require exhaustive manual testing, but
  thoughtful validation is a must.
- **Rollback readiness** — for risk-4+ deploys, confirm the on-call engineer
  knows where the rollback runbook lives.
- **Runbook/team updates** — update team docs, runbooks, or Confluence if the
  change introduces new operational procedures.

### 6. If Something Goes Wrong

- **Roll back, don't fix forward** — per the Principles, if it doesn't go to
  plan, roll it back. Do not leave broken code in master while debugging.
- **Root cause analysis** — for P1/P2 incidents, capture an RCA in the TEC
  Confluence space.
- **Regression test** — when a bug is fixed, add a test to prevent it from
  reappearing.

## Escalation

Ask before prod migrations, infra apply, CI/CD changes, or destructive
operations. Risk-4+ changes require explicit confirmation before any deploy
step.
