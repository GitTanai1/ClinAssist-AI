from app.main import app as fastapi_app

# Keep an explicit ASGI app symbol in this file so Vercel's Python runtime
# can recognize api/index.py as the function entrypoint.
app = fastapi_app
