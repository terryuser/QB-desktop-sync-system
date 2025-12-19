from fastapi import FastAPI
from api_routes.customer_routes import router as customer_router
from api_routes.order_routes import router as order_router
import uvicorn

app = FastAPI(title="Sender App Sync API")

# Register the customer router with a URL prefix
app.include_router(customer_router, prefix='/customer', tags=["customer"])

# Register the order router with a URL prefix
app.include_router(order_router, prefix='/order', tags=["order"])

@app.get('/')
def index():
    return "Sync API is running. Test 123"

@app.get('/health')
def health():
    return "APIs working fine."

if __name__ == '__main__':
    # For development, run uvicorn programmatically
    uvicorn.run(app, host='0.0.0.0', port=5000)