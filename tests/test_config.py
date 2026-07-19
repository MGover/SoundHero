import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import parse_env_mapping


class ConfigTests(unittest.TestCase):
    def test_parse_env_mapping_parses_json(self):
        self.assertEqual(
            parse_env_mapping("FFMPEG_OPTS", {"options": "-vn"}),
            {"options": "-vn"},
        )

    def test_parse_env_mapping_falls_back_to_default(self):
        self.assertEqual(parse_env_mapping("DOES_NOT_EXIST", {"a": 1}), {"a": 1})


if __name__ == "__main__":
    unittest.main()
