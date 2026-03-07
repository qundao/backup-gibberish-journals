import logging
import random
import time
from pathlib import Path

import requests


def random_sleep(max_delay: float = 3.0, min_delay: float = 0.1):
    delay = random.random() * max_delay + min_delay
    logging.debug(f"Random sleep = {delay:.3f}")
    time.sleep(delay)


def request_url(url: str, headers: dict, is_json: bool = False) -> None | str | dict:
    logging.info(f"Request = {url}")
    try:
        res = requests.get(url, headers=headers)
        random_sleep()
        if res.status_code != 200:
            logging.warning("Error code = {res.status_code}")
            return None
        return res.json() if is_json else res.text
    except Exception as e:
        logging.error(f"request failed, {e}")
    return None


def download_pdf(url: str, save_file: str, headers: dict, chunk_size=8192):
    logging.info(f"Request = {url}")
    save_parent = Path(save_file).parent
    if not save_parent.exists():
        save_parent.mkdir(parents=True)

    try:
        with requests.get(url, stream=True, headers=headers) as res:
            res.raise_for_status()
            random_sleep(5, 2)
            # total_size = int(res.headers.get('content-length', 0))
            with open(save_file, "wb") as f:
                for chunk in res.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
            return True
    except Exception as e:
        logging.error(f"request failed, {e}")
    return False
