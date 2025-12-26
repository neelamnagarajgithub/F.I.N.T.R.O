# Use a modern Node runtime
FROM node:20-alpine

# Create app directory
WORKDIR /app

# copy package files and install dependencies (including dev deps so prisma CLI is available)
COPY package.json package-lock.json* ./ 
RUN npm ci --silent

# copy project files
COPY . .

# Ensure node_modules bin is available
ENV PATH /app/node_modules/.bin:$PATH
ENV NODE_ENV=production

# Expose the port Cloud Run will bind to via PORT env var (default 8080)
EXPOSE 8080

# Run prisma generate at container start (uses runtime env vars) then start the app
CMD ["sh", "-lc", "npx prisma generate && node server.js"]