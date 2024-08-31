import logging

from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)


# Custom formatter class
class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: Style.DIM+Fore.WHITE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelno, Fore.WHITE)
        log_message = super().format(record)
        return f"{log_color}{log_message}{Style.RESET_ALL}"
