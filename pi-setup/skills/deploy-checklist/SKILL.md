---
name: deploy-checklist
description: Generate deployment readiness and post-deploy verification checklists. Use when the user says deploy checklist, ready to deploy, release, staging, production, or post-deploy verification.
---

# Deploy Checklist Workflow

## Workflow

1. Analyze changes since last release and identify high-risk areas: DB, infra, dependencies, feature flags, external services.
2. Generate checklist:
   - Pre-deploy: tests green, review approved, migrations tested, flags ready, rollback documented.
   - Deploy: staging first, smoke tests, production, monitor.
   - Post-deploy: critical journeys, error rates, latency, runbook/team updates.
3. Include environment-specific commands only when known and safe.

## Escalation

Ask before prod migrations, infra apply, CI/CD changes, or destructive operations.
