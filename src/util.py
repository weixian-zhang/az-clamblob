from datetime import datetime
import pytz

class Util:

    @staticmethod
    def full_blob_name(container_name, blob_name) -> str:
        return f"{container_name}/{blob_name}"
    
    @staticmethod
    def friendly_date() -> str:
        return datetime.now().astimezone(pytz.timezone('Asia/Singapore')).strftime("%a %d %b %Y %H:%M:%S")