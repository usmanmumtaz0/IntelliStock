"""
CV Pipeline Configuration
"""
import os
from pathlib import Path

# Environment variables
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# CV parameters
DEFAULT_FPS = int(os.getenv("CV_FPS", "2"))  # Frame sampling rate
YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8m.pt")  # Model size: n, s, m, l, x
YOLO_CONFIDENCE_THRESHOLD = float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.5"))
YOLO_DEVICE = os.getenv("YOLO_DEVICE", "cpu")  # 'cpu' or 'cuda' (0 for GPU)

# ByteTrack parameters
BYTETRACK_MIN_TRACK_LENGTH = int(os.getenv("BYTETRACK_MIN_TRACK_LENGTH", "3"))
BYTETRACK_TRACK_BUFFER = int(os.getenv("BYTETRACK_TRACK_BUFFER", "30"))
BYTETRACK_MATCH_THRESHOLD = float(os.getenv("BYTETRACK_MATCH_THRESHOLD", "0.7"))

# Video input sources
VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", "0")  # "0" for webcam, or path to file
REPLAY_MODE = os.getenv("REPLAY_MODE", "false").lower() == "true"  # Replay recorded video

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Paths
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
