import logging
import os


def setup_logger():
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # file_handler = logging.FileHandler('app.log')
    # file_handler.setLevel(logging.DEBUG)
    # logging.getLogger('').addHandler(file_handler)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging set to {log_level} level")
    return logger
