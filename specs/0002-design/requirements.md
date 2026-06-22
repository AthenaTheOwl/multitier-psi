# spec 0002 design requirements

## requirements

- `python -m mtpsi validate` must run with no arguments.
- baseline and dh_based must return the same intersection size on committed
  fixtures.
- baseline output must be deterministic when a seed is supplied.
- dh_based transcript checks must assert that the result message reveals only
  intersection size.
- status docs must keep the three required section headings in `STATUS.md`.
- development dependencies must live under `[dependency-groups]`.
