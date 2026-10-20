# security disclosure

mtpsi v0.1 is a reference implementation.

the dh_based transcript reveals the intersection size under the committed
padded transcript model. the transcript stores opaque payload hashes and a
fixed minimum slot count for the fixture run.

baseline sends plaintext sets. it is a test oracle and is outside the leakage
boundary.

dh_based blinds in the prime-order-q subgroup of the rfc 3526 2048-bit safe
prime group. an earlier version used `Z_p*` with p = 2^255 - 19, whose p - 1 has
small factors (4, 3, 65147), so every blinded value leaked the
quadratic-residue bit of its hashed id. see dec-psi-001.

do not use this repo as audited production crypto. for live use, keep the
supplier graph preparation code separate and plug in an audited two-party psi
library.
