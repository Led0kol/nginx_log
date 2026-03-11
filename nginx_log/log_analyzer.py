import re
import statistics
from collections import defaultdict
from datetime import datetime


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '  
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}
# config = {}

# Регулярное выражение для разбора строки лога
LOG_PATTERN = re.compile(
    r'(?P<ip>\S+)\s+'  # IP
    r'(?P<user>\S+)\s+'  # user (обычно '-')
    r'(?P<pass>\S+)\s+'  # pass (обычно '-')
    r'\[(?P<timestamp>[^\]]+\s+[^\]]+)\]\s+'  # timestamp
    r'"(?P<request>[^"]+)"\s+'  # request
    r'(?P<status>\d+)\s+'  # status
    r'(?P<size>\d+)\s+'  # size
    r'"(?P<referer>[^"]*)"\s+'  # referer
    r'"(?P<user_agent>[^"]*)"\s+'  # user_agent
    r'"(?P<http_x_forwarded_for>[^"]*)"\s+'  # http_x_forwarded_for (второй дефис)
    r'"(?P<request_id>[^"]*)"\s+'  # request_id (1498697422-2190034393-4708-9752759)
    r'"(?P<uid>[^"]*)"\s+'  # uid (dc7161be3)
    r'(?P<request_time>[\d\.]+)'  # request_time
)


def parse_log_line(line):
    """Разбирает строку лога. Возвращает словарь или None."""
    match = LOG_PATTERN.match(line.strip())
    if not match:
        return None
    data = match.groupdict()
    try:
        data['request_time'] = float(data['request_time'])
    except (ValueError, TypeError):
        data['request_time'] = 0.0
    return data

def analyze_log(log_path):
    """Анализирует лог и собирает метрики по URL."""
    url_data = defaultdict(list)  # {url: [time1, time2, ...]}
    total_requests = 0
    total_time = 0.0

    with open(log_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            data = parse_log_line(line)
            if not data:
                print(f"Предупреждение: не удалось разобрать строку {line_num}: {line!r}")
                continue

            # Извлекаем URL (второй элемент в поле request)
            request_parts = data['request'].split()
            if len(request_parts) >= 2:
                url = request_parts[1]
            else:
                url = "-"

            url_data[url].append(data['request_time'])
            total_requests += 1
            total_time += data['request_time']

    # Формируем отчёт
    report = []
    for url, times in url_data.items():
        count = len(times)
        count_perc = (count / total_requests) * 100
        time_sum = sum(times)
        time_perc = (time_sum / total_time) * 100 if total_time > 0 else 0
        time_avg = statistics.mean(times)
        time_max = max(times)
        time_med = statistics.median(times)

        report.append({
            'url': url,
            'count': count,
            'count_perc': round(count_perc, 2),
            'time_sum': round(time_sum, 3),
            'time_perc': round(time_perc, 2),
            'time_avg': round(time_avg, 3),
            'time_max': round(time_max, 3),
            'time_med': round(time_med, 3)
        })

    # Сортируем по count (убывание)
    report.sort(key=lambda x: x['count'], reverse=True)
    return report[:config.get("REPORT_SIZE", 1000)], len(report), total_requests, total_time


def generate_html_report(report, total_requests, total_time, output_path):
    """Создаёт HTML‑отчёт."""
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Отчёт по логу Nginx</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .summary {{ margin-bottom: 20px; }}
        .footer {{ margin-top: 30px; color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>Отчёт по анализу лога Nginx</h1>
    <div class="summary">
        <p><strong>Дата анализа:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Всего запросов:</strong> {total_requests}</p>
        <p><strong>Общее время обработки:</strong> {round(total_time, 3)} с</p>
    </div>
    <table>
        <thead>
            <tr>
                <th>URL</th>
                <th>Count</th>
                <th>Count (%)</th>
                <th>Time Sum (с)</th>
                <th>Time (%)</th>
                <th>Time Avg (с)</th>
                <th>Time Max (с)</th>
                <th>Time Med (с)</th>
            </tr>
        </thead>
        <tbody>
"""

    for row in report:
        html += f"""            <tr>
                <td>{row['url']}</td>
                <td>{row['count']}</td>
                <td>{row['count_perc']}</td>
                <td>{row['time_sum']}</td>
                <td>{row['time_perc']}</td>
                <td>{row['time_avg']}</td>
                <td>{row['time_max']}</td>
                <td>{row['time_med']}</td>
            </tr>
"""

    html += """        </tbody>
    </table>
    <div class="footer">
        <p>Отчёт сформирован автоматически.</p>
    </div>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)


def main():

    log_path = config.get("LOG_DIR", "../data/nginx-access-ui.log-20170630")
    output_path = config.get("REPORT_DIR", "../reports/eug_report.html")

    print(f"Анализирую лог: {log_path}...")
    report, find_url_count, total_requests, total_time = analyze_log(log_path)
    print(f"!Найдено URL: {find_url_count}, всего запросов: {total_requests}")

    print(f"Составляю HTML‑отчёт: {output_path}...")
    generate_html_report(report, total_requests, total_time, output_path)
    print("Готово!")

if __name__ == "__main__":
    main()
