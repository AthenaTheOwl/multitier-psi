# product brief

mtpsi is a reference two-party private set intersection runtime for supplier
graph fixtures.

the v0.1 user is an engineer or security reviewer who wants to see how two
parties can prepare canonical supplier ids, run a fixture intersection, and
inspect the session record without sharing raw supplier lists in the
dh_based transcript.

the repo ships a narrow fixture path:

- load two public supplier graphs.
- map party-local supplier names to canonical supplier ids.
- traverse tier-2 and tier-3 supplier dependencies.
- build the per-party single-source supplier set.
- run baseline and dh_based modes.
- validate that both modes return the same intersection size.

the baseline mode exists for tests. it sends plaintext sets and is not inside
the leakage boundary.

the dh_based mode is a reference mode with a padded mock secure-channel
transcript. it is not audited crypto. use an audited psi library for a live
deployment.
