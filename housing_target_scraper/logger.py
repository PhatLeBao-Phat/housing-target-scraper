import logging
import sys
from colorama import Fore, Style

class CustomFormatter(logging.Formatter):
    LEVEL_NAME_WIDTH = 8  # Ensures log levels align properly (CRITICAL is longest)
    FUNC_NAME_WIDTH = 40  # Adjusted to 40 characters for function name
    
    FORMATS = {
        logging.DEBUG: Fore.CYAN + "%(asctime)s | %(funcName)-40s | DEBUG    | %(message)s" + Style.RESET_ALL,
        logging.INFO: Fore.GREEN + "%(asctime)s | %(funcName)-40s | INFO     | %(message)s" + Style.RESET_ALL,
        logging.WARNING: Fore.YELLOW + "%(asctime)s | %(funcName)-40s | WARNING  | %(message)s" + Style.RESET_ALL,
        logging.ERROR: Fore.RED + "%(asctime)s | %(funcName)-40s | ERROR    | %(message)s" + Style.RESET_ALL,
        logging.CRITICAL: Fore.RED + Style.BRIGHT + "%(asctime)s | %(funcName)-40s | CRITICAL | %(message)s" + Style.RESET_ALL
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, "%(asctime)s | %(funcName)-40s | %(levelname)-8s | %(message)s")
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

logger = logging.getLogger("my_logger")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("app.log")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter("%(asctime)s | %(funcName)-40s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(CustomFormatter())

logger.addHandler(file_handler)
logger.addHandler(console_handler)