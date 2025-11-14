import logging


class ContextFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.task_id = None

    def set_task_id(self, task_id):
        self.task_id = task_id

    def filter(self, record):
        if self.task_id:
            record.task_id = self.task_id
        else:
            record.task_id = ''
        return True


class Logger:
    def __init__(self):
        pass

    LOGGER_NAME = 'hik_video_downloader'
    _context_filter = None

    @staticmethod
    def init_logger(task_id=None, log_level='INFO'):
        level = getattr(logging, log_level, logging.INFO)
        logging.getLogger('werkzeug').setLevel(level)
        logger = Logger.get_logger()
        logger.setLevel(level)
        logger.propagate = False

        if logger.handlers:
            logger.handlers.clear()

        Logger._context_filter = ContextFilter()
        if task_id:
            Logger._context_filter.set_task_id(task_id)

        log_format = '%(asctime)s - %(levelname)s'
        if task_id:
            log_format += ' - [%(task_id)s]'
        log_format += ' - %(message)s'

        console_formatter = logging.Formatter(fmt=log_format, datefmt='%Y-%m-%d %H:%M:%S')

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(Logger._context_filter)
        logger.addHandler(console_handler)

    @staticmethod
    def get_logger():
        return logging.getLogger(Logger.LOGGER_NAME)

    @staticmethod
    def set_task_id(task_id):
        if Logger._context_filter:
            Logger._context_filter.set_task_id(task_id)
