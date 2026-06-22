# security disclosure

mtpsi v0.1 is a reference implementation.

the dh_based transcript reveals the intersection size under the committed
padded transcript model. the transcript stores opaque payload hashes and a
fixed minimum slot count for the fixture run.

baseline sends plaintext sets. it is a test oracle and is outside the leakage
boundary.

do not use this repo as audited production crypto. for live use, keep the
supplier graph preparation code separate and plug in an audited two-party psi
library.
