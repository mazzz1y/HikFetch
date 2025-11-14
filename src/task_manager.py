import logging
import queue
import random
import string
import threading
import uuid
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class Task:
    def __init__(self, task_id, params):
        self.task_id = task_id
        self.display_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        self.params = params
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.total = 0
        self.current_file = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.cancel_flag = threading.Event()
        self.execution_thread = None

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'display_id': self.display_id,
            'status': self.status.value,
            'progress': self.progress,
            'total': self.total,
            'current_file': self.current_file,
            'error': self.error,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result': self.result,
            'params': self.params
        }

    def is_cancelled(self):
        return self.cancel_flag.is_set()

    def cancel(self):
        self.cancel_flag.set()
        if self.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            self.status = TaskStatus.CANCELLED
            self.completed_at = datetime.now()


class TaskManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TaskManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.tasks = {}
        self.task_queue = queue.Queue()
        self.worker_thread = None
        self.running = False
        self.execution_semaphore = threading.Semaphore(1)
        self._initialized = True

    def start(self):
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()

    def stop(self):
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)

    def _worker(self):
        while self.running:
            try:
                task_id = self.task_queue.get(timeout=1)
                task = self.tasks.get(task_id)

                if task:
                    if task.is_cancelled():
                        if task.status == TaskStatus.PENDING:
                            task.completed_at = datetime.now()
                    else:
                        task.execution_thread = threading.Thread(
                            target=self._execute_task_wrapper,
                            args=(task,),
                            daemon=True
                        )
                        task.execution_thread.start()

                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")

    def _execute_task_wrapper(self, task):
        with self.execution_semaphore:
            try:
                self._execute_task(task)
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = f"Task execution error: {str(e)}"
                task.completed_at = datetime.now()

    def _execute_task(self, task):
        if task.is_cancelled():
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            return

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        try:
            from src.downloader import MediaDownloader

            downloader = MediaDownloader(task.params['config'])

            task.progress = 0
            task.total = 0

            result = downloader.download(
                camera_url=task.params['camera_url'],
                user_name=task.params['user_name'],
                user_password=task.params['user_password'],
                start_datetime_str=task.params['start_datetime_str'],
                end_datetime_str=task.params['end_datetime_str'],
                camera_channel=task.params['camera_channel'],
                task=task
            )

            if task.is_cancelled():
                task.status = TaskStatus.CANCELLED
            elif result['status'] == 'success':
                task.status = TaskStatus.COMPLETED
                task.result = result
            else:
                task.status = TaskStatus.FAILED
                task.error = result.get('message', 'Unknown error')

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)

        finally:
            task.completed_at = datetime.now()

    def create_task(self, params):
        task_id = str(uuid.uuid4())
        task = Task(task_id, params)
        self.tasks[task_id] = task
        self.task_queue.put(task_id)
        return task_id

    def get_task(self, task_id):
        return self.tasks.get(task_id)

    def get_all_tasks(self):
        return list(self.tasks.values())

    def cancel_task(self, task_id):
        task = self.tasks.get(task_id)
        if task:
            task.cancel()
            return True
        return False
