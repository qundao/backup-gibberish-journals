import argparse
import json
import logging
import math
import random
import time
from datetime import UTC, datetime
from pathlib import Path

import requests
from fake_useragent import UserAgent

ZONE = ["latrine", "septic", "stone", "sediment"]
SORT_KEY = ["newest", "highest_rated", "most_rated", "hottest"]
API_URL = "https://api.shitjournal.org/api/articles/?zone={zone}&sort={sort}&discipline=all&page={page}&limit={limit}"
PDF_URL = "https://files.shitjournal.org/{id}.pdf"
KEY_ID = "id"


def random_sleep(max_delay: float = 3.0, min_delay: float = 0.1):
    delay = random.random() * max_delay + min_delay
    logging.debug(f"Random sleep = {delay:.3f}")
    time.sleep(delay)


def request_json(url: str, headers: dict) -> None | dict:
    logging.info(f"Request = {url}")
    try:
        res = requests.get(url, headers=headers)
        random_sleep()
        if res.status_code != 200:
            logging.warning("Error code = {res.status_code}")
            return None
        return res.json()
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


def download_api_data(save_file, key, sort_key, limit=10, force=False, page_limit=-1):
    ua = UserAgent(platforms=["desktop"])
    headers = {"User-Agent": ua.random}
    config = {}
    save_path = Path(save_file)
    if save_path.exists():
        with open(save_file, encoding="utf-8") as f:
            config = json.load(f)

    url = API_URL.format(zone=key, page=1, sort=sort_key, limit=limit)
    result = request_json(url, headers)
    if not result:
        return

    count = result["count"]
    if not force and count == config.get("count", 0):
        logging.info("No update")
        return

    # pages = result['total_pages']
    pages = math.ceil(count / limit)
    data_list = result["data"]
    max_pages = min(pages + 1, page_limit) if page_limit > 0 else pages + 1
    for page in range(2, max_pages):
        url = API_URL.format(zone=key, page=page, sort=sort_key, limit=limit)
        result = request_json(url, headers)
        if result and result.get("data"):
            data_list.extend(result["data"])
        if result is None:
            break

    data_list2 = list({d[KEY_ID]: d for d in data_list}.values())
    logging.info(f"New data = {len(data_list2)}")
    if not force:
        logging.info("Update data")
        item_list = config.get("data", [])
        existed_id = [item[KEY_ID] for item in item_list]
        item_list += [item for item in data_list2 if item[KEY_ID] not in existed_id]
    else:
        logging.info("Flush data")
        item_list = data_list2

    item_list = sorted(item_list, key=lambda x: x["created_at"], reverse=True)
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S%z")
    save_data = {
        "update": now,
        "count": len(item_list),
        "data": item_list,
    }
    if not save_path.parent.exists():
        save_path.parent.mkdir(parents=True)
    with open(save_file, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)


def process_config(config_dir, limit, force, page_limit):
    sort_key = SORT_KEY[0]
    for zone in ZONE:
        config_file = Path(config_dir, f"{zone}.json")
        download_api_data(config_file, zone, sort_key, limit, force, page_limit)


def process_pdf(config_dir, output_dir, limit):
    ua = UserAgent(platforms=["desktop"])
    headers = {"User-Agent": ua.random}
    count = 0
    for zone in ZONE:
        config_file = Path(config_dir, f"{zone}.json")
        if not Path(config_file).exists():
            continue
        if limit > 0 and count > limit:
            break

        with open(config_file, encoding="utf-8") as f:
            config_data = json.load(f)

        for item in config_data["data"]:
            file_id = item[KEY_ID]
            sub_dir = file_id[:2]
            pdf_file = Path(output_dir, sub_dir, f"{file_id}.pdf")
            if pdf_file.exists():
                continue
            url = PDF_URL.format(id=file_id)
            download_pdf(url, pdf_file, headers)
            count += 1
            if limit > 0 and count > limit:
                break


if __name__ == "__main__":
    fmt = "%(asctime)s %(levelname)s %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt)

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config")
    parser.add_argument("--pdf", type=str, default="pdf")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--pdf-limit", type=int, default=-1)
    parser.add_argument("--pages", type=int, default=-1)
    parser.add_argument("--force", action="store_true")

    args = parser.parse_args()
    logging.info(f"args = {args}")

    process_config(args.config, args.limit, args.force, args.pages)
    process_pdf(args.config, args.pdf, args.pdf_limit)
