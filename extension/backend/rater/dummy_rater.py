from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StringType, StructType, StructField
import json
from kafka import KafkaProducer

# 🔹 Kafka Configuration (Ensure Kafka is in KRaft Mode)
KAFKA_BROKER = "localhost:9092"
TOPIC_NAME = "news_articles"
OUTPUT_TOPIC = "processed_news_results"  # New topic for the processed results

# 🔹 Initialize Spark Session
spark = SparkSession.builder \
    .appName("NewsBiasProcessing") \
    .config("spark.sql.streaming.schemaInference", "true") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.1").getOrCreate()  # Use the correct version for your setup

# 🔹 Initialize Kafka Producer
producer = KafkaProducer(bootstrap_servers=KAFKA_BROKER, value_serializer=lambda v: json.dumps(v).encode('utf-8'))

# 🔹 Define Schema for Incoming Kafka Data
schema = StructType([
    StructField("content", StringType(), True),
    StructField("model", StringType(), True),
    StructField("url", StringType(), True)
])

# 🔹 Function to Extract Bias Score
def parse_score(result):
    try:
        return float(result.split("!$*_&")[-2])
    except Exception:
        return -999  # Return a default invalid score

# 🔹 Function to Rate News Content Using AI Models
def rate(news_content, model, temperature=0):
    prompt = f"""
    You are an AI trained to evaluate political bias in news articles. 
    
    Please analyze the news content below and give a political bias score based on the content only.

    1. Explanation: Explain the reasoning in bullet points.
    2. Bias Score: Provide a score between -2 and 2:
       - -2 = Far-left bias
       - 2 = Far-right bias
       - 0 = Neutral
       Wrap the score with !$*_& like this: !$*_&score!$*_&

    Here is the news content:
    \"\"\"{news_content}\"\"\"
    """

    return prompt, "dummy working"

# 🔹 Function to Process Each Article (Updated for Spark)
def process_article(batch_df, batch_id):
    for row in batch_df.collect():
        news_content = row["content"]
        model = row["model"]
        url = row["url"]

        if news_content and model:
            _, result = rate(news_content, model)
            score = parse_score(result)
            print(f"\n📰 Processed Article: {url}\n🔹 Bias Score: {score}\n")

            # Prepare the result to send to Kafka
            result_data = {
                "url": url,
                "model": model,
                "result": result,
                "score": score
            }

            # Send the processed result to the Kafka topic
            producer.send(OUTPUT_TOPIC, value=result_data)
            print(f"📤 Sent result to Kafka topic: {OUTPUT_TOPIC}")

# Kafka Configuration for Reading Input
kafka_options = {
    "kafka.bootstrap.servers": KAFKA_BROKER,  # Replace with your Kafka broker
    "subscribe": TOPIC_NAME,               # Replace with your Kafka topic
    "startingOffsets": "earliest",           # Optionally define how to start consuming messages,
    "group_id":'article_processing'

}

# Read Streaming Data from Kafka
df = spark.readStream \
    .format("kafka") \
    .options(**kafka_options) \
    .load()

# Parse the Kafka data and apply schema
parsed_df = df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*")

# Use foreachBatch to process each batch of incoming data
query = parsed_df.writeStream \
    .foreachBatch(process_article) \
    .start()

# Await termination
query.awaitTermination()
