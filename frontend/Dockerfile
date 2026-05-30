# Use a lightweight official Node image
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy dependency specifications
COPY package.json package-lock.json ./

# Clean install node dependencies
RUN npm ci

# Copy frontend source code
COPY . .

# Expose Vite dev server port
EXPOSE 5000

# Start Vite dev server in non-interactive container mode
CMD ["npm", "run", "dev"]
