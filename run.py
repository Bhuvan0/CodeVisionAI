#!/usr/bin/env python3
"""
CodeVision AI - Run Script
Starts the FastAPI server with proper configuration.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def main():
    """Run the CodeVision AI server."""
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "true").lower() == "true"
    
    print(f"""
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║   🔮 CodeVision AI                                ║
    ║   LLM-Powered Reverse Engineering Diagram Gen    ║
    ║                                                   ║
    ║   Server: http://{host}:{port}                      ║
    ║   Debug: {debug}                                   ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="debug" if debug else "info"
    )


if __name__ == "__main__":
    main()
