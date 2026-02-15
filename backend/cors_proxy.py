"""
Simple CORS Proxy Server
Forwards requests from frontend to backend with proper CORS headers
Run this instead of accessing backend directly
"""
from flask import Flask, request, jsonify, Response
import requests
import json

app = Flask(__name__)

# Configure logging
import logging
logging.basicConfig(filename='proxy_debug.log', level=logging.DEBUG, format='%(asctime)s %(message)s')

BACKEND_URL = "http://127.0.0.1:8000"

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'])
def proxy(path):
    logging.info(f"Proxy request: {request.method} {path}")
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
        response.headers['Access-Control-Allow-Headers'] = '*'
        response.headers['Access-Control-Max-Age'] = '3600'
        return response
    
    # Forward the request to backend
    url = f'{BACKEND_URL}/{path}'
    
    # Get query parameters
    params = request.args.to_dict()
    
    # Get headers (exclude host)
    headers = {key: value for (key, value) in request.headers if key.lower() != 'host'}
    
    # Get request body
    if request.method in ['POST', 'PUT', 'PATCH']:
        if request.is_json:
            data = request.get_json()
        elif request.form:
            data = request.form.to_dict()
        else:
            data = request.get_data()
    else:
        data = None
    
    # Make request to backend
    try:
        if request.method == 'GET':
            backend_response = requests.get(url, params=params, headers=headers)
        elif request.method == 'POST':
            if request.is_json:
                backend_response = requests.post(url, json=data, params=params, headers=headers)
            elif request.form:
                backend_response = requests.post(url, data=data, params=params, headers=headers)
            else:
                backend_response = requests.post(url, data=data, params=params, headers=headers)
        elif request.method == 'PUT':
            backend_response = requests.put(url, json=data, params=params, headers=headers)
        elif request.method == 'DELETE':
            backend_response = requests.delete(url, params=params, headers=headers)
        elif request.method == 'PATCH':
            backend_response = requests.patch(url, json=data, params=params, headers=headers)
        else:
            return jsonify({"error": "Method not allowed"}), 405
        
        # Create response
        try:
            response_data = backend_response.json()
            response = jsonify(response_data)
        except:
            response = Response(backend_response.content, mimetype=backend_response.headers.get('content-type', 'text/plain'))
        
        response.status_code = backend_response.status_code
        
        # Add CORS headers
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
        response.headers['Access-Control-Allow-Headers'] = '*'
        
        return response
        
    except Exception as e:
        print(f"Error proxying request: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("CORS Proxy Server Starting")
    print("=" * 60)
    print(f"Backend: {BACKEND_URL}")
    print(f"Proxy: http://localhost:8001")
    print("=" * 60)
    print("\nUpdate frontend to use: http://localhost:8001")
    print("   (Change API_BASE_URL in signup.html, login.html, etc.)\n")
    app.run(port=8001, debug=True)
