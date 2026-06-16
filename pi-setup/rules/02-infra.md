# Rule: Infrastructure & Observability

alwaysApply: false

Apply when editing: `infra/`, `infrastructure/`, `pulumi/`, `deploy/`, `.github/workflows/`, `docker/`, `k8s/`, `helm/`, `monitoring/`, `observability/` or files: `.tf`, `.yml`, `.yaml` (CI contexts), `Dockerfile`, `docker-compose.*`

## Infrastructure as Code
- Follow project IaC patterns. Variables for environment-specific values.
- Never hardcode secrets. Use secrets management.
- Document manual steps if any.

## Environment Parity
- Staging mirrors production. Document differences.
- Use feature flags for gradual rollouts.

## Observability
- Every service needs health checks.
- Metrics for critical business operations.
- Log correlation IDs across service boundaries.
- Alerts for critical paths.

## Security
- Least privilege principle.
- Scan containers for vulnerabilities.
- Encryption at rest and in transit.

## Rollback
- Every deployment must be reversible.
- Document rollback procedures. Test in staging.
