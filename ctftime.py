import datetime
import json

import requests
from requests import HTTPError

HEADERS = {
    'User-Agent': 'WolvSec Discord Bot/0.1.0',
}

BASE_URL = f'https://ctftime.org/api/v1/events/'


def wrap_response(response):
    if not response.ok:
        raise HTTPError()
    return json.loads(response.content)


def get_upcoming(start: datetime.datetime = None, finish: datetime.datetime = None, limit: int = 100) -> dict:
    start = start or datetime.datetime.utcnow()
    finish = finish or start + datetime.timedelta(weeks=1)
    if start >= finish:
        raise Exception('Start must be before end')
    start_timestamp = int(start.timestamp())
    finish_timestamp = int(finish.timestamp())
    response = requests.get(f'{BASE_URL}?limit={limit}&start={start_timestamp}&finish={finish_timestamp}',
                            headers=HEADERS)
    return wrap_response(response)


def get_event(event_id: int) -> dict:
    response = requests.get(f'{BASE_URL}{event_id}/', headers=HEADERS)
    return wrap_response(response)