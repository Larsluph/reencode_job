from unittest import TestCase

from worker import format_bytes

class WorkerTest(TestCase):
    def test_format_bytes(self):
        self.assertEqual(format_bytes(100), "100 B")
        self.assertEqual(format_bytes(1_024), "1.00 KiB")
        self.assertEqual(format_bytes(1_048_576), "1.00 MiB")
        self.assertEqual(format_bytes(1_073_741_824), "1.00 GiB")
        self.assertEqual(format_bytes(1_099_511_627_776), "1.00 TiB")
        self.assertEqual(format_bytes(1_125_899_906_842_624), "1.00 PiB")

    def test_calc_ratio(self):
        pass
