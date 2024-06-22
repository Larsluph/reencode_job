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
        self.assertEqual(format_bytes(512), "512 B")

    def test_kilobytes(self):
        self.assertEqual(format_bytes(1024), "1.00 KiB")

    def test_kilobytes_and_half(self):
        self.assertEqual(format_bytes(1536), "1.50 KiB")

    def test_megabytes(self):
        self.assertEqual(format_bytes(1048576), "1.00 MiB")

    def test_gigabytes(self):
        self.assertEqual(format_bytes(1073741824), "1.00 GiB")

    def test_large_values(self):
        self.assertEqual(format_bytes(1208925819614629174706176), "1.00 YiB")

    def test_zero_value(self):
        self.assertEqual(format_bytes(0), "0.00 B")

    def test_negative_values(self):
        self.assertEqual(format_bytes(-1024), "-1.00 KiB")
