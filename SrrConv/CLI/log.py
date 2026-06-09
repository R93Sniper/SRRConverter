import logging
from .default_properties import get_default_property

try:
    from colorama import init, Fore, Back, Style
except ImportError:
    init = None
    Fore = None
    Back = None
    Style = None

RESET = Style.RESET_ALL if Style else ""

DEBUG_TITLE = f"{RESET}{Fore.BLACK}{Back.CYAN}" if Fore and Back else ""
DEBUG_TRACE = f"{RESET}{Fore.BLUE}" if Fore and Back else ""
DEBUG_MSG = f"{RESET}{Fore.CYAN}" if Fore else ""

INFO_TITLE = f"{RESET}{Fore.BLACK}{Back.GREEN}" if Fore and Back else ""
INFO_MSG = f"{RESET}{Fore.GREEN}" if Fore else ""

WARN_TITLE = f"{RESET}{Fore.BLACK}{Back.YELLOW}" if Fore and Back else ""
WARN_MSG = f"{RESET}{Fore.YELLOW}" if Fore else ""

ERR_TITLE = f"{RESET}{Fore.BLACK}{Back.RED}" if Fore and Back else ""
ERR_MSG = f"{RESET}{Fore.RED}" if Fore else ""


class CustomFormatter(logging.Formatter):
    def __init__(self, fmt: str | None = None, colorized: bool = False):
        if init:
            init()
        super().__init__()
        self.fmt = fmt
        self.colorized = colorized

    def format(self, record: logging.LogRecord) -> str:
        match record.levelno:
            case logging.DEBUG:
                if self.colorized:
                    return f"{DEBUG_TITLE}Debug|{DEBUG_MSG} {record.msg} {DEBUG_TRACE}[{record.filename}:{record.lineno}]{RESET}"
                return f"Debug| {record.msg} [{record.filename}:{record.lineno}]"
            case logging.INFO:
                if self.colorized:
                    return f"{INFO_TITLE}Info |{INFO_MSG} {record.msg}{RESET}"
                return f"Info | {record.msg}"
            case logging.WARNING:
                if self.colorized:
                    return f"{WARN_TITLE}Warn |{WARN_MSG} {record.msg}{RESET}"
                return f"Warn | {record.msg}"
            case logging.ERROR:
                if self.colorized:
                    return f"{ERR_TITLE}Error|{ERR_MSG} {record.msg}{RESET}"
                return f"Error| {record.msg}"
            case _:
                return super().format(record)


def log_level_from_str(string: str) -> int | None:
    match string:
        case "debug": return logging.DEBUG
        case "info": return logging.INFO
        case "warning": return logging.WARNING
        case "error": return logging.ERROR
        case _: return None


def init_log(args) -> logging.Logger:
    """Initialize the logger using any arguments passed in the command."""
    logger = logging.getLogger("SrrConv")
    logger.handlers.clear()

    log_level = log_level_from_str(get_default_property("log_level", logger))
    if args.log_level:
        log_level = log_level_from_str(args.log_level)

    if log_level is None:
        return logger

    logger.setLevel(log_level)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(CustomFormatter("%(message)s", True))
    logger.addHandler(stream_handler)

    if args.write_log is not None:
        file_handler = logging.FileHandler(args.write_log, mode="w")
        file_handler.setFormatter(CustomFormatter("%(message)s"))
        logger.addHandler(file_handler)

    return logger