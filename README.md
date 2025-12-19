# Парсер расписания электричек (tutu.ru)

Скрипт извлекает время отправления и маршрут в формате "Откуда -> Куда". По умолчанию HTML скачивается с сайта, при желании можно парсить сохраненный файл. Есть фильтрация по типу дней: **будни** и **ежедневно**.

## Откуда берется HTML
Можно заранее сохранить HTML-страницу расписания локально и парсить файл. Например:

```bash
curl -L "https://www.tutu.ru/station.php?nnst=45807" -o tutu_station.html
```

Также можно сохранить страницу через браузер (Файл - Сохранить страницу как...).

## Установка зависимостей

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Запуск

```bash
python parse_sputnik.py
```

Фильтрация по дням:

```bash
python parse_sputnik.py --days будни
python parse_sputnik.py --days ежедневно
```

Вывод в JSON:

```bash
python parse_sputnik.py --json
python parse_sputnik.py --json --output result.json
```

Парсинг локального файла:

```bash
python parse_sputnik.py --html tutu_station.html
python parse_sputnik.py --html tutu_station.html --days будни
```

Другой URL:

```bash
python parse_sputnik.py --url "https://www.tutu.ru/station.php?nnst=45807"
```

Если загрузка по сети тормозит, можно увеличить таймаут:

```bash
python parse_sputnik.py --timeout 40
```

### Пример вывода

```
06:12 Москва Ярославская -> Сергиев Посад
06:18 Москва Ярославская -> Монино
```

## Что извлекается
- время отправления;
- маршрут в формате "Откуда -> Куда";
- тип дней для фильтрации (будни/ежедневно).

## Алгоритм поиска
1. Скачивает HTML по URL (или читает локальный файл, если указан `--html`).
2. Находит в HTML скрипт `__NEXT_DATA__` с JSON-данными страницы.
3. Из JSON берет блок `props.pageProps.values.*.timetable`, где лежат рейсы.
4. Для каждого рейса извлекает `departureDateTime`, `train.route.departure.name`,
   `train.route.arrival.name` и список дней `schedule`.
5. Определяет тип дней по `schedule` и при необходимости фильтрует.

## Как работает код
- `load_html` получает HTML: из сети (через `urlopen`) или из файла.
- `extract_timetable` парсит HTML через BeautifulSoup, читает `__NEXT_DATA__`
  и возвращает список рейсов `timetable`.
- В `main` из каждого рейса формируется словарь с:
  `departure_time`, `route`, `days`.
- Фильтр `--days` оставляет только "будни" или "ежедневно".
- Результат выводится построчно или в JSON (если указан `--json`/`--output`).
