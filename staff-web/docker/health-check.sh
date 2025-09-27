#!/bin/sh
# Health check script for Staff-Web V2 production container

# Check if nginx is running
if ! pgrep nginx > /dev/null; then
    echo "Nginx is not running"
    exit 1
fi

# Check if the health endpoint responds
if ! wget --quiet --tries=1 --spider http://localhost:80/health; then
    echo "Health endpoint is not responding"
    exit 1
fi

# Check if main application files exist
if [ ! -f "/usr/share/nginx/html/index.html" ]; then
    echo "Main application file is missing"
    exit 1
fi

# Check nginx configuration
if ! nginx -t > /dev/null 2>&1; then
    echo "Nginx configuration is invalid"
    exit 1
fi

echo "Health check passed"
exit 0