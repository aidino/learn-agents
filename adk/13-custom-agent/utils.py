import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    

def print_colorful_log(logger, label, message):
    deco_str_top = f"╔══ {label.upper()} ═════════════════════════════════════════"
    deco_str_bottom = f"╚{'═'*(len(deco_str_top)-1)}"
    logger.info(f"{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}{deco_str_top}{Colors.RESET}")
    logger.info(f"{Colors.CYAN}{Colors.BOLD}{message}{Colors.RESET}")
    logger.info(f"{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}{deco_str_bottom}{Colors.RESET}\n")
    
if __name__ == "__main__":
    print_colorful_log(logger, "agent response", "Hello, world!")