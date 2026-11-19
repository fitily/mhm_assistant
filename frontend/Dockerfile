# Étape 1 : compilation de l'application Vue
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# false = le frontend parle au vrai backend ; true = réponses fictives
ARG VITE_USE_MOCK=false
ENV VITE_USE_MOCK=$VITE_USE_MOCK
ENV VITE_API_BASE_URL=/api
RUN npm run build

# Étape 2 : service des fichiers statiques par nginx
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
