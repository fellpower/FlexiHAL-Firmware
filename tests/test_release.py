"""Exercise corrupt-image rejection before shipping flashable artifacts."""
import struct
import unittest
from unittest.mock import patch

import uf2conv
from scripts.release import BASE, END, FAMILY, validate_uf2


class UF2ValidationTests(unittest.TestCase):
    def setUp(self):
        self.binary = bytes(range(256)) + b"last partial page"
        with patch.object(uf2conv, "appstartaddr", BASE), patch.object(uf2conv, "familyid", FAMILY):
            self.uf2 = uf2conv.convert_to_uf2(self.binary)

    def test_converter_round_trip_and_partial_page(self):
        validate_uf2(self.uf2, self.binary)

    def test_rejects_corrupted_fields_and_payload(self):
        for offset in (0, 4, 8, 12, 16, 20, 24, 28, 32, 508, 512 + 32 + 30):
            with self.subTest(offset=offset):
                corrupt = bytearray(self.uf2)
                corrupt[offset] ^= 1
                with self.assertRaises(ValueError):
                    validate_uf2(corrupt, self.binary)

    def test_rejects_truncation_and_extra_blocks(self):
        for corrupt in (self.uf2[:-1], self.uf2 + self.uf2[:512]):
            with self.assertRaises(ValueError):
                validate_uf2(corrupt, self.binary)

    def test_rejects_bootloader_address(self):
        corrupt = bytearray(self.uf2)
        struct.pack_into("<I", corrupt, 12, 0x08000000)
        with self.assertRaises(ValueError):
            validate_uf2(corrupt, self.binary)

    def test_rejects_empty_or_oversized_firmware(self):
        for binary in (b"", bytes(END - BASE + 1)):
            with self.assertRaises(ValueError):
                validate_uf2(self.uf2, binary)


if __name__ == "__main__":
    unittest.main()
