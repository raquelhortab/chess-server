import os

from app import create_app

app, socketio = create_app(os.getenv('FLASK_CONFIG') or 'default')

if __name__  == "__main__":
    socketio.run(app)
