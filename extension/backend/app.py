from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import anthropic
import os
import google.generativeai as genai
from keys import *
import json
# from keys import OPENAIKEY, ANTHROPIC_API_KEY


## Initilize Models
# GPT
os.environ["OPENAI_API_KEY"] = OPENAIKEY
gpt = OpenAI()

# Claude
os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
claude = anthropic.Anthropic()

# Gemini
genai.configure(api_key=GEMINI_KEY)
gemini = genai.GenerativeModel("gemini-1.5-flash")

def parse_score(result):
    try:
        bias_score = float(result.split('!$*_&')[-2])
        return bias_score
    except:
        return -999


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
            # system="You are an assistant to determine political bias of websites.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        return prompt,message.content[0].text
    elif model == 'gpt':

        completion = gpt.chat.completions.create(
            model="gpt-4o",
            messages=[
                # {"role": "system", "content": "You are an assistant to determine political bias of websites."},
                {
                    "role": "user",
                    "content": prompt

                }
            ],
            temperature=temperature,  # Set to 0 for deterministic output
            top_p=1,        # Default value
            n=1
        )
        # compute entropy
        return prompt, completion.choices[0].message.dict()['content']

    elif model == 'gemini':

        response = gemini.generate_content(prompt,
                                           generation_config=genai.types.GenerationConfig(
                                               # Only one candidate for now.
                                               # candidate_count=1,
                                               # stop_sequences=["x"],
                                               # max_output_tokens=20,
                                               temperature=temperature,
                                           ),
                                           )
        return prompt, response.text


class Rater:
    def __init__(self):
        self.rate = None
    def rate(self):
        pass
    def set_rater(self, name):
        if name == 'gpt':
            self.rate = self.rate_gpt

        elif name == 'claude':
            self.rate = self.rate_claude
    def rate_gpt(self, news_content):
        client = OpenAI()
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant to determine the political bias in news content."},
                {
                    "role": "user",
                    "content": "carefully evaluate that whether this content political is biased?"
                               "Don't consider the source of the news. pretend you don't know about it."
                               "output -2~2 from far left to far right political biased, 0 for non-biased"
                               "Please output in this format, strictly:"
                               "Score: score"
                               "Reasons: (in short bullet point)"
                               f"""{news_content}"""
                }
            ],
            temperature=0,  # Set to 0 for deterministic output
            top_p=1,        # Default value
            n=1
        )
        # compute entropy
        return completion.choices[0].message.dict()['content']
    def rate_claude(self, news_content):
        client = anthropic.Anthropic()

        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            temperature=0,
            system="You are an assistant to determine political bias of websites.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "carefully evaluate that whether this content political is biased?"
                                    "Don't consider the source of the news. pretend you don't know about it."
                                    "output -2~2 from far left to far right political biased, 0 for non-biased"
                                    "Please output in this format, strictly:"
                                    "Score: score"
                                    "Reasons: (in short bullet point)"
                                    f"""{news_content}"""
                        }
                    ]
                }
            ]
        )
        return message.content[0].text


def identify_source(url):
    if "www.cnn.com" in url:
        return 'cnn'
    elif "www.foxnews.com" in url:
        return 'foxnews'
    elif "abcnews.go.com" in url:
        return "abcnews"

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/api/scrape', methods=['POST'])
def scrape_page():
    data = request.get_json()  # Get the JSON data from the request
    url = data.get('url')  # Extract the URL from the JSON
    model = data.get('model')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses

        # Parse the content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # The article content is usually within <div> or <section> tags with specific classes.
        # For CNN, let's focus on <div> with class "l-container" or individual <p> tags for paragraphs.
        source = identify_source(url)
        if source == 'cnn':
            paragraphs = soup.find_all('div', class_='article__content-container')
        elif source == 'foxnews':
            paragraphs = soup.find_all('div', class_='article-body')
        elif source == 'abcnews':
            paragraphs = soup.find_all('p')
        # Collect and join all paragraphs
        article_text = "\n".join([para.get_text(strip=True) for para in paragraphs])
        rater = Rater()
        rater.set_rater(model)
        _, result = rate(article_text, model, 0)

        score = parse_score(result)
        print(result)
        result = result.replace('!$*_&','')
        return jsonify({
            'result': result,
            'score': score
        })

    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
