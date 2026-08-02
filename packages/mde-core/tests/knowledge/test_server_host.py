import argparse

import pytest

from mde.knowledge.cli import _private_host


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("127.0.0.1", "127.0.0.1"),
        ("192.168.0.10", "192.168.0.10"),
        ("100.75.235.67", "100.75.235.67"),
        ("0.0.0.0", "0.0.0.0"),
        ("::1", "::1"),
    ],
)
def test_private_host_accepts_local_network_addresses(value: str, expected: str) -> None:
    assert _private_host(value) == expected


@pytest.mark.parametrize("value", ["8.8.8.8", "example.com", "224.0.0.1"])
def test_private_host_rejects_broad_or_public_addresses(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        _private_host(value)
