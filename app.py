import json
from pathlib import Path
from flask import Flask, jsonify, request, render_template
import logging

app = Flask(__name__)
DATA_FILE = Path(__file__).with_name('data.json')
logging.basicConfig(level=logging.INFO)


def load_data():
    if DATA_FILE.exists():
        with DATA_FILE.open() as f:
            return json.load(f)
    return {}


def save_data(data):
    with DATA_FILE.open('w') as f:
        json.dump(data, f, indent=2)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data')
def get_data():
    return jsonify(load_data())


@app.post('/api/add_category')
def add_category():
    payload = request.get_json(force=True)
    name = payload.get('name')
    if not name:
        return jsonify({'error': 'Category name required'}), 400
    data = load_data()
    if name in data:
        return jsonify({'error': 'Category exists'}), 400
    data[name] = []
    save_data(data)
    return jsonify({'status': 'ok'})


@app.post('/api/delete_category')
def delete_category():
    payload = request.get_json(force=True)
    name = payload.get('name')
    data = load_data()
    if name not in data:
        return jsonify({'error': 'Category not found'}), 404
    del data[name]
    save_data(data)
    return jsonify({'status': 'ok'})


@app.post('/api/add_item')
def add_item():
    payload = request.get_json(force=True)
    category = payload.get('category')
    name = payload.get('name')
    url = payload.get('url')
    if not all([category, name, url]):
        return jsonify({'error': 'category, name and url required'}), 400
    data = load_data()
    data.setdefault(category, [])
    data[category].append({'name': name, 'url': url})
    save_data(data)
    return jsonify({'status': 'ok'})


@app.post('/api/delete_item')
def delete_item():
    payload = request.get_json(force=True)
    category = payload.get('category')
    name = payload.get('name')
    data = load_data()
    if category not in data:
        return jsonify({'error': 'Category not found'}), 404
    items = data[category]
    data[category] = [i for i in items if i.get('name') != name]
    save_data(data)
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=True)
