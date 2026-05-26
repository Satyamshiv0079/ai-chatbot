#!/bin/bash
cd backend && python api/app.py &
cd frontend/chatbot-ui && npm run build && npx serve -s dist -l 5000
