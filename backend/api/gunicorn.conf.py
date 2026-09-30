import os

# Render automatically injects the PORT environment variable (typically 10000).
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Single worker to prevent PyTorch/Transformers memory duplication on Render free tier
workers = 1
threads = 2
timeout = 120

accesslog = "-"
errorlog = "-"
