"""
https://www.shift-journal.org/library
"""

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from dl_utils import download_pdf, request_url
from fake_useragent import UserAgent

KEY_ID = "id"
LIST_URL = "https://zcpgslkimjjnmwatmkje.supabase.co/rest/v1/articles"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpjcGdzbGtpbWpqbm13YXRta2plIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4NjQ3MzcsImV4cCI6MjA4ODQ0MDczN30.uIwglLgrQEp20VyGy5IhOZK9y2IrE5oG9DFGBgOeNpk"
DOMAIN = "zcpgslkimjjnmwatmkje.supabase.co"


def process_config(save_file, force=False, page_limit=-1):
    ua = UserAgent(platforms=["desktop"])
    headers = {"User-Agent": ua.random, "apikey": API_KEY}
    config = {}
    save_path = Path(save_file)
    if save_path.exists():
        with open(save_file, encoding="utf-8") as f:
            config = json.load(f)

    url = LIST_URL
    data_list = request_url(url, headers, is_json=True)
    if not data_list:
        return

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

    item_list = sorted(item_list, key=lambda x: x[KEY_ID])
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
        file_id = item[KEY_ID]
        sub_dir = file_id[:2]
        if list(Path(output_dir, sub_dir).glob(f"{file_id}*")):
            continue

        url = item["file_url"]
        if not url.startswith("http") or DOMAIN not in url:
            logging.info(f"Ignore url = {url}")
            continue

        suffix = url.split("?")[0].split(".")[-1].lower()
        if suffix not in ["doc", "docx", "pdf"]:
            logging.warning(f"Error suffix = {suffix}")
            continue

        pdf_file = Path(output_dir, sub_dir, f"{file_id}.{suffix}")
        if pdf_file.exists():
            continue

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
    parser.add_argument("--page-limit", type=int, default=-1)
    parser.add_argument("--force", action="store_true")

    args = parser.parse_args()
    logging.info(f"args = {args}")

    # process_config(args.config, args.force, args.page_limit)
    process_pdf(args.config, args.pdf, args.pdf_limit)
