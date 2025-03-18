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

def info(message: str):
    logger.debug(f'{friendly_datetime()}: {message}')

def error(e: Exception):
    if e is Exception:
        logger.error(f'{friendly_datetime()}: {str(e)}')
    else:
        logger.error(f'{friendly_datetime()}: {e}')

