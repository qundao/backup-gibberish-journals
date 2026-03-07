import argparse
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

from fake_useragent import UserAgent
from dl_utils import download_pdf, request_url

KEY_ID = "id"
BASE_URL = "https://rubbish-journal.org/"
LIST_URL = "https://rubbish-journal.org/en/articles"
# PDF_URL = "https://rubbish-journal.org/api/uploads/1772800179526.pdf"


def _parse_str(text):
    text2 = text.replace('\\"', '"').replace("\\\\", "\\")
    try:
        return json.loads(text2)
    except:
        return None


def parse_list_page(text: str) -> list[dict]:
    logging.info("Parse text")
    pattern1 = r"<script>self\.__next_f\.push\((.+?)\)</script>"
    pattern2 = r'\{\\"id\\":\\".*?\\"filePath\\".*?\}'
    results = re.findall(pattern1, text)
    candidates = [v for v in results if '\\"articles\\":[' in v]
    logging.debug(f"candidates = {len(candidates)}")
    articles = []
    for value in candidates:
        items = re.findall(pattern2, value)
        articles.extend(items)

    logging.debug(f"articles = {len(articles)}")
    output = [_parse_str(item) for item in articles]
    output = [item for item in _parse_str if item]
    return output


def process_config(save_file, force):
    ua = UserAgent(platforms=["desktop"])
    headers = {"User-Agent": ua.random}
    config = {}
    save_path = Path(save_file)
    if save_path.exists():
        with open(save_file, encoding="utf-8") as f:
            config = json.load(f)

    url = LIST_URL
    logging.info(f"Request = {url}")
    html_text = request_url(url, headers)
    if not html_text:
        return
    data_list = parse_list_page(html_text)

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

    item_list = sorted(item_list, key=lambda x: x["doi"], reverse=True)
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


def process_pdf(config_file, output_dir, limit):
    ua = UserAgent(platforms=["desktop"])
    headers = {"User-Agent": ua.random}
    count = 0

    if not Path(config_file).exists():
        logging.warning(f"No file = {config_file}")
        return
    if limit > 0 and count > limit:
        return

    with open(config_file, encoding="utf-8") as f:
        config_data = json.load(f)

    for item in config_data["data"]:
        file_path = item["filePath"]
        if "api/uploads" not in file_path:
            logging.warning(f"Invalid file path = {file_path}")
            continue

        file_id = item[KEY_ID]
        sub_dir = file_id[:2]
        suffix = file_path.split(".")[-1]
        pdf_file = Path(output_dir, sub_dir, f"{file_id}.{suffix}")
        if pdf_file.exists():
            continue
        url = urljoin(BASE_URL, file_path)
        download_pdf(url, pdf_file, headers)
        count += 1
        if limit > 0 and count > limit:
            break

    logging.info(f"Download {count}")


if __name__ == "__main__":
    fmt = "%(asctime)s %(levelname)s %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt)

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config.json")
    parser.add_argument("--pdf", type=str, default="pdf")
    parser.add_argument("--pdf-limit", type=int, default=-1)
    parser.add_argument("--force", action="store_true")

    args = parser.parse_args()
    logging.info(f"args = {args}")

    process_config(args.config, args.force)
    process_pdf(args.config, args.pdf, args.pdf_limit)
