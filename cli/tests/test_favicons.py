"""The filename algorithm is the one fact everything else depends on."""

from __future__ import annotations

from refaver.favicons import filename_for_uuid


def test_filename_is_uppercase_md5_of_uuid() -> None:
    # Precomputed: md5("11111111-1111-4111-8111-111111111111").hexdigest().upper()
    import hashlib

    uuid = "11111111-1111-4111-8111-111111111111"
    expected = hashlib.md5(uuid.encode()).hexdigest().upper()
    assert filename_for_uuid(uuid) == expected
    assert filename_for_uuid(uuid).isupper()
    assert len(filename_for_uuid(uuid)) == 32
