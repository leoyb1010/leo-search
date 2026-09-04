import importlib.util
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest

SPEC = importlib.util.spec_from_file_location("budget", Path(__file__).resolve().parents[1] / "scripts/request_budget.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RequestBudgetTest(unittest.TestCase):
    def test_concurrent_identical_requests_share_one_operation(self):
        budget = MODULE.RequestBudget(1)
        started, finish = threading.Event(), threading.Event()
        def work():
            started.set()
            self.assertTrue(finish.wait(2))
            return "one response"
        with ThreadPoolExecutor(2) as pool:
            first = pool.submit(budget.run, "same", work)
            self.assertTrue(started.wait(2))
            second = pool.submit(budget.run, "same", work)
            finish.set()
            self.assertEqual(first.result(), second.result())
        self.assertEqual((budget.calls, budget.cache_hits), (1, 1))

    def test_hard_budget_blocks_network_operation(self):
        budget = MODULE.RequestBudget(1)
        budget.run("first", lambda: "ok")
        with self.assertRaisesRegex(RuntimeError, "budget exhausted"):
            budget.run("second", lambda: self.fail("must not call"))

    def test_failed_request_is_not_retried_implicitly(self):
        budget = MODULE.RequestBudget(2)
        def fail():
            raise RuntimeError("auth required")
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError, "auth required"):
                budget.run("same", fail)
        self.assertEqual(budget.calls, 1)

    def test_new_run_does_not_reuse_previous_task_data(self):
        one, two = MODULE.RequestBudget(1), MODULE.RequestBudget(1)
        self.assertEqual(one.run("same", lambda: "old"), "old")
        self.assertEqual(two.run("same", lambda: "new"), "new")
