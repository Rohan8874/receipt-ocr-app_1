import sys
from pathlib import Path

# Add this before Flask imports
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)