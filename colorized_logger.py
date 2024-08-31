import logging

from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

PROGRESS = logging.INFO + 1
SKIP = logging.INFO + 2
DESTRUCTIVE = logging.WARNING + 1
STOP = logging.WARNING + 2
ROLLBACK = logging.ERROR + 1


# Custom formatter class
class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: Style.DIM + Fore.WHITE,
        logging.INFO: Fore.GREEN,
        PROGRESS: Fore.CYAN,
        SKIP: Fore.MAGENTA,
        logging.WARNING: Fore.YELLOW,
        DESTRUCTIVE: Style.BRIGHT + Fore.YELLOW,
        STOP: Fore.BLUE,
        logging.ERROR: Fore.RED,
        ROLLBACK: Fore.MAGENTA,
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelno, Fore.WHITE)
        log_message = super().format(record)
        return f"{log_color}{log_message}{Style.RESET_ALL}"
