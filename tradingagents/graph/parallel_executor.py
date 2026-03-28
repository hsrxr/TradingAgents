"""
Parallel execution utilities for trading agents.
Provides tools for concurrent execution of independent tasks.
"""

import asyncio
import time
from typing import Callable, List, Dict, Any, Coroutine, TypeVar
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging

T = TypeVar('T')

logger = logging.getLogger(__name__)


class ParallelExecutor:
    """Executor for running multiple independent tasks in parallel."""

    def __init__(self, max_workers: int = 4, use_threads: bool = True):
        """Initialize parallel executor.
        
        Args:
            max_workers: Maximum number of concurrent workers
            use_threads: If True, use ThreadPoolExecutor. If False, use ProcessPoolExecutor.
        """
        self.max_workers = max_workers
        self.use_threads = use_threads
        self.executor = ThreadPoolExecutor(max_workers=max_workers) if use_threads \
                       else ProcessPoolExecutor(max_workers=max_workers)

    def run_parallel(self, tasks: List[Callable[[], T]]) -> List[T]:
        """Run multiple callable tasks in parallel.
        
        Args:
            tasks: List of callable functions to execute
            
        Returns:
            List of results in the same order as input tasks
        """
        results = []
        start_time = time.time()
        
        try:
            futures = [self.executor.submit(task) for task in tasks]
            for future in futures:
                results.append(future.result())
            
            elapsed = time.time() - start_time
            logger.info(f"Parallel execution completed in {elapsed:.2f}s")
        except Exception as e:
            logger.error(f"Error during parallel execution: {e}")
            raise
        
        return results

    def run_parallel_dict(self, tasks: Dict[str, Callable[[], T]]) -> Dict[str, T]:
        """Run named tasks in parallel and return dict of results.
        
        Args:
            tasks: Dictionary of task_name -> callable
            
        Returns:
            Dictionary of task_name -> result
        """
        results = {}
        start_time = time.time()
        
        try:
            futures = {name: self.executor.submit(task) 
                      for name, task in tasks.items()}
            for name, future in futures.items():
                results[name] = future.result()
            
            elapsed = time.time() - start_time
            logger.info(f"Parallel execution completed in {elapsed:.2f}s")
        except Exception as e:
            logger.error(f"Error during parallel execution: {e}")
            raise
        
        return results

    def shutdown(self):
        """Shutdown the executor."""
        self.executor.shutdown(wait=True)


class AsyncParallelExecutor:
    """Executor for running async tasks concurrently."""

    async def run_parallel_async(self, tasks: List[Coroutine]) -> List[Any]:
        """Run multiple coroutines concurrently.
        
        Args:
            tasks: List of coroutines to execute
            
        Returns:
            List of results in the same order as input tasks
        """
        start_time = time.time()
        try:
            results = await asyncio.gather(*tasks, return_exceptions=False)
            elapsed = time.time() - start_time
            logger.info(f"Async parallel execution completed in {elapsed:.2f}s")
            return results
        except Exception as e:
            logger.error(f"Error during async parallel execution: {e}")
            raise

    @staticmethod
    async def run_with_timeout(coro: Coroutine, timeout: float = 300.0) -> Any:
        """Run a coroutine with timeout.
        
        Args:
            coro: Coroutine to execute
            timeout: Timeout in seconds (default 5 minutes)
            
        Returns:
            Result of coroutine
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"Coroutine timed out after {timeout}s")
            raise


def parallel_map(func: Callable[[T], Any], items: List[T], 
                max_workers: int = 4) -> List[Any]:
    """Apply function to list of items in parallel.
    
    Args:
        func: Function to apply
        items: List of items to process
        max_workers: Maximum number of concurrent workers
        
    Returns:
        List of results
    """
    executor = ParallelExecutor(max_workers=max_workers)
    try:
        return executor.run_parallel([lambda i=item: func(i) for item in items])
    finally:
        executor.shutdown()


async def async_parallel_map(afunc: Callable[[T], Coroutine], 
                            items: List[T]) -> List[Any]:
    """Apply async function to list of items concurrently.
    
    Args:
        afunc: Async function to apply
        items: List of items to process
        
    Returns:
        List of results
    """
    executor = AsyncParallelExecutor()
    tasks = [afunc(item) for item in items]
    return await executor.run_parallel_async(tasks)
