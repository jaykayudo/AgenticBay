import os

# Provide required settings before any app module is imported
os.environ.setdefault("ORCHESTRATOR_API_KEY", "test-orchestrator-key")
os.environ.setdefault("AGENT_WALLET_ADDRESS", "0xTestWallet")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
