import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'
os.environ['DEMO_MODE'] = 'true'
os.environ['EVENT_PROVIDER'] = 'demo'
