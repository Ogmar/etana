"""Tests for the CCSDS primary header codec."""

import pytest

from ccsds.primary_header import PrimaryHeader, HEADER_LENGTH


def test_pack_known_bytes():
    """A hand-computed header packs to exactly the expected 6 bytes.

    APID 100, seq_count 5, data_length 16, all flags default
    (version 0, type 0, sec_hdr 0, seq_flags 0b11).

    word0 = version/type/sec_hdr all 0, apid 100 = 0x0064
    word1 = seq_flags 0b11 << 14 | count 5 = 0xC005
    word2 = data_length - 1 = 15 = 0x000F
    """
    h = PrimaryHeader(apid=100, sequence_count=5, data_length=16)
    assert h.pack() == bytes([0x00, 0x64, 0xC0, 0x05, 0x00, 0x0F])


def test_pack_length_is_encoded_minus_one():
    """data_length 16 encodes as 15 in the length field."""
    h = PrimaryHeader(apid=1, sequence_count=0, data_length=16)
    packed = h.pack()
    length_field = (packed[4] << 8) | packed[5]
    assert length_field == 15


def test_roundtrip_all_containers():
    """Pack then unpack reproduces the original fields for every APID."""
    for apid in (100, 200, 300, 400):
        for count in (0, 1, 8191, 16383):
            original = PrimaryHeader(
                apid=apid, sequence_count=count, data_length=22
            )
            recovered = PrimaryHeader.unpack(original.pack())
            assert recovered == original


def test_apid_boundary_bits():
    """The 11-bit APID round-trips at its maximum, confirming no bit bleed
    into the adjacent sec_hdr flag."""
    h = PrimaryHeader(apid=2047, sequence_count=0, data_length=1)
    recovered = PrimaryHeader.unpack(h.pack())
    assert recovered.apid == 2047
    assert recovered.sec_hdr_flag == 0


def test_sequence_count_boundary_bits():
    """The 14-bit count round-trips at its maximum, confirming no bit bleed
    into the adjacent sequence flags."""
    h = PrimaryHeader(apid=0, sequence_count=16383, data_length=1)
    recovered = PrimaryHeader.unpack(h.pack())
    assert recovered.sequence_count == 16383
    assert recovered.sequence_flags == 0b11


def test_unpack_ignores_trailing_bytes():
    """Unpack reads only the first 6 bytes; a full packet's data is ignored."""
    h = PrimaryHeader(apid=100, sequence_count=1, data_length=4)
    packet = h.pack() + bytes([0xDE, 0xAD, 0xBE, 0xEF])
    assert PrimaryHeader.unpack(packet).apid == 100


def test_unpack_rejects_short_input():
    with pytest.raises(ValueError):
        PrimaryHeader.unpack(bytes([0x00, 0x64, 0xC0]))


@pytest.mark.parametrize(
    "field,value",
    [("apid", 2048), ("sequence_count", 16384), ("data_length", 0)],
)
def test_pack_rejects_out_of_range(field, value):
    kwargs = {"apid": 1, "sequence_count": 0, "data_length": 1, field: value}
    with pytest.raises(ValueError):
        PrimaryHeader(**kwargs).pack()


def test_header_length_constant():
    assert HEADER_LENGTH == 6
    assert len(PrimaryHeader(apid=1, sequence_count=0, data_length=1).pack()) == 6
