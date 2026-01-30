# Module Registry Service Dockerfile
FROM node:18-alpine

# Create app directory
WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Copy package files
COPY package.json ./

# No npm install needed - vanilla Node.js

# Copy source
COPY server.js ./

# Set ownership
RUN chown -R appuser:appgroup /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:4000/health || exit 1

# Use non-root user
USER appuser

# Expose port
EXPOSE 4000

# Start server
CMD ["node", "server.js"]
