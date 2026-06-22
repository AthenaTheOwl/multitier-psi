# dec-psi-001 protocol choice

status: accepted for v0.1 reference

## decision

v0.1 keeps two modes.

baseline computes a plaintext set intersection. it is the test oracle.

dh_based uses a commutative blinding reference flow and records a padded mock
secure-channel transcript. the transcript reveals the intersection size under
the v0.1 leakage model.

## reason

the repo needs a small protocol path that can be read, tested, and replaced.
the supplier-graph work is separate from the crypto library choice, so v0.1
keeps the crypto surface narrow.

## security boundary

this is not audited production crypto. the dh_based mode is a reference
implementation for fixtures and tests.

baseline is outside the leakage boundary because it sends plaintext sets.

before live use, replace this mode with an audited two-party psi library and
run the same graph preparation and fixture parity tests against that library.

## replacement path

an oprf-based or he-based implementation can replace `run_dh_based` if it
keeps the same session record fields and returns only the intersection size to
the caller by default.
