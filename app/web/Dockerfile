# Portal web: build estático con Node y servido por nginx sin privilegios (puerto 8080) en Cloud Run.
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build && rm -f dist/config.json

FROM nginxinc/nginx-unprivileged:1.29-alpine
# La imagen procesa /etc/nginx/templates/*.template con envsubst al arrancar:
# así la misma imagen sirve para DEV/QA/PROD (API_URL, FIREBASE_* se inyectan en Cloud Run).
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
ENV API_URL=http://localhost:8080 AUTH_MODE=firebase \
    FIREBASE_API_KEY= FIREBASE_AUTH_DOMAIN= FIREBASE_PROJECT_ID=
EXPOSE 8080
