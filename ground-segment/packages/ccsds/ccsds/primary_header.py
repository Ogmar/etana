"""CCSDS Space Packet primary header (CCSDS 133.0-B).

The primary header is a fixed 6-byte block prepended to every packet, structured
as three big-endian 16-bit words:

    word 0  packet identification   version(3) type(1) sec_hdr(1) apid(11)
    word 1  packet sequence control seq_flags(2) seq_count(14)
    word 2  packet data length      (data byte count - 1)(16)

Fields do not align to byte boundaries, so pack/unpack operate on the 16-bit
words with bit shifts and masks rather than on individual bytes.
"""

from __future__ import annotations

from dataclasses import dataclass

HEADER_LENGTH = 6

# Field widths in bits.
_VERSION_BITS = 3
_TYPE_BITS = 1
_SEC_HDR_BITS = 1
_APID_BITS = 11
_SEQ_FLAGS_BITS = 2
_SEQ_COUNT_BITS = 14

# Maximum values, used for range validation.
_APID_MAX = (1 << _APID_BITS) - 1          # 2047
_SEQ_COUNT_MAX = (1 << _SEQ_COUNT_BITS) - 1  # 16383
_LENGTH_FIELD_MAX = (1 << 16) - 1            # 65535


@dataclass
class PrimaryHeader:
    """The seven fields of a CCSDS primary header.

    data_length is the number of data bytes that follow the header (the caller's
    natural value); the on-wire (length - 1) encoding is handled in pack/unpack.
    """

    apid: int
    sequence_count: int
    data_length: int
    version: int = 0
    packet_type: int = 0      # 0 = telemetry, 1 = telecommand
    sec_hdr_flag: int = 0     # 0 = no secondary header
    sequence_flags: int = 0b11  # unsegmented

    def pack(self) -> bytes:
        """Encode the header as 6 bytes."""
        self._validate()

        word0 = (
            (self.version << (_TYPE_BITS + _SEC_HDR_BITS + _APID_BITS))
            | (self.packet_type << (_SEC_HDR_BITS + _APID_BITS))
            | (self.sec_hdr_flag << _APID_BITS)
            | self.apid
        )
        word1 = (self.sequence_flags << _SEQ_COUNT_BITS) | self.sequence_count
        word2 = self.data_length - 1  # on-wire length is (count - 1)

        return bytes(
            [
                (word0 >> 8) & 0xFF, word0 & 0xFF,
                (word1 >> 8) & 0xFF, word1 & 0xFF,
                (word2 >> 8) & 0xFF, word2 & 0xFF,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes) -> "PrimaryHeader":
        """Decode 6 bytes into a header. Reads only the first 6 bytes."""
        if len(data) < HEADER_LENGTH:
            raise ValueError(
                f"primary header needs {HEADER_LENGTH} bytes, got {len(data)}"
            )

        word0 = (data[0] << 8) | data[1]
        word1 = (data[2] << 8) | data[3]
        word2 = (data[4] << 8) | data[5]

        return cls(
            version=(word0 >> (_TYPE_BITS + _SEC_HDR_BITS + _APID_BITS)) & 0b111,
            packet_type=(word0 >> (_SEC_HDR_BITS + _APID_BITS)) & 0b1,
            sec_hdr_flag=(word0 >> _APID_BITS) & 0b1,
            apid=word0 & _APID_MAX,
            sequence_flags=(word1 >> _SEQ_COUNT_BITS) & 0b11,
            sequence_count=word1 & _SEQ_COUNT_MAX,
            data_length=word2 + 1,  # undo the (count - 1) encoding
        )

    def _validate(self) -> None:
        if not 0 <= self.apid <= _APID_MAX:
            raise ValueError(f"apid {self.apid} out of range 0..{_APID_MAX}")
        if not 0 <= self.sequence_count <= _SEQ_COUNT_MAX:
            raise ValueError(
                f"sequence_count {self.sequence_count} out of range 0..{_SEQ_COUNT_MAX}"
            )
        if not 1 <= self.data_length <= _LENGTH_FIELD_MAX + 1:
            raise ValueError(
                f"data_length {self.data_length} out of range 1..{_LENGTH_FIELD_MAX + 1}"
            )
