# status

## Current state

v0.1 is runnable as a local reference package. `python -m mtpsi validate`
checks both fixture graphs, runs baseline and dh_based modes, compares their
intersection size, and parses the committed example session.

the committed fixtures produce intersection size 1.

## Known limits

dh_based is a reference mode with a mock secure-channel transcript. it is not
audited crypto.

baseline sends plaintext sets and exists only as a deterministic test oracle.

tier traversal treats a canonical supplier as single-source when a component
has exactly one canonical supplier at that tier in the graph.

## Next feature queue

add a transport harness after the protocol transcript is stable.

swap the reference dh_based mode for an audited psi library before any live
deployment.

extend fixtures to cover substitute suppliers and missing canonical ids.
