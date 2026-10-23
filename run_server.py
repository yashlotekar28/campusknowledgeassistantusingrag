"""One-click server launcher for the Campus Knowledge Assistant."""

import uvicorn
from src.config import config

if __name__ == "__main__":
    print(f"\n🚀 Starting MIT AOE Campus Knowledge Assistant...")
    print(f"👉 Open in your browser: http://localhost:{config.server_port}\n")
    uvicorn.run(
        "src.api:app",
        host=config.server_host,
        port=config.server_port,
        reload=True,
    )
