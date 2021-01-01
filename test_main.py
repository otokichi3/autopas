import unittest
from main import Opas

expected = """
[港 第1]
12:00 ～ 15:00
 02-03(水)
 02-08(月)
 02-09(火)
 02-25(木)

[港 第2]
12:00 ～ 15:00
 02-03(水)
 02-08(月)
 02-09(火)
 02-25(木)

[大正 第1]
12:00 ～ 15:00
 02-22(月)

[大正 第2]
12:00 ～ 15:00
 02-22(月)

[東淀川 第1]
12:00 ～ 15:00
 02-01(月)

[住之江 第1]
12:00 ～ 15:00
 02-10(水)

[住吉 第1]
12:00 ～ 15:00
 02-02(火)
 02-09(火)
"""
    
class TestCreateMessageFromList(unittest.TestCase):
    def test_create_message_from_list(self):
        opas = Opas()
        with open('./output.html') as f:
            html = f.read()
        opas.set_date()
        opas.get_vacant_list(html)
        res = opas.create_message_from_list()
        self.assertEqual(expected, res)

if __name__ == "__main__":
    unittest.main()