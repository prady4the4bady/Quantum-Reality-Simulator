# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x (Phase 1 foundation) | Yes, within the limits documented below |

Phase 1 is a local scientific prototype, not a hardened production service.

## Reporting a vulnerability

Do not open a public issue containing credentials, personal data, or exploit
details. Use GitHub's private vulnerability reporting or a private security
advisory for `prady4the4bady/Quantum-Reality-Simulator`. Include:

- affected version or commit;
- a minimal reproduction;
- impact assessment;
- any suggested remediation.

No response-time guarantee is made for this phase.

## Security model

Phase 1 is designed to be local-first and offline at runtime:

- No paid APIs, cloud inference, or mandatory network services.
- No telemetry.
- No downloaded model weights.
- No CUDA or GPU quantum backend requirement.
- No credential handling inside the project.
- No `.env` files, tokens, private keys, or certificates are committed.
- No administrator privileges are required to build or test.

## Operational restrictions

1. Never commit credentials, API tokens, `.env` files, private keys, or
   personal data.
2. Never run `gh auth token`, print authentication tokens, or store GitHub
   credentials in the repository.
3. Treat external scientific data and third-party scripts as untrusted until
   provenance and content are reviewed.
4. Do not add a dependency without checking Python 3.12/Windows compatibility,
   maintenance status, and necessity.
5. Do not introduce mandatory cloud dependencies or paid services.
6. Do not weaken validation, suppress warnings, or skip failing tests to obtain
   a green build.
7. Do not execute untrusted code with elevated privileges.

## Dependency and supply-chain controls

- Runtime dependencies are exactly pinned in `pyproject.toml`: NumPy 2.5.4,
  SciPy 1.18.1, and PennyLane 0.45.1.
- Development tools are exactly pinned: pytest 9.2.0 and Ruff 0.17.4.
- PennyLane installs `pennylane-lightning` transitively; Phase 1 does not select
  a GPU backend.
- New dependencies require an explicit justification and a recorded decision.
- Reproducible environment creation is documented in `README.md`.

## Known limitations

- Phase 1 has no authentication, authorisation, multi-user isolation, network
  service, or data-at-rest encryption because it exposes none of those surfaces.
- The Bell-state simulation is an ideal statevector simulation. It does not model
  hardware noise, decoherence, or measurement sampling.
- The harmonic oscillator is an ideal linear, undamped, unforced model. It is not
  a validated model of a real physical structure.

## Change control

Changes are made on a dedicated Git branch and committed locally only after
tests and lint pass. Pushing, merging, deleting data, and force operations
require separate explicit approval.
