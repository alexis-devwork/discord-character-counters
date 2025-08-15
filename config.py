import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
MAX_USER_CHARACTERS = int(os.getenv("MAX_USER_CHARACTERS"))
MAX_COUNTERS_PER_CHARACTER = int(os.getenv("MAX_COUNTERS_PER_CHARACTER"))
MAX_FIELD_LENGTH = int(os.getenv("MAX_FIELD_LENGTH"))
MAX_COMMENT_LENGTH = int(os.getenv("MAX_COMMENT_LENGTH"))
