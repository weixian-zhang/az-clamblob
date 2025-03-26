import logging
from opencensus.ext.azure.log_exporter import AzureLogHandler
from config import Config
from datetime import datetime
import pytz

config = Config()

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)
logger.addHandler(AzureLogHandler(
    connection_string=f'InstrumentationKey={config.appinsights_key}')
)

# log with time
def friendly_datetime(time_zone='Asia/Singapore'):
        return datetime.now().astimezone(pytz.timezone(time_zone)).strftime("%a %d %b %Y %H:%M:%S")

def info(message: str, module=''):
    msg = f'{friendly_datetime()} | {module} - {message}' if module else f'{friendly_datetime()} - {message}'
    logger.debug(msg)

def error(e: Exception, module=''):
    msg = f'{friendly_datetime()} | {module} - {str(e)}' if module else f'{friendly_datetime()} - {str(e)}'
    logger.error(msg)

