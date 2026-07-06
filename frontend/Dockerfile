FROM node:18-alpine AS build

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .
# Vite resuelve import.meta.env.VITE_* en tiempo de BUILD, no en runtime del
# contenedor — a diferencia del servidor `vite dev` anterior, que sí las leía
# del entorno del proceso en caliente. Sin este ARG, el bundle de producción
# queda apuntando al valor por defecto hardcodeado en el código (localhost:8000).
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
