FROM node:22-slim

WORKDIR /app

# Install dependencies first so the layer is cached across source changes.
COPY package.json ./
RUN npm install

# Copy source.
COPY . .

EXPOSE 5173

# Vite dev server. ``--host 0.0.0.0`` is required for Docker port forwarding.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
