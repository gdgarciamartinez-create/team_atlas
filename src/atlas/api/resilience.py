from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any, Optional
import time
import random

@dataclass
class RetryPolicy:
    tries: int = 4
    base_delay_s: float = 0.8
    max_delay_s: float = 6.0
    jitter: float = 0.25

def with_retry(fn: Callable[[], Any], policy: RetryPolicy, on_error: Optional[Callable[[Exception,int],None]] = None) -> Any:
    last_err = None
    for i in range(policy.tries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if on_error:
                on_error(e, i)
            delay = min(policy.max_delay_s, policy.base_delay_s * (2 ** i))
            delay = delay * (1 + random.uniform(-policy.jitter, policy.jitter))
            time.sleep(max(0.05, delay))
    raise last_err

def is_stale(last_ts: int, max_age_s: int) -> bool:
    return (int(time.time()) - int(last_ts)) > max_age_s