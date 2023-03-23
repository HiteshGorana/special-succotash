import logging

logger = logging.getLogger()

if logging.getLogger("gunicorn.error").hasHandlers():
    logger = logging.getLogger("gunicorn.error")

if logging.getLogger("uvicorn").hasHandlers():
    logger = logging.getLogger("uvicorn")

logger.handlers[0].setFormatter(
    logging.Formatter(
        "%(asctime)s %(levelname)-8s [%(filename)s::%(funcName)s:%(lineno)d]\t %(message)s"
    )
)


def show_error(f):
    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.exception(e)

    return inner
