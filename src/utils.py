import os
from dotenv import load_dotenv
from datetime import datetime


def load_env():
    # 현재 파일 위치 기준으로 .env 파일 경로 설정
    env_path = os.path.join(os.path.dirname(__file__), "../.env")
    load_dotenv(dotenv_path=env_path)


def convert_date_format(int_date):
    """
    Converts an integer date to a new format.

    Args:
        int_date (int): Date in the format "YYYYMMDD".

    Returns:
        str: Date in the format "YYMM".
    """
    try:
        date_str = str(int_date)
        date_obj = datetime.strptime(date_str, "%Y%m%d")
        return date_obj.strftime("%y%m")
    except ValueError as e:
        print(f"Invalid date format: {e}")
        return None
