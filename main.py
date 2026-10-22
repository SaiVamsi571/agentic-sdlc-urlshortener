"""
AetherSDLC - Unified System Entrypoint.
Launches the Web Dashboard and Orchestration Engine, or runs CLI scenarios.

Usage:
    python main.py                  # Launches Interactive Web Dashboard on http://127.0.0.1:8000
    python main.py --cli            # Launches Interactive Terminal CLI
    python main.py --scenario all   # Executes all 3 scenarios via CLI
"""
from __future__ import annotations
import argparse
import sys
import uvicorn
from src.config import CONFIG

def main():
    parser = argparse.ArgumentParser(description="AetherSDLC Agentic Software Engineering System")
    parser.add_argument("--cli", action="store_true", help="Launch Rich Terminal CLI instead of Web Dashboard")
    parser.add_argument("--scenario", choices=["greenfield", "brownfield", "ambiguous", "all"], help="Execute specific scenario directly")
    parser.add_argument("--port", type=int, default=CONFIG.web_port, help="Port for Web Dashboard server")
    parser.add_argument("--host", type=str, default=CONFIG.web_host, help="Host address for Web Dashboard server")
    args = parser.parse_args()

    if args.cli or args.scenario:
        import asyncio
        from src.cli import main as cli_main
        sys.argv = [sys.argv[0]]
        if args.scenario:
            sys.argv.extend(["--scenario", args.scenario])
        asyncio.run(cli_main())
    else:
        print("=" * 76)
        print("    AETHERSDLC : AGENTIC SOFTWARE ENGINEERING ORCHESTRATION SYSTEM")
        print("=" * 76)
        print(f"[*] Starting Interactive Web Dashboard at: http://{args.host}:{args.port}")
        print(f"[*] OpenAPI Documentation at:             http://{args.host}:{args.port}/docs")
        print(f"[*] Target URL Shortener Service at:      http://{args.host}:{args.port}/shortener")
        print("=" * 76)
        uvicorn.run("src.web.server:dashboard_app", host=args.host, port=args.port, reload=False)

if __name__ == "__main__":
    main()
