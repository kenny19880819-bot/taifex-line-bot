import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from PIL import Image


LIST_URL = "https://www.spf.com.tw/sinopacSPF/research/list.do?id=1709f20d3ff00000d8e2039e8984ed51"
REPORT_TITLE = "台指期籌碼快訊"
REPORTS_DIR = Path("reports")
METADATA_FILE = REPORTS_DIR / "current.json"
SENT_FILE = REPORTS_DIR / "sent_dates.txt"
HEADERS = {"User-Agent": "Mozilla/5.0 taifex-line-bot/1.0"}


def set_output(name: str, value: str) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")
    print(f"{name}={value}")


def already_sent(report_date: str) -> bool:
    if not SENT_FILE.exists():
        return False
    return report_date in {
        line.strip() for line in SENT_FILE.read_text(encoding="utf-8").splitlines()
    }


def locate_today_report(today_slash: str) -> str | None:
    response = requests.get(LIST_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    for link in soup.find_all("a"):
        if link.get_text(" ", strip=True) != REPORT_TITLE:
            continue
        surrounding_text = link.parent.get_text(" ", strip=True)
        match = re.search(r"\d{4}/\d{2}/\d{2}", surrounding_text)
        if match and match.group(0) == today_slash:
            href = link.get("href")
            if href:
                return urljoin(LIST_URL, href)
    return None


def create_images(pdf_path: Path, report_date: str) -> list[dict[str, str]]:
    prefix = REPORTS_DIR / f"{report_date}-page"
    subprocess.run(
        [
            "pdftoppm",
            "-jpeg",
            "-r",
            "180",
            "-jpegopt",
            "quality=90",
            str(pdf_path),
            str(prefix),
        ],
        check=True,
    )

    images = []
    page_files = [
        path
        for path in REPORTS_DIR.glob(f"{report_date}-page-*.jpg")
        if re.fullmatch(rf"{re.escape(report_date)}-page-\d+", path.stem)
    ]
    page_files.sort(key=lambda p: int(p.stem.rsplit("-", 1)[1]))
    if not page_files:
        raise RuntimeError("PDF 沒有成功轉換成圖片")

    for page_file in page_files:
        preview_file = page_file.with_name(f"{page_file.stem}-preview.jpg")
        with Image.open(page_file) as image:
            image.thumbnail((1000, 1000 * image.height // image.width))
            image.convert("RGB").save(preview_file, "JPEG", quality=72, optimize=True)

        if page_file.stat().st_size > 10 * 1024 * 1024:
            raise RuntimeError(f"原圖超過 LINE 10 MB 上限：{page_file}")
        if preview_file.stat().st_size > 1024 * 1024:
            raise RuntimeError(f"預覽圖超過 LINE 1 MB 上限：{preview_file}")

        images.append({"original": page_file.name, "preview": preview_file.name})
    return images


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    today = datetime.now(ZoneInfo("Asia/Taipei"))
    report_date = today.strftime("%Y-%m-%d")
    today_slash = today.strftime("%Y/%m/%d")

    if already_sent(report_date):
        set_output("status", "already_sent")
        return

    pdf_url = locate_today_report(today_slash)
    if not pdf_url:
        set_output("status", "not_found")
        return

    response = requests.get(pdf_url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    if not response.content.startswith(b"%PDF"):
        raise RuntimeError("下載內容不是 PDF")

    pdf_path = REPORTS_DIR / f"{report_date}.pdf"
    pdf_path.write_bytes(response.content)
    images = create_images(pdf_path, report_date)
    pdf_path.unlink(missing_ok=True)

    metadata = {
        "date": report_date,
        "pdf_url": pdf_url,
        "images": images,
    }
    METADATA_FILE.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    set_output("status", "new")
    set_output("report_date", report_date)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
