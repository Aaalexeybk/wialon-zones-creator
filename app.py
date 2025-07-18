from flask import Flask, request, jsonify, render_template
import json
import requests
import csv
import os

app = Flask(__name__)

# Инициализация переменных (значения по умолчанию)
DEFAULT_HOST = 'https://wialon.rtmglonass.ru'
DEFAULT_TOKEN = '962bb8cf3e1406d061c9a66be125d1b13E036E5AD55E88FDA9EA43DCA6F4C692ED5B95C6'
DEFAULT_ITEM_ID = 12050


def login_to_wialon(host, token):
    """Аутентификация в Wialon"""
    response = requests.post(f'{host}/wialon/ajax.html', params={
        'svc': 'token/login',
        'params': json.dumps({
            'token': token
        })
    })
    jsonData = response.json()
    return jsonData['eid']


def read_zones_from_csv(file_path):
    """Чтение зон из CSV файла"""
    zones = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            headers = next(csv_reader)  # Пропускаем заголовки

            for row in csv_reader:
                if len(row) >= 3:  # Проверяем, что в строке достаточно данных
                    zones.append({
                        'Name': row[0],
                        'Lat': float(row[1]),
                        'Long': float(row[2])
                    })
    except Exception as e:
        print(f"Ошибка при чтении CSV: {e}")
    return zones


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html',
                           default_host=DEFAULT_HOST,
                           default_token=DEFAULT_TOKEN,
                           default_item_id=DEFAULT_ITEM_ID)


@app.route('/upload', methods=['POST'])
def upload_file():
    """Загрузка CSV файла"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.endswith('.csv'):
        # Сохраняем файл временно
        file_path = os.path.join('uploads', file.filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(file_path)

        # Читаем зоны из файла
        zones = read_zones_from_csv(file_path)

        # Удаляем временный файл
        os.remove(file_path)

        return jsonify({'zones': zones, 'count': len(zones)})

    return jsonify({'error': 'Invalid file type'}), 400


@app.route('/create_zones', methods=['POST'])
def create_zones():
    """Создание зон в Wialon"""
    data = request.json
    required_fields = ['zones', 'itemId', 'host', 'token']

    if not all(field in data for field in required_fields):
        return jsonify({'error': f'Missing required data: {required_fields}'}), 400

    zones = data['zones']
    item_id = data['itemId']
    host = data['host']
    token = data['token']
    results = []

    # Аутентификация
    try:
        sid = login_to_wialon(host, token)
    except Exception as e:
        return jsonify({'error': f'Authentication failed: {str(e)}'}), 500

    # Создание зон
    for zone in zones:
        try:
            response = requests.post(f'{host}/wialon/ajax.html', params={
                'svc': 'resource/update_zone',
                'sid': sid,
                'params': json.dumps({
                    "itemId": item_id,
                    "id": 0,
                    "callMode": "create",
                    "n": zone['Name'],
                    "d": "рамка",
                    "t": 3,
                    "w": 2000,
                    "f": 112,
                    "c": 2568583984,
                    "tc": 16733440,
                    "ts": 12,
                    "min": 0,
                    "max": 18,
                    "path": "",
                    "libId": "",
                    "p": [{
                        "x": zone['Lat'],
                        "y": zone['Long'],
                        "r": 2000
                    }]
                })
            })
            results.append({
                'name': zone['Name'],
                'status': 'success' if response.status_code == 200 else 'failed',
                'response': response.json()
            })
        except Exception as e:
            results.append({
                'name': zone['Name'],
                'status': 'error',
                'message': str(e)
            })

    return jsonify({'results': results})


if __name__ == '__main__':
    app.run(debug=True)