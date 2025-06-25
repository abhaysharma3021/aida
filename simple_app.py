from flask import Flask, render_template, request, redirect, url_for, flash
import requests
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'dev-key-for-testing'

# Create data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def save_analysis(analysis_id, data):
    """Save analysis data to a JSON file"""
    filepath = os.path.join(DATA_DIR, f"{analysis_id}.json")
    with open(filepath, 'w') as f:
        json.dump(data, f)
    return analysis_id

def load_analysis(analysis_id):
    """Load analysis data from a JSON file"""
    filepath = os.path.join(DATA_DIR, f"{analysis_id}.json")
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return None

def generate_with_ollama(prompt, model_name="llama3.1"):
    """Generate text using Ollama API"""
    try:
        ollama_url = "http://localhost:11434/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        
        print(f"Sending request to Ollama for '{model_name}'...")
        response = requests.post(ollama_url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
        else:
            return f"Ollama API error: Status code {response.status_code}"
            
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/')
def index():
    return render_template('simple_form.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        # Get form data
        topic = request.form.get('topic', '')
        
        if not topic:
            flash('Please enter a topic')
            return redirect(url_for('index'))
        
        # Generate analysis
        prompt = f"Write a short paragraph about {topic}"
        result = generate_with_ollama(prompt)
        
        # Save result
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        analysis_id = f"test_{timestamp}"
        
        data = {
            'topic': topic,
            'result': result,
            'date': datetime.now().strftime("%B %d, %Y at %H:%M")
        }
        
        save_analysis(analysis_id, data)
        
        return redirect(url_for('results', analysis_id=analysis_id))
    
    except Exception as e:
        flash(f"Error: {str(e)}")
        return redirect(url_for('index'))

@app.route('/results/<analysis_id>')
def results(analysis_id):
    data = load_analysis(analysis_id)
    
    if not data:
        flash('Analysis not found')
        return redirect(url_for('index'))
    
    return render_template('simple_results.html', 
                          topic=data['topic'],
                          result=data['result'],
                          date=data['date'])

if __name__ == '__main__':
    app.run(debug=True)