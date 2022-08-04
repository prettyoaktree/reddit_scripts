import logging
LOGGER_NAME = 'elizabot'

def get_bot_logger():

    # Define logger format string
    logger_format_string = '[%(funcName)s] [%(lineno)d] [%(levelname)s]: %(message)s'

    # Initialize the logger
    logger_handler = logging.StreamHandler()
    logger_handler.setLevel(logging.DEBUG)
    logger_formatter = logging.Formatter(logger_format_string)
    logger_handler.setFormatter(logger_formatter) 
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(logger_handler)
    logger.setLevel(logging.DEBUG)

    return logger

