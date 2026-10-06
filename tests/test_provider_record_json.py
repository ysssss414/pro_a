import json
import math
import unittest
from pro_a.source_analysis_provider_record import parse_object

class StructuredTests(unittest.TestCase):
    def test_full_lossless_roundtrip(self):
        original = {'string': 'ＡＢＣ 中文 emoji 😀', 'boolean': True, 'false': False,
                    'integer': 2**100, 'float': 0.125, 'negative_zero': -0.0, 'null': None,
                    'array': [1, '2', False, None, {'nested': [3.5]}], 'object': {'arbitrary_key': {'deep': []}}}
        for ascii_mode in (True, False):
            result = parse_object(json.dumps(original, ensure_ascii=ascii_mode, allow_nan=False))
            self.assertEqual(result, original)
            self.assertIs(type(result['integer']), int)
            self.assertIs(type(result['float']), float)
            self.assertIs(type(result['boolean']), bool)
            self.assertIsNone(result['null'])
            self.assertEqual(math.copysign(1, result['negative_zero']), -1)
            self.assertEqual(json.dumps(result, ensure_ascii=ascii_mode, allow_nan=False), json.dumps(original, ensure_ascii=ascii_mode, allow_nan=False))

    def test_empty_object(self):
        self.assertEqual(parse_object('{}'), {})

    def test_valid_surrogate_pair(self):
        self.assertEqual(parse_object('{"s":"\\ud83d\\ude00"}'), {'s': '😀'})


INVALID = {
    'broken_json': '{', 'duplicate_root': '{"a":1,"a":2}',
    'duplicate_nested': '{"a":{"b":1,"b":2}}', 'duplicate_escaped_key': '{"a":1,"\\u0061":2}',
    'scalar_number': '1', 'scalar_string': '"s"', 'scalar_bool': 'true', 'scalar_null': 'null',
    'array_root': '[]', 'nan': '{"x":NaN}', 'positive_infinity': '{"x":Infinity}',
    'negative_infinity': '{"x":-Infinity}', 'overflow_exponent': '{"x":1e9999}',
    'nested_nan': '{"x":[{"y":NaN}]}', 'high_surrogate': '{"x":"\\ud800"}',
    'low_surrogate': '{"x":"\\udfff"}', 'surrogate_key': '{"\\ud800":1}',
    'raw_surrogate': '{"x":"\ud800"}', 'trailing_payload': '{}{}',
    'non_string_dict': {}, 'non_string_bytes': b'{}', 'bad_utf8_bytes': b'{"x":"\xff"}',
}
for name, value in INVALID.items():
    def test(self, value=value):
        with self.assertRaises(ValueError):
            parse_object(value)
    setattr(StructuredTests, 'test_reject_' + name, test)

del test
