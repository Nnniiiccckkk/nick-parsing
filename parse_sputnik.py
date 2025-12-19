#!/usr/bin/env python
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import requests

from bs4 import BeautifulSoup

DAYS_WEEKDAYS = {1, 2, 3, 4, 5}
DAYS_DAILY = {1, 2, 3, 4, 5, 6, 7}
DEFAULT_URL = "https://www.tutu.ru/station.php?nnst=45807"

FILTER_ALIASES = {
    "будни": "будни",
    "weekday": "будни",
    "weekdays": "будни",
    "workdays": "будни",
    "ежедневно": "ежедневно",
    "daily": "ежедневно",
    "everyday": "ежедневно",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Парсинг расписания электричек tutu.ru",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="URL страницы расписания (по умолчанию сайт tutu.ru)",
    )
    parser.add_argument(
        "--html",
        help="Путь к сохраненному HTML-файлу (если указан, URL не используется)",
    )
    parser.add_argument(
        "--days",
        "-d",
        help="Фильтр по дням: будни или ежедневно (доступны daily/weekdays)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Таймаут загрузки страницы в секундах",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Вывести результат в JSON (по умолчанию печать строк)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Путь для сохранения JSON (по умолчанию печать в stdout)",
    )
    return parser.parse_args()


def load_html(url: str, html_path: str | None, timeout: int) -> str:
    if html_path:
        return Path(html_path).read_text(encoding="utf-8")
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        curl_path = shutil.which("curl") or shutil.which("curl.exe")
        if not curl_path:
            raise OSError(str(exc)) from exc
        try:
            result = subprocess.run(
                [curl_path, "-L", url],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except subprocess.SubprocessError as curl_exc:
            raise OSError(str(exc)) from curl_exc
        if result.returncode != 0:
            error_text = result.stderr.strip() or f"curl exit {result.returncode}"
            raise OSError(f"{exc}; curl: {error_text}") from exc
        return result.stdout


def extract_timetable(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return []

    data = json.loads(script.string)
    page_props = data.get("props", {}).get("pageProps", {})
    values = page_props.get("values", {})

    # Next.js payload stores the schedule in values.*.timetable
    for value in values.values():
        if isinstance(value, dict) and "timetable" in value:
            return value.get("timetable") or []

    return []


def schedule_tag(schedule: list[int] | None) -> str:
    days = set(schedule or [])
    if days == DAYS_WEEKDAYS:
        return "будни"
    if days == DAYS_DAILY:
        return "ежедневно"
    return "другие"


def main() -> int:
    args = parse_args()
    try:
        html = load_html(args.url, args.html, args.timeout)
    except OSError as exc:
        print(f"Не удалось получить HTML: {exc}", file=sys.stderr)
        return 2

    timetable = extract_timetable(html)
    if not timetable:
        print("Не удалось найти расписание в HTML.", file=sys.stderr)
        return 1

    days_filter = None
    if args.days:
        days_filter = FILTER_ALIASES.get(args.days.strip().lower())
        if not days_filter:
            print("Неизвестный фильтр дней. Используйте: будни или ежедневно.", file=sys.stderr)
            return 2

    trips = []
    for item in timetable:
        route = item.get("train", {}).get("route", {})
        departure = route.get("departure", {}).get("name")
        arrival = route.get("arrival", {}).get("name")
        departure_time = item.get("departureDateTime")
        if not (departure and arrival and departure_time):
            continue
        if "T" not in departure_time:
            continue
        time_value = departure_time.split("T")[1][:5]
        tag = schedule_tag(item.get("schedule"))
        if days_filter and tag != days_filter:
            continue
        trips.append(
            {
                "departure_time": time_value,
                "route": f"{departure} -> {arrival}",
                "days": tag,
            }
        )

    if args.json or args.output:
        payload = json.dumps(trips, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(payload, encoding="utf-8")
        else:
            print(payload)
    else:
        for trip in trips:
            print(f"{trip['departure_time']} {trip['route']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
