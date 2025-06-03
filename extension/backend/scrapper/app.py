import time
import datetime
import redis
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
from kafka import KafkaProducer
import psycopg2


KAFKA_BROKER = 'localhost:9092'
TOPIC_NAME = 'scraped_news_articles'
REDIS_HOST = 'localhost'
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

def fetch_from_SQL(url):
    # conn = psycopg2.connect(
    #     dbname="your_db_name",    # Replace with your database name
    #     user="your_username",     # Replace with your PostgreSQL username (often "postgres")
    #     password="your_password", # Replace with your PostgreSQL password
    #     host="localhost",         # Localhost
    #     port="5432"               # Default PostgreSQL port
    # )
    #
    # cur = conn.cursor()
    # cur.execute("SELECT current_date;")
    # print(cur.fetchone())
    #
    # cur.close()
    # conn.close()
    return False, True



# 🔹 Route for Scraping News Articles
@app.route('/api/click', methods=['POST'])
def scrape_page():

    data = request.get_json()
    url = data.get('url')
    model = data.get('model', 'gpt')  # Default to GPT if no model is specified
    # model = 'dummy'  # use dummy for testing



    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
        # Step 1. Try to fetch from cache
        result = r.hgetall(url)
        if len(result) == 0:
            fetched, result = fetch_from_SQL(url)
            if fetched: # Found in SQL
                return jsonify({'result': '444'}), 202

            else: # Initiate new scraping and rating
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                source = identify_source(url)
                article_text = extract_article_text(soup, source)

                if not article_text.strip():
                    return jsonify({'error': 'No content extracted from the article'}), 400

                # Publish to Kafka for processing
                producer.send(TOPIC_NAME, {'url': url, 'content': article_text, 'model': model})
                status = {
                    'status': 'sent',
                    'topic': TOPIC_NAME,
                    'time': str(datetime.datetime.now()),
                    'result': '',
                    'score': ''
                }
                r.hset(url, mapping = status)

                # yield jsonify({'result': 'Article sent for processing', 'source': source}), 202
        retry_times = 0
        while retry_times <= 3:
            result = r.hgetall(url)
            print(result)
            if result.get('status') == 'rated':
                return jsonify({'result': result.get('result'), 'score': result.get('score')}), 202
            print('retrying', retry_times)
            time.sleep(3)
            retry_times += 1
        else:
            return jsonify({'result': 'Error Processing'}), 400
        return jsonify({'result': 'Error Processing'}), 400

        # while retry_times <= 3:
        #     result = r.hgetall(url)
        #     if result.get('status', 'None') not in ['sent', 'rating']:
        #         break
        #     time.sleep(3)
        #     retry_times += 1
        # if r.get(url) == 'rating':
        #     return jsonify({'error': 'Content rating timeout'}), 400


    except requests.Timeout:
        return jsonify({'error': 'Request timed out'}), 504
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

# 🔹 Run Flask App
if __name__ == '__main__':
    app.run(port=5000, debug=True)
