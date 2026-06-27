"""
Worker — concurrent job consumer daemon.

Dequeues jobs from PostgreSQL and dispatches to registered handlers.
Replaces the Huey consumer (``aiw worker``).

Architecture:
  - Main process: scheduler ticker (every 60s) + health endpoint
  - Worker pool: N async workers, each running dequeue → process → complete
  - Heartbeat extends consumer lock to prevent expiry during long jobs

Usage:
    worker = Worker(dsn="postgresql:///ai_workspace")
    await worker.start(concurrency=4)

    # Or via CLI:
    # aiw queue worker --concurrency 4
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from ai_workspace.queue import JobQueue, Job, get_handler

logger = logging.getLogger("aiw.worker")


class Worker:
    """Dequeues jobs from PostgreSQL and dispatches to registered handlers.

    Runs a scheduler ticker and a pool of concurrent job consumers.
    """

    def __init__(
        self,
        dsn: str = "postgresql:///ai_workspace",
        consumer_id: str | None = None,
    ):
        self.queue = JobQueue(dsn)
        self.consumer_id = consumer_id or f"worker-{uuid.uuid4().hex[:8]}"
        self._running = False
        self._active_jobs: dict[int, asyncio.Task] = {}
        self._scheduler_task: asyncio.Task | None = None
        self._worker_tasks: list[asyncio.Task] = []

    async def start(self, concurrency: int = 4) -> None:
        """Start the worker pool and scheduler ticker.

        Args:
            concurrency: Number of concurrent job processors
        """
        self._running = True
        await self.queue.connect()

        logger.info(
            "Worker %s starting with %d slots",
            self.consumer_id, concurrency,
        )

        # Scheduler ticker (every 60s)
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

        # Worker pool
        self._worker_tasks = [
            asyncio.create_task(self._worker_loop(i))
            for i in range(concurrency)
        ]

        # Wait for shutdown signal
        try:
            await asyncio.gather(self._scheduler_task, *self._worker_tasks)
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        """Graceful shutdown."""
        logger.info("Worker %s shutting down...", self.consumer_id)
        self._running = False

        # Cancel active jobs
        for job_id, task in list(self._active_jobs.items()):
            task.cancel()
            logger.info("Cancelled active job %d", job_id)

        # Cancel worker tasks
        for task in self._worker_tasks:
            task.cancel()
        if self._scheduler_task:
            self._scheduler_task.cancel()

        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        if self._scheduler_task:
            await asyncio.gather(self._scheduler_task, return_exceptions=True)

        await self.queue.close()
        logger.info("Worker %s stopped", self.consumer_id)

    async def _worker_loop(self, worker_id: int) -> None:
        """Single worker: dequeue → process → repeat."""
        cid = f"{self.consumer_id}-{worker_id}"
        heartbeat_interval = 30  # seconds

        while self._running:
            try:
                job = await self.queue.dequeue(
                    consumer_id=cid,
                    queues=["default", "loops", "workflows", "scheduled"],
                )

                if job is None:
                    await asyncio.sleep(1)
                    continue

                # Process in a task so heartbeat can run concurrently
                process_task = asyncio.create_task(
                    self._process_job(job, cid)
                )
                self._active_jobs[job.id] = process_task
                process_task.add_done_callback(
                    lambda _, jid=job.id: self._active_jobs.pop(jid, None)
                )

                # Run heartbeat concurrently with the job
                async def _heartbeat(jid: int, cid: str):
                    while self._running and jid in self._active_jobs:
                        await asyncio.sleep(heartbeat_interval)
                        try:
                            await self.queue.heartbeat(cid, [jid])
                        except Exception as hb_err:
                            logger.warning("Heartbeat failed for job %d: %s", jid, hb_err)

                heartbeat_task = asyncio.create_task(
                    _heartbeat(job.id, cid)
                )
                process_task.add_done_callback(
                    lambda _: heartbeat_task.cancel()
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Worker %d loop error: %s", worker_id, e)
                await asyncio.sleep(5)

    async def _process_job(self, job: Job, consumer_id: str) -> None:
        """Process a single job with timeout."""
        handler = get_handler(job.job_type)
        if handler is None:
            logger.warning(
                "No handler registered for job_type=%s (job %d)",
                job.job_type, job.id,
            )
            await self.queue.fail(job.id, f"No handler for {job.job_type}", retry=False)
            return

        logger.info(
            "Processing job %d (%s) from queue=%s",
            job.id, job.job_type, job.queue,
        )

        try:
            result = await asyncio.wait_for(
                handler(job.payload),
                timeout=job.timeout_seconds,
            )
            await self.queue.complete(job.id, result)
            logger.info("Job %d (%s) completed", job.id, job.job_type)

        except asyncio.TimeoutError:
            logger.warning("Job %d (%s) timed out after %ds", job.id, job.job_type, job.timeout_seconds)
            await self.queue.fail(job.id, f"Timeout after {job.timeout_seconds}s")
        except Exception as e:
            logger.error("Job %d (%s) failed: %s", job.id, job.job_type, e)
            await self.queue.fail(job.id, f"{type(e).__name__}: {e}")

    async def _scheduler_loop(self) -> None:
        """Tick the scheduler every 60 seconds."""
        while self._running:
            try:
                jobs = await self.queue.tick_scheduler()
                if jobs:
                    logger.info("Scheduler enqueued %d jobs: %s", len(jobs), [j.job_type for j in jobs])
            except Exception as e:
                logger.error("Scheduler tick failed: %s", e)
            await asyncio.sleep(60)

    async def status(self) -> dict:
        """Return current worker status."""
        return {
            "consumer_id": self.consumer_id,
            "running": self._running,
            "active_jobs": len(self._active_jobs),
            "active_job_ids": list(self._active_jobs.keys()),
            "uptime_seconds": None,  # TODO: track start time
        }


# ── Standalone entry point ───────────────────────────────

_worker_instance: Worker | None = None


async def run_worker(concurrency: int = 4, dsn: str | None = None) -> None:
    """Run the worker until SIGINT/SIGTERM.

    This is the entry point for ``aiw queue worker``.
    """
    global _worker_instance
    if dsn is None:
        from ai_workspace.core.db import get_db_url
        dsn = get_db_url()

    _worker_instance = Worker(dsn=dsn)

    # Register signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(_worker_instance.stop()),
        )

    print(f"[worker] Starting with {concurrency} slots...")
    print(f"[worker] Consumer ID: {_worker_instance.consumer_id}")
    print()

    await _worker_instance.start(concurrency=concurrency)


def start_worker_sync(concurrency: int = 4, dsn: str | None = None) -> None:
    """Synchronous entry point for CLI."""
    asyncio.run(run_worker(concurrency=concurrency, dsn=dsn))
