from datetime import datetime
import pytz

class Util:

    @staticmethod
    def full_blob_name(container_name, blob_name) -> str:
        return f"{container_name}/{blob_name}"
    
    @staticmethod
    def friendly_date() -> str:
        return datetime.now().astimezone(pytz.timezone('Asia/Singapore')).strftime("%a %d %b %Y %H:%M:%S")
    

    @staticmethod
    def get_blob_name_to_file_share(container_name: str, blob_name: str) -> str:
        blob_without_backslash = blob_name.replace('/', '-')
        return f"{container_name}-{blob_without_backslash}"