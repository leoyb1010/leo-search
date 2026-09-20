import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from eval_answers import evaluate


class AnswerEvalTest(unittest.TestCase):
    def test_wrong_value_citation_or_missing_answer_fails(self):
        cases = [{'id':'one','expected':{'value':False,'evidence_ids':['s1']}}]
        for answers in [[],[{'id':'one','value':0,'evidence_ids':['s1']}],
                        [{'id':'one','value':False,'evidence_ids':['s2']}]]:
            self.assertEqual(evaluate(cases, answers)['passed'], 0)
        self.assertEqual(evaluate(cases, [{'id':'one','value':False,'evidence_ids':['s1']}])['passed'], 1)

    def test_duplicate_answers_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([{'id':'one','expected':{'value':1,'evidence_ids':[]}}], [{'id':'one'}]*2)
