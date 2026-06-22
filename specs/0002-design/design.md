# spec 0002 design

## graph preparation

the party layer loads json graphs, validates required fields, and fills supplier
canonical ids from the committed dictionary.

the traverser starts at component nodes. for each component, it collects
canonical tier-2 and tier-3 supplier ids. if a tier has exactly one canonical
supplier for that component, that supplier id enters the party psi set.

## protocol modes

baseline exchanges sorted plaintext sets and returns the intersection size.
it is deterministic when a seed is passed.

dh_based uses a commutative blinding reference flow and pads transcript slots
to a fixed minimum for fixture runs. the transcript records payload hashes and
the final intersection size.

## gates

the local gates are pytest, voice lint, schema validation, determinism, and
leakage bound.
