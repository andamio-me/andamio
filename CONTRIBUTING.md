# Contributing to andamio

Thanks for helping. andamio secures servers and runs other people's apps, so changes are
held to a high bar: a bug here can expose someone's server.

*Español: toda contribución entra por fork y pull request. Los cambios de infraestructura o
seguridad se discuten primero en un issue. Reporta vulnerabilidades en privado (ver
[SECURITY.md](SECURITY.md)), nunca en un issue o PR público.*

## Before you start

- **Found a vulnerability?** Do not open an issue or PR. Follow [SECURITY.md](SECURITY.md).
- **Big change, new stack, or anything touching security?** Open an issue first and agree on
  the approach. A design that lands as a surprise PR is likely to be declined.
- **Small fix** (a typo, a clear bug, docs): a direct PR is fine.

## How changes land

`main` is protected: nobody pushes to it directly. Every change goes through a pull request
that needs a review and passing CI before it can merge.

1. Fork the repository and create a branch from `main`.
2. Make your change. Keep it focused — one concern per PR.
3. Run the checks locally (below). The same checks run in CI and must pass.
4. Open the PR against `andamio-me/andamio`, fill in the template, and link the issue if there
   is one.

## Running the checks

CI runs four jobs; reproduce them before pushing:

```bash
tools/tests.sh          # pytest (the CLIs, the extractor, the roles)
shellcheck scripts/*.sh # shell scripts
tools/ui-build.sh       # the panel (types and generated ui/ up to date)
```

Dockerfile builds also run in CI. If your change touches a generated Dockerfile, build it and
confirm the container starts.

## Conventions

- Architecture decisions are recorded as ADRs in `docs/decisions/`. A change that alters how
  the platform works usually needs one. See `docs/conventions.md`.
- Match the surrounding style. Comments and docs are bilingual (English first, Spanish where
  the existing file is).
- Never commit secrets, real IPs, hostnames, or keys. CI scans for them and will fail.

## License

By contributing, you agree your work is licensed under the project's [MIT License](LICENSE).
