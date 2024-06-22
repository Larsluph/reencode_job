from unittest import TestCase

from worker import format_bytes, format_float


class TestFormatFloat(TestCase):
    """Test case for the format_float function"""

    def test_format_small_float(self):
        self.assertEqual(format_float(23.456), "23.5")

    def test_format_large_float(self):
        self.assertEqual(format_float(123.456), "123")

    def test_format_negative_float(self):
        self.assertEqual(format_float(-23.456), "-23.5")

    def test_format_zero(self):
        self.assertEqual(format_float(0), "0.00")

    def test_format_very_small_float(self):
        self.assertEqual(format_float(0.004), "0.00")


class TestFormatBytes(TestCase):
    """Test case for the format_bytes function"""

    def test_small_values(self):
        self.assertEqual(format_bytes(512), f"{format_float(512)} B")

    def test_kilobytes(self):
        self.assertEqual(format_bytes(1024), f"{format_float(1)} KiB")

    def test_kilobytes_and_half(self):
        self.assertEqual(format_bytes(1536), f"{format_float(1.5)} KiB")

    def test_megabytes(self):
        self.assertEqual(format_bytes(1_048_576), f"{format_float(1)} MiB")

    def test_gigabytes(self):
        self.assertEqual(format_bytes(1_073_741_824), f"{format_float(1)} GiB")

    def test_large_values(self):
        self.assertEqual(format_bytes(1_208_925_819_614_629_174_706_176), f"{format_float(1)} YiB")

    def test_zero_value(self):
        self.assertEqual(format_bytes(0), f"{format_float(0)} B")

    def test_negative_values(self):
        self.assertEqual(format_bytes(-1024), f"{format_float(-1)} KiB")
