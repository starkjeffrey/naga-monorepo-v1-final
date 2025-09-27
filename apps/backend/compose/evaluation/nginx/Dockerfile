FROM docker.io/nginx:1.25-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY ./compose/evaluation/nginx/default.conf /etc/nginx/conf.d/default.conf

# Create log directory for evaluation debugging
RUN mkdir -p /var/log/nginx/evaluation && \
    touch /var/log/nginx/evaluation/access.log && \
    touch /var/log/nginx/evaluation/error.log

# Expose port 80 for the reverse proxy
EXPOSE 80