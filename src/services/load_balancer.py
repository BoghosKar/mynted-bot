"""Load Balancer for multiple Gemini API accounts.

Distributes requests across multiple Google API keys with
rate limiting awareness and automatic failover.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional
from collections import deque

from src.config import get_google_api_keys, settings


@dataclass
class AccountStatus:
    """Status of a single API account."""

    api_key: str
    active_requests: int = 0
    total_requests: int = 0
    failures: int = 0
    last_failure: float = 0
    rate_limited_until: float = 0
    consecutive_failures: int = 0


class LoadBalancer:
    """
    Manages multiple Gemini API accounts with intelligent load distribution.

    Features:
    - Round-robin distribution with awareness of active requests
    - Rate limit detection and automatic cooldown
    - Failover to healthy accounts
    - Request queuing when all accounts are busy
    """

    def __init__(self):
        self.accounts: list[AccountStatus] = []
        self._lock = asyncio.Lock()
        self._request_queue: deque = deque()
        self._max_concurrent_per_account = settings.max_concurrent_per_account

        # Initialize accounts from config
        for key in get_google_api_keys():
            self.accounts.append(AccountStatus(api_key=key))

    @property
    def total_capacity(self) -> int:
        """Total concurrent requests across all accounts."""
        return len(self.accounts) * self._max_concurrent_per_account

    @property
    def available_capacity(self) -> int:
        """Current available capacity."""
        now = time.time()
        available = 0
        for account in self.accounts:
            if account.rate_limited_until <= now:
                available += self._max_concurrent_per_account - account.active_requests
        return max(0, available)

    async def acquire_account(self, timeout: float = 60.0) -> Optional[AccountStatus]:
        """
        Acquire an account for making a request.

        Args:
            timeout: Maximum time to wait for an available account

        Returns:
            AccountStatus if acquired, None if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            async with self._lock:
                account = self._get_best_account()
                if account:
                    account.active_requests += 1
                    account.total_requests += 1
                    return account

            # No account available, wait a bit
            await asyncio.sleep(0.5)

        return None

    def _get_best_account(self) -> Optional[AccountStatus]:
        """Get the best available account (internal, must hold lock)."""
        now = time.time()
        best = None
        best_score = float("inf")

        for account in self.accounts:
            # Skip rate-limited accounts
            if account.rate_limited_until > now:
                continue

            # Skip accounts at max capacity
            if account.active_requests >= self._max_concurrent_per_account:
                continue

            # Score based on: active requests, failures, consecutive failures
            score = (
                account.active_requests * 10
                + account.failures * 2
                + account.consecutive_failures * 5
            )

            if score < best_score:
                best_score = score
                best = account

        return best

    async def release_account(
        self,
        account: AccountStatus,
        success: bool = True,
        rate_limited: bool = False,
    ) -> None:
        """
        Release an account after request completion.

        Args:
            account: The account to release
            success: Whether the request succeeded
            rate_limited: Whether hit rate limit
        """
        async with self._lock:
            account.active_requests = max(0, account.active_requests - 1)

            if success:
                account.consecutive_failures = 0
            else:
                account.failures += 1
                account.consecutive_failures += 1
                account.last_failure = time.time()

                if rate_limited:
                    # Cooldown for 45 seconds on rate limit
                    account.rate_limited_until = time.time() + 45

                # If too many consecutive failures, temporary cooldown
                if account.consecutive_failures >= 3:
                    account.rate_limited_until = time.time() + 30

    def get_stats(self) -> dict:
        """Get current load balancer statistics."""
        now = time.time()
        return {
            "accounts": len(self.accounts),
            "total_capacity": self.total_capacity,
            "available_capacity": self.available_capacity,
            "account_stats": [
                {
                    "index": i,
                    "active": acc.active_requests,
                    "total": acc.total_requests,
                    "failures": acc.failures,
                    "rate_limited": acc.rate_limited_until > now,
                    "cooldown_remaining": max(0, acc.rate_limited_until - now),
                }
                for i, acc in enumerate(self.accounts)
            ],
        }

    async def wait_for_capacity(self, required: int, timeout: float = 120.0) -> bool:
        """
        Wait until enough capacity is available.

        Args:
            required: Number of concurrent slots needed
            timeout: Maximum wait time

        Returns:
            True if capacity available, False if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.available_capacity >= required:
                return True
            await asyncio.sleep(1.0)

        return False

    def is_healthy(self) -> bool:
        """Check if at least one account is healthy."""
        now = time.time()
        return any(
            acc.rate_limited_until <= now and acc.consecutive_failures < 5
            for acc in self.accounts
        )


# Global load balancer instance
_load_balancer: Optional[LoadBalancer] = None


def get_load_balancer() -> LoadBalancer:
    """Get or create the global load balancer instance."""
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = LoadBalancer()
    return _load_balancer
