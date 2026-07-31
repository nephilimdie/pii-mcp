from dotenv import load_dotenv

from .http_app import create_http_app
from .settings import Settings

load_dotenv()
app = create_http_app(Settings.from_env(default_transport="streamable-http"))
