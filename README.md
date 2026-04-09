# CodeRAG: AI-Powered Code Assistant

A sophisticated Retrieval-Augmented Generation (RAG) system that ingests GitHub repositories and provides intelligent Q&A capabilities about codebase content using advanced AI models.

## 🚀 Features

- **Repository Ingestion**: Clone and process GitHub repositories automatically
- **Intelligent Chunking**: Smart code splitting with overlap for optimal retrieval
- **Vector Search**: Fast semantic search using ChromaDB vector database
- **Multi-Model Support**: Choose between Groq (cloud) or Ollama (local) LLMs
- **User Authentication**: Secure JWT-based auth system
- **Rate Limiting**: Built-in API rate limiting with SlowAPI
- **Modern UI**: Streamlit-based web interface for easy interaction
- **Docker Ready**: Complete containerization for easy deployment
- **Caching**: Redis-based caching for improved performance

## 🛠 Tech Stack

### Backend
- **FastAPI**: High-performance async web framework
- **SQLAlchemy**: ORM for database operations
- **PostgreSQL**: Primary database
- **Redis**: Caching and session storage
- **ChromaDB**: Vector database for embeddings
- **Groq/Ollama**: LLM providers
- **JWT**: Authentication tokens

### Frontend
- **Streamlit**: Interactive web UI
- **Requests**: HTTP client for API communication

### DevOps
- **Docker & Docker Compose**: Containerization
- **Python 3.11**: Runtime environment
- **Poetry/Pip**: Dependency management

## 📋 Prerequisites

- Docker and Docker Compose
- Git
- Python 3.11+ (for local development)
- GitHub Personal Access Token (for repository access)

## 🏗 Installation & Setup

### Quick Start with Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd pro1
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   # ⚠️  NEVER commit .env to version control
   ```

3. **Launch the application**
   ```bash
   # For development (default)
   docker-compose up --build

   # For production with custom settings
   docker-compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Production Deployment

For production deployment with proper security:

1. **Set production environment variables**
   ```bash
   export DEBUG=false
   export LOG_LEVEL=WARNING
   export CREATE_DEFAULT_ACCOUNT=false
   # Set other production secrets
   ```

2. **Use reverse proxy** (nginx/traefik) for SSL and load balancing

3. **For fully production-ready deployment**, set these environment variables:
   ```bash
   export POSTGRES_CONTAINER_NAME=code-ragg-postgres-prod
   export REDIS_CONTAINER_NAME=code-ragg-redis-prod
   export WEB_CONTAINER_NAME=code-ragg-web-prod
   export FRONTEND_CONTAINER_NAME=code-ragg-frontend-prod
   # Remove ports for internal networking only
   export POSTGRES_PORT=
   export REDIS_PORT=
   export WEB_PORT=
   export FRONTEND_PORT=
   ```

### Local Development Setup

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements_backend.txt
   ```

3. **Set up external services**
   - Start PostgreSQL and Redis (or use Docker)
   - Configure Ollama (if using local models)

4. **Run the backend**
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Run the frontend** (in another terminal)
   ```bash
   streamlit run streamlit_app.py
   ```

## � Security

### Environment Variables
- **Never commit `.env` to version control** - it's in `.gitignore`
- Use strong, randomly generated `SECRET_KEY`: `python -c "import secrets; print(secrets.token_hex(32))"`
- Store API keys securely (environment variables, secret managers)
- Use `.env.example` as a template for required variables

### Production Security
- Use `docker-compose.prod.yml` for production deployments
- Implement proper authentication and authorization
- Enable HTTPS with SSL certificates
- Use managed database services instead of local containers
- Regularly rotate API keys and secrets

## �🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/code_ragg_db

# Redis
REDIS_URL=redis://localhost:6379

# API Keys
GROQ_API_KEY=your_groq_api_key
JINA_API_KEY=your_jina_api_key

# LLM Configuration
USE_GROQ=true
USE_OLLAMA=false
OLLAMA_BASE_URL=http://localhost:11434

# Security
SECRET_KEY=your_secure_random_key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Other settings
MAX_CONTEXT_TOKENS=2000
DEBUG=false
```

## 📖 Usage

### Web Interface

1. **Register/Login**: Create an account or log in
2. **Ingest Repository**: Enter a GitHub repository URL to process
3. **Ask Questions**: Query the ingested codebase with natural language

### API Usage

#### Authentication
```bash
# Login
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"

# Use the returned access_token for authenticated requests
```

#### Ingest Repository
```bash
curl -X POST "http://localhost:8000/ingest" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo"}'
```

#### Ask Questions
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/user/repo",
    "question": "How does the authentication work?"
  }'
```

## 🚀 Deployment

### Production Deployment

1. **Update environment variables** for production settings
2. **Use managed services** for PostgreSQL and Redis (e.g., Supabase, Redis Cloud)
3. **Configure reverse proxy** (nginx) for SSL and load balancing
4. **Set up monitoring** and logging

### Docker Deployment

```bash
# Production build
docker-compose -f docker-compose.yml up -d

# With custom environment
docker-compose --env-file .env.prod up -d
```

### Cloud Platforms

The application is compatible with:
- **Render**: Free tier with 512MB RAM limit
- **Railway**: Easy Docker deployment
- **Heroku**: Traditional PaaS deployment
- **AWS/GCP/Azure**: Full cloud infrastructure

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write tests for new features
- Update documentation
- Use type hints
- Keep dependencies minimal

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [ChromaDB](https://www.trychroma.com/) for vector database capabilities
- [Groq](https://groq.com/) for fast LLM inference
- [Ollama](https://ollama.ai/) for local model hosting

## 📞 Support

For questions or issues:
- Open an issue on GitHub
- Check the API documentation at `/docs`
- Review the setup guide in `OLLAMA_GROQ_SETUP.md`

---

**Happy coding! 🚀**