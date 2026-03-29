import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


DATABASEPATH=Path(BASE_DIR / "data")
DATABASEPATH.mkdir(exist_ok=True)
DATABASEURL=os.getenv("DATABASE_URL",default=f"sqlite:///{DATABASEPATH}/cybercafe.db")


JWT_SECRET=os.getenv("JWT_SECRET", "12c772d5f202e6e965733a956e0a32f5c12c3d500452844cb63d50c1aa478090")
ALGORITHM = "HS256"

HDFS_WEBHDFS_URL = os.getenv("HDFS_WEBHDFS_URL", "http://hdfs-namenode:9870/webhdfs/v1")
AIRFLOW_BASE_URL = os.getenv("AIRFLOW_BASE_URL", "http://airflow-webserver:8080")
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")