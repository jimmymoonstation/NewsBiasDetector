import functions_framework
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
import anthropic
import openai
import google.generativeai as genai
import os
import requests
from openai import OpenAI

# Initialize APIs with environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gpt = OpenAI()
claude = anthropic.Anthropic()
genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel("gemini-1.5-flash")

# Helper function: Parse bias score from response
def parse_score(result):
    try:
        return float(result.split("!$*_&")[-2])
    except:
        return -999  # Return a default error score

# Helper function: Rate the content with different models
def rate(news_content, model, temperature):
    prompt = f"""
    You are an AI trained to evaluate political bias in news articles. 

    Please analyze the news content below and give a political bias score based on the content. Do not consider the source or any other context, only the content itself.

    1. Explanation: explain the reasoning in bullet points. Be objective, and logical in your explanation.

    2. Bias Score: Based on the explanation, provide a score between -2 and 2:
       - -2 = Far-left bias
       - 2 = Far-right bias
       - 0 = Neutral (no bias)
       Please wrap the score between !$*_& sign like this !$*_&score!$*_&

    Here is the news content:
    \"\"\"{news_content}\"\"\"

    Please evaluate the content and output only the score following the reasons. Do not use any formatting like **.
    """
    if model == 'claude':
        message = claude.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            temperature=temperature,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        )
        return prompt, message.content[0].text
    elif model == 'gpt':
        completion = gpt.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            top_p=1,
            n=1
        )
        return prompt, completion.choices[0].message.dict()['content']
    elif model == 'gemini':
        response = gemini.generate_content(prompt,
                                           generation_config=genai.types.GenerationConfig(
                                               temperature=temperature,
                                           ))
        return prompt, response.text

# Helper function: Identify the news source from the URL
def identify_source(url):
    if "cnn.com" in url:
        return "cnn"
    elif "foxnews.com" in url:
        return "foxnews"
    elif "abcnews.go.com" in url:
        return "abcnews"
    return "unknown"

# Cloud Function entry point
@functions_framework.http
def scrape_page(request):
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        response = jsonify({"message": "CORS preflight check successful"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        return response

    # Handle POST requests
    if request.method == 'POST':
        data = request.get_json()
        if not data or "url" not in data:
            response = jsonify({"error": "No URL provided"})
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response, 400

        url = data["url"]
        model = data.get("model", "gpt")  # Default to GPT model if not specified
        temperature = data.get("temperature", 0)  # Default to 0 if not specified

        try:
            # Fetch the web page content
            response = requests.get(url)
            response.raise_for_status()

            # Parse the web page using BeautifulSoup
            soup = BeautifulSoup(response.content, "html.parser")
            source = identify_source(url)

            # Extract article text based on source
            if source == "cnn":
                paragraphs = soup.find_all("div", class_="article__content-container")
            elif source == "foxnews":
                paragraphs = soup.find_all("div", class_="article-body")
            elif source == "abcnews":
                paragraphs = soup.find_all("p")
            else:
                paragraphs = soup.find_all("p")  # Fallback for unknown sources

            article_text = "\n".join([para.get_text(strip=True) for para in paragraphs])

            # Evaluate the article text
            _, result = rate(article_text, model, temperature)
            score = parse_score(result)

            # Remove custom bias score markers from the result
            cleaned_result = result.replace("!$*_&", "")

            response = jsonify({
                "source": source,
                "result": cleaned_result,
                "score": score
            })
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response

        except requests.RequestException as e:
            response = jsonify({"error": f"Failed to fetch URL: {str(e)}"})
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response, 500
        except Exception as e:
            response = jsonify({"error": str(e)})
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response, 500
    else:
        response = jsonify({"error": "Invalid method"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 405
