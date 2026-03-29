import logging
from params import BASE_DIR,Path

LOG_PATH = BASE_DIR / "logs"
LOG_DIR = Path(LOG_PATH)
LOG_DIR.mkdir(exist_ok=True)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cybercafe Server")