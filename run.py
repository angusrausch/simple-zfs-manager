from dotenv import load_dotenv
from os import getenv

from app import create_app

app = create_app()

load_dotenv()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=getenv("PORT", "8080"))