# security disclosure

mtpsi v0.1 is a reference implementation.

the dh_based transcript reveals the intersection size under the committed
padded transcript model. the transcript stores opaque payload hashes and a
fixed minimum slot count for the fixture run.

baseline sends plaintext sets. it is a test oracle and is outside the leakage
boundary.

## known limit: dictionary attacks

psi tells each party which of its own ids the other side also holds. it
cannot stop a party from choosing what to ask. the canonical supplier
dictionary is public and has five entries, exactly the union of the two
fixture sets, so a party that submits the whole dictionary as its "set" gets
the other party's whole single-source list back. the transcript still carries
no ids. that is a dictionary attack, and no psi protocol prevents it on its
own: the defence is to bound what a party may ask.

`assert_leakage_boundary` now fails a run in which either party submitted more
than 80% of the dictionary (`MAX_QUERY_FRACTION`), and in every case it requires
at least one entry left out. against the five-entry fixture dictionary that is
four ids, which the honest oem_a set (four ids) meets. the bound is on set size
because a party sees the size of the other side's blinded set, not its
contents. `mtpsi run --mode dh_based` refuses to print a session that fails it,
and `eval/leakage_bound.py` checks that the full sweep is rejected.

what the bound does not do:

- with a five-entry dictionary, an honest four-id query still learns the other
  side's membership for four of the five suppliers. the privacy a small
  dictionary leaves is small.
- a party can split the sweep across sessions. stopping that needs
  per-counterparty query accounting across sessions, which v0.1 does not keep.
- a party can pad its query with real-looking ids that are not in the
  dictionary to hide its size; the bound counts them as queries, so padding
  only makes it hit the bound sooner.

live use needs a dictionary much larger than any one party's set, session
accounting, and an audited protocol (see dec-psi-001).

dh_based blinds in the prime-order-q subgroup of the rfc 3526 2048-bit safe
prime group. an earlier version used `Z_p*` with p = 2^255 - 19, whose p - 1 has
small factors (4, 3, 65147), so every blinded value leaked the
quadratic-residue bit of its hashed id. see dec-psi-001.

do not use this repo as audited production crypto. for live use, keep the
supplier graph preparation code separate and plug in an audited two-party psi
library.
