import mangum
from app.main import app

# This handler wraps the FastAPI app, making it compatible with Netlify's
# AWS Lambda-based function environment.
handler = mangum.Mangum(app)