# Build stage
FROM node:18-slim as builder

WORKDIR /app

# Install dependencies
COPY web/package*.json ./
RUN npm ci

# Copy source code
COPY web/ ./

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 3000

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
