import asyncio
import heapq
from typing import Any, Callable, Optional, Tuple
from enum import Enum
import structlog
import time

logger = structlog.get_logger()


class Priority(Enum):
    """Request priority levels."""

    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


class PriorityQueue:
    """Priority queue for request processing."""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.queue = []
        self.running_tasks = 0
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._shutdown = False

    async def add_request(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: Priority = Priority.NORMAL,
        timeout: Optional[float] = None,
    ) -> Any:
        """Add a request to the priority queue."""
        if self._shutdown:
            raise RuntimeError("Queue is shutting down")

        if kwargs is None:
            kwargs = {}

        # Create a unique identifier for this request
        request_id = f"{func.__name__}_{int(time.time() * 1000)}"

        # Create the task wrapper
        task_wrapper = PriorityTask(
            request_id=request_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            created_at=time.time(),
        )

        # Add to priority queue (heapq uses min-heap, so lower priority = higher priority)
        heapq.heappush(self.queue, task_wrapper)

        logger.debug(
            "Request added to priority queue",
            request_id=request_id,
            priority=priority.name,
            queue_size=len(self.queue),
        )

        # Process the queue
        return await self._process_queue()

    async def _process_queue(self) -> Any:
        """Process requests from the priority queue."""
        if not self.queue or self.running_tasks >= self.max_concurrent:
            return None

        # Get the highest priority request
        task_wrapper = heapq.heappop(self.queue)

        # Acquire semaphore
        await self.semaphore.acquire()
        self.running_tasks += 1

        try:
            # Execute the task
            result = await self._execute_task(task_wrapper)
            return result
        finally:
            self.running_tasks -= 1
            self.semaphore.release()

            # Continue processing if there are more requests
            if self.queue and not self._shutdown:
                asyncio.create_task(self._process_queue())

    async def _execute_task(self, task_wrapper: "PriorityTask") -> Any:
        """Execute a single task."""
        try:
            logger.debug(
                "Executing priority task",
                request_id=task_wrapper.request_id,
                priority=task_wrapper.priority.name,
                wait_time=time.time() - task_wrapper.created_at,
            )

            if task_wrapper.timeout:
                result = await asyncio.wait_for(
                    task_wrapper.func(*task_wrapper.args, **task_wrapper.kwargs),
                    timeout=task_wrapper.timeout,
                )
            else:
                result = await task_wrapper.func(
                    *task_wrapper.args, **task_wrapper.kwargs
                )

            logger.debug(
                "Priority task completed",
                request_id=task_wrapper.request_id,
                execution_time=time.time() - task_wrapper.created_at,
            )

            return result

        except asyncio.TimeoutError:
            logger.warning(
                "Priority task timed out",
                request_id=task_wrapper.request_id,
                timeout=task_wrapper.timeout,
            )
            raise
        except Exception as e:
            logger.error(
                "Priority task failed", request_id=task_wrapper.request_id, error=str(e)
            )
            raise

    def get_stats(self) -> dict:
        """Get queue statistics."""
        return {
            "queue_size": len(self.queue),
            "running_tasks": self.running_tasks,
            "max_concurrent": self.max_concurrent,
            "available_slots": self.max_concurrent - self.running_tasks,
        }

    async def shutdown(self):
        """Shutdown the queue gracefully."""
        self._shutdown = True
        logger.info("Priority queue shutting down", remaining_tasks=len(self.queue))


class PriorityTask:
    """Wrapper for tasks in the priority queue."""

    def __init__(
        self,
        request_id: str,
        func: Callable,
        args: tuple,
        kwargs: dict,
        priority: Priority,
        timeout: Optional[float],
        created_at: float,
    ):
        self.request_id = request_id
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.priority = priority
        self.timeout = timeout
        self.created_at = created_at

    def __lt__(self, other):
        """Comparison for heapq (lower priority value = higher priority)."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        # If same priority, older requests have higher priority
        return self.created_at < other.created_at


# Global priority queue instance
priority_queue = PriorityQueue(max_concurrent=20)
