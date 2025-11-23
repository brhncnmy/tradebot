FROM nginx:alpine

# Remove default configuration
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy our custom config
COPY docker/nginx-proxy.conf /etc/nginx/conf.d/default.conf

# Expose port 80 inside the container
EXPOSE 80


