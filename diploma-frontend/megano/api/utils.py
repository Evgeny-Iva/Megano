from django.utils.dateformat import format
from datetime import datetime
import pytz
import logging


logger = logging.getLogger(__name__)


def format_datetime(dt):
    """Получает dt данные возвращает строку date_str"""
    if dt is None:
        logger.warning(f"format_datetime получил None вместо datetime")
        return ''

    if not isinstance(dt, datetime):
        logger.error(f"format_datetime получил {type(dt)} вместо datetime. Значение: {dt}")
        return ''

    date_str = format(
        dt.astimezone(pytz.timezone('Europe/Moscow')),
        'D M d Y H:i:s O'
    )
    return date_str