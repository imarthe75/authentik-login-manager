FROM node:18-alpine

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

# node:18-alpine ya trae un usuario "node" (uid 1000) sin privilegios.
RUN chown -R node:node /app
USER node

EXPOSE 3000

CMD ["npm", "run", "dev"]
