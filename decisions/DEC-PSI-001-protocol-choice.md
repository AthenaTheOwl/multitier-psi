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

## group (amended october 2026)

the first reference flow blinded in `Z_p*` with p = 2^255 - 19. that is the
curve25519 field prime, not a group chosen for this protocol: p - 1 is
divisible by 4, 3 and 65147, so a blinded value h^a kept the quadratic-residue
bit (and the order-3 and order-65147 characters) of the hashed id h. a peer
holding the public five-entry dictionary could use those bits to narrow which
ids a blinded value could be, and to learn bits of the secret, without
breaking anything.

the flow now works in the subgroup of prime order q inside the rfc 3526
2048-bit modp group, where p = 2q + 1 is a safe prime. ids are hashed into
that subgroup by squaring a wide hash. secrets are drawn uniformly from
[1, q - 1], and each party draws its own (`secrets` in real mode; separate
seeded streams only in fixture mode). a received element is rejected unless it
is a non-identity quadratic residue. this removes the residue-bit leak. it
does not make the mode audited; the replacement path above still applies.

## replacement path

an oprf-based or he-based implementation can replace `run_dh_based` if it
keeps the same session record fields and returns only the intersection size to
the caller by default.
