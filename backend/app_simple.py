import os
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({"message": "✅ Backend funcionando!", "status": "online"})

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy", "version": "1.0"})

@app.route('/api/test')
def test():
    return jsonify({"data": "Teste OK", "numbers": [1, 2, 3]})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)