# Furniture Recommender API Deployment

This guide explains how to run and deploy the Furniture Recommender API locally using Docker and on Render.

## Prerequisites

- Docker installed on your system (for local development)
- Docker Compose (optional, for easier local environment management)
- Render account (for cloud deployment)

## Local Development with Docker

### Using Docker Compose (Recommended)

1. Set environment variables in your shell or create a `.env` file locally (not committed to repo):
   ```bash
   export OPENROUTER_API_KEY=your_key_here
   export PINECONE_API_KEY=your_key_here
   # ... set all required variables
   ```

2. Run the application:
   ```bash
   docker-compose up --build
   ```

3. The API will be available at `http://localhost:10000`

### Using Docker Directly

1. Build the Docker image:
   ```bash
   docker build -t furniture-recommender .
   ```

2. Run the container with environment variables:
   ```bash
   docker run -p 10000:10000 \
     -e OPENROUTER_API_KEY=your_key \
     -e PINECONE_API_KEY=your_key \
     # ... other env vars \
     furniture-recommender
   ```

3. The API will be available at `http://localhost:10000`

## Environment Variables

The application requires the following environment variables:

- `OPENROUTER_API_KEY`: API key for OpenRouter/OpenAI
- `PINECONE_API_KEY`: API key for Pinecone vector database
- `PINECONE_INDEX`: Pinecone index name
- `PINECONE_REGION`: Pinecone region
- `DATABASE_URL`: PostgreSQL database URL
- `EMBED_MODEL`: Embedding model name
- `HF_TOKEN`: Hugging Face token
- `IKARUS_SPACE`: Ikarus space identifier

## Deploying to Render

1. **Connect Repository**: Push your code to GitHub and connect it to Render.

2. **Create Web Service**:
   - Select "Docker" as the environment.
   - Set build and start commands to blank (uses Dockerfile).
   - Set port to `10000`.

3. **Environment Variables**: Add all required variables in Render's environment settings (mark API keys as secrets).

4. **Deploy**: Render will build and deploy automatically. Your API will be available at the generated URL.

## API Endpoints

## API Endpoints

- `GET /health`: Health check endpoint
- `POST /search`: Search for furniture products
- `GET /item/{id}`: Get detailed information about a specific product

## Stopping the Application

### Using Docker Compose
```bash
docker-compose down
```

### Using Docker Directly
```bash
docker stop <container_id>
```

## Troubleshooting

- Ensure all environment variables are set correctly (in shell for local, in Render for deployment)
- Check that Docker is running and you have sufficient permissions
- Verify that the required ports (10000) are not in use by other applications
- For Render: Check deployment logs for errors related to missing env vars or DB connectivity