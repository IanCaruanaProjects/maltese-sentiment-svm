from emoji import demojize
import malti.tokeniser
import requests
import time
from functools import lru_cache

# ==================
# Text Preprocessing
# ==================

import re
from emoji import demojize

def emoji_to_text(text):
    """
    Replaces emojis and common emoticons in a string with their text equivalents.
    Handles emoticons with repeated ending characters (e.g., :)))), :-)))), xDDDD).
    
    Args:
        text: The text containing emojis and emoticons to process
    """
    result = text

    # Replace emojis
    result = demojize(result)

    # Define emoticon patterns with regex
    emoticon_patterns = {
        # Happy/Positive
        r":\)+": ":smile:",
        r":-\)+": ":smile:",
        r":D+": ":big smile:",
        r":-D+": ":big smile:",
        r"=\)+": ":smile:",
        r"=D+": ":big smile:",
        r"<3+": ":heart:",
        r":\*+": ":kiss:",
        r":-\*+": ":kiss:",
        r";\)+": ":wink:",
        r";-\)+": ":wink:",
        r":P+": ":tongue:",
        r":-P+": ":tongue:",
        r":p+": ":tongue:",
        r"=P+": ":tongue:",
        r":-p+": ":tongue:",
        r"x[Dd]+": ":laughing:",
        r"X[Dd]+": ":laughing:",
        
        # Sad/Negative
        r":\(+": ":sad:",
        r":-\(+": ":sad:",
        r"D:+": ":sad:",
        r":/+": ":skeptical:",
        r":\\+": ":skeptical:",
        r":\|+": ":neutral:",
        r":-\|+": ":neutral:",
        r":O+": ":surprised:",
        r":o+": ":surprised:",
        r":'-\(+": ":crying:",
        r"-_-+": ":annoyed:",
    }
    
    # Replace each emoticon pattern with its text equivalent
    for pattern, replacement in emoticon_patterns.items():
        result = re.sub(pattern, replacement, result)
        
    return result

# ===============================
# Tokenisation & Token Processing
# ===============================

def tokenise(text):
    # Tokenises text into a list of tokens
    return malti.tokeniser.tokenise(text)


def clean_tokens(tokens):
    """
    Cleans and normalizes punctuation within a list of tokens.
    
    Args:
        tokens: The list of tokens to clean
    """
    result = []
    i = 0
    
    while i < len(tokens):
        # Skip empty tokens
        if not tokens[i]:
            i += 1
            continue

        # Handle three or more consecutive dots ('.', '.', '.' -> '...')
        if (i <= len(tokens) - 3 and 
            tokens[i] == '.' and 
            tokens[i+1] == '.' and 
            tokens[i+2] == '.'):
            result.append('...')
            while i < len(tokens) and tokens[i] == '.':
                i += 1
            continue
            
        # Handle emoji patterns (':', 'thumbs_up', ':' -> ':thumbs_up:')
        if (i <= len(tokens) - 3 and 
            tokens[i] == ':' and 
            tokens[i+2] == ':'):
            result.append(f":{tokens[i+1]}:")
            i += 3
            continue

        # Handle placeholder patterns ('[', 'NAME', ']' -> '[NAME]')
        if (i <= len(tokens) - 3 and 
            tokens[i] == '[' and 
            tokens[i+2] == ']'):
            result.append(f"[{tokens[i+1]}]")
            i += 3
            continue
        
        # Handle !? combination ('!', '?' -> '!?')
        if (i <= len(tokens) - 2 and 
            tokens[i] == '!' and 
            tokens[i+1] == '?'):
            result.append('!?')
            i += 2
            continue
            
        # Handle two or more consecutive exclamation marks ('!', '!' -> '!!')
        if (i <= len(tokens) - 2 and 
            tokens[i] == '!' and 
            tokens[i+1] == '!'):
            result.append('!!')
            while i < len(tokens) and tokens[i] == '!':
                i += 1
            continue
            
        # Handle two or more consecutive question marks ('?', '?' -> '??')
        if (i <= len(tokens) - 2 and 
            tokens[i] == '?' and 
            tokens[i+1] == '?'):
            result.append('??')
            while i < len(tokens) and tokens[i] == '?':
                i += 1
            continue

        # Remove '-' at end of tokens ('bil-' -> 'bil')
        # Helps model generalize since many articles in our dataset are written without hyphens
        # (e.g. "bil Malti" instead of "bil-Malti")
        if tokens[i].endswith('-'):
            tokens[i] = tokens[i][:-1]

        # Add any other token as is
        result.append(tokens[i])
        i += 1
        
    return result

def lowercase(tokens):
    """
    Converts all tokens to lowercase.
    
    Args:
        tokens: The list of tokens to convert to lowercase
    """
    return [token.lower() for token in tokens]

def selective_lowercase(tokens):
    """
    Converts tokens to lowercase, but keeps fully uppercase words unchanged.
    
    Args:
        tokens: The list of tokens to selectively convert to lowercase
    """
    return [token if token.isupper() else token.lower() for token in tokens]

def tokenise_with_pos_tag(text):
    """
    Tokenises and POS-tags a Maltese text using the MLRS API.
    
    Args:
        text: The text to tokenize and tag with parts of speech
    """
    url = "https://mlrs.research.um.edu.mt/tools/mlrsapi/tag"
    
    # Parameters for the GET request
    params = {
        'text': text
    }

    try:
        # Make the GET request
        response = requests.get(url, params=params)
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Get the JSON response and return the result
        json_response = response.json()
        return json_response['result']
        
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during POS tagging: {e}")
        return None
    
# =============
# Lemmatisation
# =============
    
@lru_cache(maxsize=512)
def make_request(url):
    """
    Helper function to make request with retry logic.
    
    Args:
        url: The URL to make the request to
    """
    DELAY = 3  # 3 second delay between requests
    MAX_RETRIES = 3  # Will try each request up to 3 times

    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                time.sleep(DELAY)  # Wait before making request after first attempt

            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt == MAX_RETRIES - 1:  # Last attempt
                print(f"Request failed after {MAX_RETRIES} attempts: {e}")
                print(f"URL: {url}")
                return None
            print(f"Request failed, retrying: {e}")

def normalize_word(word):
    """
    Takes an incorrectly written Maltese word (e.g., 'nohorgu') and uses Gabra's Search Suggest API
    to try to find its proper spelling equivalent ('noħorġu').
    
    Args:
        word: The word to normalize
    """
    # Skip empty words    
    if not word:
        return ""
    
    # Skip if word is too short
    if len(word) < 2:
        return word

    # Skip if word isn't alphanumeric
    if not word.isalnum():
        return word
        
    # Special case - avoid 'hemm' being converted to 'ħemm'
    if word == 'hemm':
        return word

    # Store original word case pattern
    is_upper = word.isupper()
    is_title = word.istitle()
    
    # Try searching wordforms first
    url = f"https://mlrs.research.um.edu.mt/resources/gabra-api/wordforms/search_suggest?s={word.lower()}"
    data = make_request(url)
    
    if data and data.get("results") and len(data["results"]) > 0:
        # Iterate through all wordform results
        for result in data["results"]:
            if "wordform" in result and "surface_form" in result["wordform"]:
                surface_form = result["wordform"]["surface_form"]
                
                # Apply original case pattern and return
                if is_upper:
                    return surface_form.upper()
                elif is_title:
                    return surface_form.title()
                return surface_form
    
    # If not found, try searching lexemes
    url = f"https://mlrs.research.um.edu.mt/resources/gabra-api/lexemes/search_suggest?s={word.lower()}"
    data = make_request(url)
    
    if data and data.get("results") and len(data["results"]) > 0:
        # Iterate through all lexeme results
        for result in data["results"]:
            if "lexeme" in result and "lemma" in result["lexeme"]:
                lemma = result["lexeme"]["lemma"]
                
                # Only use lemma if it's the same length as the input word
                if len(lemma) == len(word):
                    if is_upper:
                        return lemma.upper()
                    elif is_title:
                        return lemma.title()
                    return lemma
    
    # If no matches found, return original word
    return word

def get_lemma(word):
    """
    Retrieves the lemma (base form) of a given word using the Gabra API.
    
    Args:
        word: The word to lemmatize
    """
    # Skip empty words
    if not word:
        return ""

    # Skip if word is too short
    if len(word) < 2:
        return word

    # Skip if word isn't alphanumeric
    if not word.isalnum():
        return word

    # Store original word case pattern
    is_upper = word.isupper()
    is_title = word.istitle()
    
    url = f"https://mlrs.research.um.edu.mt/resources/gabra-api/lexemes/lemmatise?s={word.lower()}"
    data = make_request(url)

    # Check if results exist and are not empty
    if data and data.get("results") and len(data["results"]) > 0:
        # Iterate through all results
        for result in data["results"]:
            surface_form = result["wordform"]["surface_form"]
            
            # Check if surface form matches and lexeme/lemma exists
            if (word.lower() == surface_form and 
                "lexeme" in result and 
                "lemma" in result["lexeme"]):
                
                lemma = result["lexeme"]["lemma"]
                
                # Apply original case pattern to lemma
                if is_upper:
                    return lemma.upper()
                elif is_title:
                    return lemma.title()
                return lemma

    # No matching lemma found, return the original word
    return word