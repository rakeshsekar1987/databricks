# =============================================================================
# Angular Module Federation POC - Multi-Stage Dockerfile
# =============================================================================
#
# This Dockerfile supports building both the Shell (host) and remote modules
# using multi-stage builds with shared base layers for efficiency.
#
# Build targets:
#   - shell:  The host application
#   - module: Any remote module (specify MODULE_NAME arg)
#
# Usage:
#   docker build --target shell -t mf-shell .
#   docker build --target module --build-arg MODULE_NAME=tax-reporting -t mf-tax-reporting .
#
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base - Common dependencies and setup
# -----------------------------------------------------------------------------
FROM node:18-alpine AS base

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache python3 make g++

# Copy package files for dependency installation
COPY package*.json ./
COPY angular.json tsconfig.json ./

# Install all dependencies using lock file for reproducible builds
COPY package-lock.json ./
RUN npm ci --legacy-peer-deps

# -----------------------------------------------------------------------------
# Stage 2: Source - Copy all source files
# -----------------------------------------------------------------------------
FROM base AS source

# Copy shared library (required by all builds)
COPY projects/shared-lib ./projects/shared-lib

# Copy all project sources
COPY projects/shell ./projects/shell
COPY projects/reg-reporting ./projects/reg-reporting
COPY projects/financial-reporting ./projects/financial-reporting
COPY projects/expense-reporting ./projects/expense-reporting
COPY projects/tax-reporting ./projects/tax-reporting
COPY projects/control-tower ./projects/control-tower

# -----------------------------------------------------------------------------
# Stage 3: Build Shared Library
# -----------------------------------------------------------------------------
FROM source AS build-shared

# Build the shared library first (dependency for all modules)
RUN npm run build:shared

# -----------------------------------------------------------------------------
# Stage 4: Build Shell Application
# -----------------------------------------------------------------------------
FROM build-shared AS build-shell

# Build shell application
RUN npm run build:shell

# -----------------------------------------------------------------------------
# Stage 5: Build Remote Module (parameterized)
# -----------------------------------------------------------------------------
FROM build-shared AS build-module

ARG MODULE_NAME=reg-reporting

# Build the specified module
RUN npm run build:${MODULE_NAME}

# -----------------------------------------------------------------------------
# Stage 6: Shell Production Image
# -----------------------------------------------------------------------------
FROM nginx:alpine AS shell

# Copy custom nginx configuration
COPY infrastructure/docker/nginx/shell.conf /etc/nginx/conf.d/default.conf

# Copy built shell application
COPY --from=build-shell /app/dist/shell/browser /usr/share/nginx/html

# Create health check endpoint
RUN mkdir -p /usr/share/nginx/html/health

# Set proper permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

# -----------------------------------------------------------------------------
# Stage 7: Module Production Image (parameterized)
# -----------------------------------------------------------------------------
FROM nginx:alpine AS module

ARG MODULE_NAME=reg-reporting

# Copy custom nginx configuration
COPY infrastructure/docker/nginx/module.conf /etc/nginx/conf.d/default.conf

# Copy built module - handle both possible output paths
COPY --from=build-module /app/dist/${MODULE_NAME}/browser /usr/share/nginx/html

# Set proper permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check - verify remoteEntry.js is accessible
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost/remoteEntry.js || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
