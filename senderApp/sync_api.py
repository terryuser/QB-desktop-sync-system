from flask import Flask
from api_routes.customer_routes import customer_bp

app = Flask(__name__)

# Register the customer blueprint with a URL prefix
app.register_blueprint(customer_bp, url_prefix='/customer')

@app.route('/')
def index():
    return "Sync API is running. Use the /customer endpoint to sync customers."

if __name__ == '__main__':
    # For development, the built-in server is fine.
    # For production, use a proper WSGI server like Gunicorn or Waitress.
    app.run(host='0.0.0.0', port=5000, debug=True)