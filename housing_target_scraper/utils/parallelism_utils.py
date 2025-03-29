from typing import Callable, List, Tuple
import concurrent.futures

DEFAULT_MAX_WORKER = 12

class ParallelOfficer:
    """Responsible for handling parallelized computation."""

    def __init__(self, max_worker : int = DEFAULT_MAX_WORKER):
        self.max_worker = max_worker
    
    def process_parallel_list(self, item_list : List, func : Callable):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(func, i) for i in item_list]

            concurrent.futures.wait(futures)

        return [f.result() for f in futures]
    



        