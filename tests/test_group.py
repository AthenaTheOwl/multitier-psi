from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

import mtpsi.protocol as protocol
from mtpsi.protocol import GROUP_P, GROUP_Q, hash_to_group, in_prime_order_subgroup


ROOT = Path(__file__).resolve().parents[1]
DICTIONARY_IDS = [
    entry["canonical_id"]
    for entry in json.loads((ROOT / "data" / "canonical_supplier_dict.json").read_text(encoding="utf-8"))["entries"]
]


def _probably_prime(n: int, rounds: int = 32) -> bool:
    if n < 4:
        return n in (2, 3)
    d, s = n - 1, 0
    while d % 2 == 0:
        d, s = d // 2, s + 1
    rng = random.Random(0)
    for _ in range(rounds):
        x = pow(rng.randrange(2, n - 2), d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _legendre(value: int) -> int:
    return 1 if pow(value, (GROUP_P - 1) // 2, GROUP_P) == 1 else -1


SMALL_NON_RESIDUE = next(n for n in range(2, 100) if _legendre(n) == -1)


def test_group_is_a_2048_bit_safe_prime() -> None:
    # p - 1 = 2q with q prime: the only small subgroup is {1, p - 1}.
    assert GROUP_P.bit_length() == 2048
    assert GROUP_P == 2 * GROUP_Q + 1
    assert _probably_prime(GROUP_P)
    assert _probably_prime(GROUP_Q)


def test_hashed_and_blinded_values_carry_no_residue_bit() -> None:
    # In Z_p* with p = 2^255 - 19 the Legendre symbol of H(id)^a equals that of
    # H(id) whenever a is odd, so a blinded value told the receiver which
    # dictionary ids it could be. In the order-q subgroup every element is a
    # residue, whatever the id and whatever the secret's parity.
    secrets_to_try = [2, 3, protocol._party_secret("fixture-v0", "a")]  # even, odd, fixture
    for identifier in DICTIONARY_IDS:
        element = hash_to_group(identifier)
        assert pow(element, GROUP_Q, GROUP_P) == 1  # order divides q
        assert _legendre(element) == 1
        for secret in secrets_to_try:
            blinded = protocol._blind(identifier, secret)
            assert in_prime_order_subgroup(blinded)
            assert _legendre(blinded) == 1


def test_secrets_are_drawn_from_the_subgroup_order() -> None:
    for role in ("a", "b"):
        assert 1 <= protocol._party_secret("fixture-v0", role) < GROUP_Q
        assert 1 <= protocol._party_secret(None, role) < GROUP_Q


@pytest.mark.parametrize("value", [0, 1, GROUP_P - 1, GROUP_P, SMALL_NON_RESIDUE])
def test_reblinding_refuses_elements_outside_the_subgroup(value: int) -> None:
    # p - 1 has order 2 and a non-residue has even order: either would let a
    # peer read the parity of the secret back out of the reply.
    with pytest.raises(ValueError, match="prime-order subgroup"):
        protocol._blind_value(value, 12345)


def test_jacobi_matches_euler_criterion() -> None:
    rng = random.Random(7)
    for _ in range(20):
        value = rng.randrange(2, GROUP_P - 1)
        assert protocol._jacobi(value, GROUP_P) == _legendre(value)
