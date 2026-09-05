# Build stage
FROM node:26-alpine AS builder

WORKDIR /app

# Vite env vars must be available at build time
ARG VITE_API_URL
ARG VITE_API_TOKEN

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Expose build-time variables to the Vite build
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_API_TOKEN=${VITE_API_TOKEN}

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files from builder
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

