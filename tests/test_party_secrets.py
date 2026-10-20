from __future__ import annotations

import random
import secrets
from pathlib import Path

import pytest

import mtpsi.protocol as protocol
from mtpsi.protocol import run_dh_based


ROOT = Path(__file__).resolve().parents[1]
A_IDS = {"sup.a", "sup.shared", "sup.c"}
B_IDS = {"sup.shared", "sup.d"}


def test_real_mode_draws_each_party_secret_from_the_os_csprng(monkeypatch: pytest.MonkeyPatch) -> None:
    # Real mode must not fall back to a seeded Mersenne Twister for either party.
    class NoSeededRandom(random.Random):
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("real mode built a random.Random")

    calls: list[int] = []
    real_randbelow = secrets.randbelow

    def spy(bound: int) -> int:
        calls.append(bound)
        return real_randbelow(bound)

    monkeypatch.setattr(protocol.random, "Random", NoSeededRandom)
    monkeypatch.setattr(protocol.secrets, "randbelow", spy)
    result = run_dh_based(A_IDS, B_IDS)
    assert result.intersection_canonical_ids == ("sup.shared",)
    assert len(calls) == 2  # one independent OS draw per party


def test_fixture_mode_gives_each_party_its_own_stream() -> None:
    seed = "fixture-v0"
    a_secret = protocol._party_secret(seed, "a")
    b_secret = protocol._party_secret(seed, "b")
    assert a_secret != b_secret
    # Each role's secret is a function of (seed, role) alone: drawing A's secret
    # any number of times does not move B's, unlike one shared random.Random(seed).
    for _ in range(3):
        protocol._party_secret(seed, "a")
    assert protocol._party_secret(seed, "b") == b_secret
    assert protocol._party_secret("other-seed", "a") != a_secret


def test_fixture_mode_is_deterministic_and_correct() -> None:
    first = run_dh_based(A_IDS, B_IDS, seed="fixture-v0")
    second = run_dh_based(A_IDS, B_IDS, seed="fixture-v0")
    assert first.transcript == second.transcript
    assert first.intersection_canonical_ids == ("sup.shared",)


def test_root_package_copy_matches_src() -> None:
    # `python -m mtpsi` from the repo root imports mtpsi/, not src/mtpsi/, so the
    # two copies must not drift (the root copy sits one directory shallower).
    for name in ("protocol.py", "party.py", "cli.py", "__main__.py"):
        src = (ROOT / "src" / "mtpsi" / name).read_text(encoding="utf-8")
        root = (ROOT / "mtpsi" / name).read_text(encoding="utf-8")
        assert root == src.replace("parents[2]", "parents[1]"), name
