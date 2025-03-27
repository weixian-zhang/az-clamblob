import logging
from opencensus.ext.azure.log_exporter import AzureLogHandler
from config import Config
from util import Util

config = Config()

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)
logger.addHandler(AzureLogHandler(
    connection_string=f'{config.appinsights_conn_str}')
)


def info(message: str, module=''):
    msg = f'{Util.friendly_date()} | {module} - {message}' if module else f'{Util.friendly_date()} - {message}'
    logger.debug(msg)

def error(e: Exception, module=''):
    msg = f'{Util.friendly_date()} | {module} - {str(e)}' if module else f'{Util.friendly_date()} - {str(e)}'
    logger.error(msg)

