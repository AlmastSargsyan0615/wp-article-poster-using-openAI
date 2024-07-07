import json
import csv
import logging
import requests
import base64
from datetime import datetime
import openai

USER_JSON_PATH = 'user.json'
KEYWORDS_CSV_PATH = 'keywords.csv'
logging.basicConfig(filename='logfile.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: The file {file_path} was not found.")
    except json.JSONDecodeError as e:
        logging.error(f"Error: JSON decoding error in {file_path} - {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading config: {e}")
    return {}

# Load user credentials
config = load_config(USER_JSON_PATH)
hostname = config.get('hostname', '')
username = config.get('username', '')
userpassword = config.get('userpassword', '')
category_id = config.get('category_id', '')
tag_id = config.get('tag_id', '')
product_tag_id = config.get('new-product_tag', '')
openai_key = config.get('openai-key', '')

openai.api_key = openai_key

def read_keywords_from_csv(file_path):
    keywords = []
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8-sig') as file:  # Using utf-8-sig to handle BOM (Byte Order Mark)
            csv_reader = csv.reader(file)
            for row in csv_reader:
                for keyword in row:
                    keyword = keyword.strip()
                    if keyword:  # Ensure keyword is not empty after stripping
                        keywords.append(keyword)
    except FileNotFoundError:
        logging.error(f"Error: The file {file_path} was not found.")
    except PermissionError:
        logging.error(f"Error: Permission denied for file {file_path}.")
    except csv.Error as e:
        logging.error(f"Error: CSV read error occurred - {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while reading CSV: {e}")
    
    logging.info("\nFinal array of keywords: %s", keywords)
    return keywords

def get_article_topics(product_name):
    try:
        prompt = f"Write a detailed article in casual funny tone for keyword - {product_name}"
        prompt_additional = f'''Please give me only article.Please don't include another your explaination for this answer.
        And please add the below hyperlink ,strong, underline to only all {product_name} in article content only.
        Hyperlink is 'https://regencyshop.com/product-tag/chesterfield-sofa'.
        
        '''
        prompt = prompt + prompt_additional
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        suggested_article = completion.choices[0].message['content']
        return suggested_article.replace("Title: ", "")
    except Exception as e:
        logging.error(f"An error occurred while generating article for {product_name}: {e}")
        return ""

def create_wordpress_post(site_url, username, userpassword, title, content, category_id, tag_id, product_tag_id):
    try:
        url = f"https://{site_url}/wp-json/wp/v2/posts"
        credentials = f"{username}:{userpassword}"
        token = base64.b64encode(credentials.encode())
        headers = {'Authorization': 'Basic ' + token.decode('utf-8')}
        
        current_date = datetime.now().isoformat()
        
        post = {
            'title': title,
            'status': 'publish',
            'content': content,
            'categories': category_id,
            'tags': tag_id,
            'date': current_date
        }
        
        # Print post data for debugging purposes
        print(f"Post Data for '{title}': {post}")
        
        response = requests.post(url, headers=headers, json=post)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while posting to WordPress: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while posting to WordPress: {e}")
        return None

# Main script
keywords_array = read_keywords_from_csv(KEYWORDS_CSV_PATH)

# Process each keyword
cnt = 0
for keyword in keywords_array:
    cnt = cnt + 1
    print(f"Processing keyword: {cnt} / {len(keywords_array)} - {keyword}")
    content = get_article_topics(keyword)
    if content:
        response = create_wordpress_post(hostname, username, userpassword, keyword, content, category_id, tag_id, product_tag_id)
        if response:
            logging.info(f"Successfully posted '{keyword}' to WordPress with status code {response.status_code}")
        else:
            logging.error(f"Failed to post '{keyword}' to WordPress")
    else:
        logging.warning(f"Failed to generate content for keyword '{keyword}'")
