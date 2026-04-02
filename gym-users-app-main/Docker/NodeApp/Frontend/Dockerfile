FROM node:18-bullseye-slim

WORKDIR /app

COPY package*.json ./
RUN apt-get update && apt-get install -y python3 python3-pip build-essential --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN npm install --ignore-engines --no-optional

COPY src ./src
COPY public ./public
COPY . . 

ENV DANGEROUSLY_DISABLE_HOST_CHECK=true
ENV HOST=0.0.0.0

EXPOSE 3000
CMD ["npm", "start"]