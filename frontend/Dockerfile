FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* yarn.lock* ./

# Install dependencies
RUN npm ci || npm install

# Copy app
COPY . .

# Expose port
EXPOSE 3000

# Dev server
CMD ["npm", "run", "dev"]
