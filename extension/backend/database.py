from kafka import KafkaConsumer
import psycopg2
import json

# Kafka Consumer Configuration
consumer = KafkaConsumer(
    'processed_news_results',  # Kafka topic name
    bootstrap_servers=['localhost:9092'],
    group_id='news-bias-group',
    auto_offset_reset='earliest'
)

# Database Connection
def connect_to_db():
    return psycopg2.connect(
        host="localhost",
        database="news_bias_db",  # Replace with your database name
        user="your_user",          # Replace with your DB username
        password="your_password"   # Replace with your DB password
    )

# Function to Insert Data into DB
def insert_into_db(url, model, result, score):
    try:
        conn = connect_to_db()
        cursor = conn.cursor()

        insert_query = """
                       INSERT INTO news_bias_results (url, model, result, bias_score)
                       VALUES (%s, %s, %s, %s) \
                       """
        cursor.execute(insert_query, (url, model, result, score))

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error inserting into DB: {e}")

# Consuming messages and inserting into DB
for message in consumer:
    message_value = json.loads(message.value.decode('utf-8'))
    url = message_value['url']
    model = message_value['model']
    result = message_value['result']
    score = message_value['score']

    # Insert the message data into the database
    insert_into_db(url, model, result, score)
