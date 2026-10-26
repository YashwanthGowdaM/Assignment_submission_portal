FROM nginx:alpine
RUN apk update && apk upgrade --no-cache

WORKDIR /usr/share/nginx/html

# Static assets
COPY static/ ./static/

# Optional custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
