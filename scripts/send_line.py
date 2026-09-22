import json
import os
import time
from pathlib import Path
from urllib.parse import quote

import requests


LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
METADATA_FILE = Path("reports/current.json")
SENT_FILE = Path("reports/sent_dates.txt")


def raw_url(filename: str) -> str:
    repository = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    return (
        f"https://raw.githubusercontent.com/{repository}/{branch}/reports/"
        f"{quote(filename)}"
    )


def wait_until_public(url: str) -> None:
    for _ in range(12):
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            return
        time.sleep(5)
    raise RuntimeError(f"圖片尚未能從公開網址讀取：{url}")


def push(messages: list[dict]) -> None:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    group_id = os.environ["LINE_GROUP_ID"]
    response = requests.post(
        LINE_PUSH_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"to": group_id, "messages": messages},
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"LINE API {response.status_code}: {response.text}")


def main() -> None:
    metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    report_date = metadata["date"]
    pdf_url = metadata["pdf_url"]

    push(
        [
            {
                "type": "text",
                "text": f"{report_date} 台指期籌碼快訊\n原始 PDF：{pdf_url}",
            }
        ]
    )

    image_messages = []
    for item in metadata["images"]:
        original = raw_url(item["original"])
        preview = raw_url(item["preview"])
        wait_until_public(original)
        wait_until_public(preview)
        image_messages.append(
            {
                "type": "image",
                "originalContentUrl": original,
                "previewImageUrl": preview,
            }
        )

    for start in range(0, len(image_messages), 5):
        push(image_messages[start : start + 5])

    SENT_FILE.parent.mkdir(exist_ok=True)
    sent_dates = []
    if SENT_FILE.exists():
        sent_dates = SENT_FILE.read_text(encoding="utf-8").splitlines()
    if report_date not in sent_dates:
        sent_dates.append(report_date)
        SENT_FILE.write_text("\n".join(sent_dates) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
