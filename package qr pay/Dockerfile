FROM node:24-alpine
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev --ignore-scripts
COPY src ./src
ENV HOST=0.0.0.0 PORT=8787 QR_SQLITE_PATH=/data/qr-payments.sqlite
EXPOSE 8787
VOLUME /data
CMD ["node", "src/cli.js"]
