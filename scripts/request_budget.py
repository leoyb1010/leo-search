"""Per-run request budget and single-flight reuse. Nothing persists across tasks."""
from concurrent.futures import Future
from threading import Lock


class RequestBudget:
    def __init__(self, limit=8):
        if limit < 1:
            raise ValueError("request limit must be positive")
        self.limit, self.calls, self.cache_hits = limit, 0, 0
        self._pending, self._lock = {}, Lock()

    def run(self, key, operation):
        with self._lock:
            if key in self._pending:
                self.cache_hits += 1
                future, owner = self._pending[key], False
            else:
                if self.calls >= self.limit:
                    raise RuntimeError("request budget exhausted; report the remaining evidence gap")
                self.calls += 1
                future, owner = Future(), True
                self._pending[key] = future
        if owner:
            try:
                future.set_result(operation())
            except Exception as error:
                future.set_exception(error)
        return future.result()
