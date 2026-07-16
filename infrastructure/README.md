# Infrastructure

Empty by design. The MVP runs locally with no containers (see `../docs/TechnicalDecisions.md`) — Python via a venv, Node via npm.

This directory is reserved for when a real deploy target needs it: Dockerfiles for `apps/api` and `apps/web`, a `docker-compose.yml` for staging, or IaC for a cloud target. Add it when there's an actual environment to deploy to, not speculatively.
