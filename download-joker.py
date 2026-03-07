import argparse
import json
import logging
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

from fake_useragent import UserAgent
from parsel import Selector

from dl_utils import download_pdf, request_url

COUNT = 12
KEY_ID = "id"
BASE_URL = "https://jokerofacademics.com/"
LIST_URL = "https://jokerofacademics.com/articles.php?page={page}"
PDF_URL = "https://jokerofacademics.com/download.php?id={id}"


def strip(value):
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    elif isinstance(value, list):
        return [strip(v) for v in value]
    elif isinstance(value, dict):
        return {k: strip(v) for k, v in value.items()}
    return value


def parse_count(selector) -> int:
    result = selector.css("span.result-count ::text").get()
    if result:
        nums = re.findall(r"\d+", result)
        if nums:
            return int(nums[0])
    return 0


def parse_list(selector) -> list[dict]:
    items = selector.css("div.article-list .article-card")
    output = []
    for item in items:
        cover = item.css("div.card-cover img").xpath("@src").get()
        card_body = item.css("div.card-body")
        tags = card_body.css(".card-tag ::text").getall()
        anchor = card_body.css("h2.card-title a")
        title = anchor.css("::text").get()
        link = anchor.xpath("@href").get()
        file_id = int(link.split("?id=")[-1])
        authors = card_body.css("div.card-author ::text").get()
        abstract = card_body.css("p.card-abstract ::text").get()
        meta = card_body.css("div.card-meta>span ::text").getall()
        # .card-read-more
        entry = {
            "id": file_id,
            "title": strip(title),
            "link": urljoin(BASE_URL, link),
            "cover": cover,
            "authors": strip(authors),
            "tags": strip(tags),
            "meta": strip(meta),
            "abstract": strip(abstract),
        }
        output.append(entry)
    return output


def process_config(save_file, force=False, page_limit=-1):
    ua = UserAgent(platforms=["desktop"])
    headers = {"User-Agent": ua.random}
    config = {}
    save_path = Path(save_file)
    if save_path.exists():
        with open(save_file, encoding="utf-8") as f:
            config = json.load(f)

    url = LIST_URL.split("?")[0]
    html_text = request_url(url, headers)
    if not html_text:
        return
    selector = Selector(text=html_text)
    total = parse_count(selector)
    items = parse_list(selector)
    items_count = len(items)
    if items_count == 0:
        return

    pages = math.ceil(total / items_count)
    max_pages = min(pages, page_limit) if page_limit > 0 else pages
    logging.info(f"total = {total}, pages = {pages}, max_pages = {max_pages}")
    data_list = items
    for page in range(2, max_pages + 1):
        url = LIST_URL.format(page=page)
        html_text = request_url(url, headers)
        selector = Selector(text=html_text)
        items = parse_list(selector)
        if len(items) != items_count:
            logging.warning(f"item count = {len(items)}")
        data_list.extend(items)

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
        page_url = item["link"]
        if "?id=" not in page_url:
            logging.warning(f"Invalid url = {page_url}")
            continue

        file_id = item[KEY_ID]
        file_name = f"{file_id:05}"
        sub_dir = file_name[:2]
        pdf_file = Path(output_dir, sub_dir, f"{file_name}.pdf")
        if pdf_file.exists():
            continue
        url = PDF_URL.format(id=file_id)
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
