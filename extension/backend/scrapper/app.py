from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
from kafka import KafkaProducer

KAFKA_BROKER = 'localhost:9092'
TOPIC_NAME = 'news_articles'

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# 🔹 Flask App Setup
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# 🔹 Identify News Source
def identify_source(url):
    if "cnn.com" in url:
        return 'cnn'
    elif "foxnews.com" in url:
        return 'foxnews'
    elif "abcnews.go.com" in url:
        return "abcnews"
    else:
        return "unknown"

# 🔹 Extract Article Text Based on Source
def extract_article_text(soup, source):
    if source == 'cnn':
        paragraphs = soup.find_all('div', class_='article__content-container')
    elif source == 'foxnews':
        paragraphs = soup.find_all('div', class_='article-body')
    elif source == 'abcnews':
        paragraphs = soup.find_all('p')
    else:
        paragraphs = soup.find_all('p')  # Fallback for unknown sources

    return "\n".join([para.get_text(strip=True) for para in paragraphs if para.get_text(strip=True)])

# 🔹 Route for Scraping News Articles
@app.route('/api/scrape', methods=['POST'])
def scrape_page():
    data = request.get_json()
    url = data.get('url')
    model = data.get('model', 'gpt')  # Default to GPT if no model is specified

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        source = identify_source(url)
        article_text = extract_article_text(soup, source)

        if not article_text.strip():
            return jsonify({'error': 'No content extracted from the article'}), 400

        # Publish to Kafka for processing
        producer.send(TOPIC_NAME, {'url': url, 'content': article_text, 'model': model})
        return jsonify({'message': 'Article sent for processing', 'source': source}), 202

    except requests.Timeout:
        return jsonify({'error': 'Request timed out'}), 504
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

# 🔹 Run Flask App
if __name__ == '__main__':
    app.run(port=5000, debug=True)
