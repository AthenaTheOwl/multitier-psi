# protocol walkthrough

## fixture flow

1. load `data/oem_a_graph.json` and `data/oem_b_graph.json`.
2. load `data/canonical_supplier_dict.json`.
3. map each supplier node display name or party-local id to a canonical id.
4. walk each component to tier-2 and tier-3 supplier nodes.
5. add a supplier to the party set when it is the only canonical supplier at
   that tier for the component.
6. run baseline and dh_based over those two sets.

## baseline

baseline sorts both prepared sets, records a plaintext exchange transcript,
and returns the size of the set intersection.

with seed `fixture-v0`, the session record is byte-stable.

## dh_based

dh_based hashes each canonical id to a group value, applies one secret scalar
per party, applies the peer scalar through the reference flow, and intersects
the resulting blinded tokens.

the transcript records opaque payload hashes, a fixed padding policy, and the
intersection size. it does not record canonical supplier ids.

this mode is a reference. replace it with an audited psi library before live
use.
