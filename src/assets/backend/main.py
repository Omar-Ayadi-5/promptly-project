"""Development and WSGI entry point for the modular Flask backend."""
from app import create_app

app = create_app()


if __name__ == '__main__':
    app.run(debug=True, port=5000)
