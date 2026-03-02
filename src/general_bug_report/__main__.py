from .app import create_app
from .settings import load_settings

app = create_app()

if __name__ == "__main__":
    settings = load_settings()
    app.run(host="0.0.0.0", port=settings.port, debug=False)
