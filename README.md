# RAG-Driven Investment Portfolio

A sophisticated RAG (Retrieval-Augmented Generation) system that provides AI-powered investment insights based on real-time news analysis of the defense and semiconductor industries.

## 🚀 Features

- **Real-time News Ingestion**: Fetches news from multiple sources (Reuters, CNBC, WSJ, Bloomberg, Yahoo Finance, etc.)
- **AI-Powered Summaries**: GPT-4 generates concise industry summaries with source citations
- **Investment Ideas**: AI suggests long-term stock picks and short-term option plays
- **Vector Search**: Semantic search using OpenAI embeddings and Chroma vector database
- **Mobile App**: React Native mobile interface for easy access
- **Scheduled Updates**: Automatic data refresh every 60 minutes, summaries every 5 minutes
- **Source Transparency**: All insights include explicit source references
- **YAML Configuration**: Flexible configuration system with separate config files

## 🏗️ Architecture

```
Data Sources → Ingestion → Text Processing → Vector Store → LLM → API → Mobile UI
     ↓              ↓            ↓              ↓         ↓      ↓       ↓
News APIs    → Cleaning → Chunking → Embeddings → GPT-4 → FastAPI → React Native
```

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI
- **LLM**: OpenAI GPT-4-turbo
- **Embeddings**: OpenAI text-embedding-ada-002
- **Vector Database**: Chroma
- **RAG Framework**: LangChain
- **Data Sources**: NewsAPI, Alpha Vantage, Finnhub, RSS feeds
- **Configuration**: YAML-based config system

### Frontend
- **Mobile**: React Native with Expo
- **UI Components**: React Native Paper
- **Styling**: StyleSheet

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- API keys for:
  - OpenAI
  - NewsAPI
  - Alpha Vantage
  - Finnhub

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd RAG-Driven-Portfolio
```

### 2. Install Dependencies

```bash
# Backend dependencies
pip install -r requirements.txt

# Mobile app dependencies
cd mobile
npm install
cd ..
```

### 3. Environment Configuration

Copy the example environment file and configure your API keys:

```bash
cp config.env.example .env
```

Edit `.env` with your API keys:

```env
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# News APIs
NEWSAPI_API_KEY=your_newsapi_key_here
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
FINNHUB_API_KEY=your_finnhub_key_here
```

### 4. Configuration Files

The system uses YAML configuration files in the `config/` directory:

- **`config/rag_config.yaml`**: RAG pipeline settings, LLM parameters, vector store config
- **`config/api_config.yaml`**: API server settings, data sources, CORS config
- **`config/app_config.yaml`**: Application settings, logging, mobile app config

You can customize these files to adjust:
- Chunk sizes and overlap
- LLM model and parameters
- Data source settings
- Server configuration
- Scheduling intervals
- Industry keywords and tickers

### 5. Start the Backend

```bash
python run.py
```

The API server will start on the configured host and port (default: `http://localhost:8000`)

### 6. Start the Mobile App

```bash
cd mobile
npm start
```

Use the Expo Go app on your mobile device to scan the QR code.

## 📚 Configuration System

### Configuration Files

#### `config/rag_config.yaml`
```yaml
rag:
  # Text Processing
  chunk_size: 1000
  chunk_overlap: 200
  
  # LLM Settings
  max_tokens: 300
  temperature: 0.7
  model: "gpt-4-turbo-preview"
  
  # Retrieval Settings
  retrieval_top_k: 10
  max_history_size: 6
  
  # Scheduling (in minutes)
  data_ingestion_interval: 60
  summarization_interval: 5
  
  # Vector Database
  vector_store:
    persist_directory: "./chroma_db"
    embedding_model: "text-embedding-ada-002"
    distance_metric: "cosine"
  
  # Industries and Keywords
  industries:
    defense:
      keywords: ["defense", "military", "aerospace", ...]
      tickers: ["LMT", "RTX", "BA", ...]
    semiconductor:
      keywords: ["semiconductor", "chip", ...]
      tickers: ["TSMC", "AMD", "NVDA", ...]
```

#### `config/api_config.yaml`
```yaml
api:
  # Server Settings
  server:
    host: "0.0.0.0"
    port: 8000
    debug: false
    log_level: "info"
  
  # CORS Settings
  cors:
    allow_origins: ["*"]
    allow_credentials: true
    allow_methods: ["*"]
    allow_headers: ["*"]
  
  # Data Sources
  data_sources:
    newsapi:
      enabled: true
      base_url: "https://newsapi.org/v2"
      page_size: 50
      language: "en"
      sort_by: "publishedAt"
    
    rss_feeds:
      enabled: true
      feeds:
        - name: "Reuters Business"
          url: "https://feeds.reuters.com/reuters/businessNews"
          max_articles: 20
  
  # Search Settings
  search:
    default_top_k: 10
    max_top_k: 50
    recent_hours: 24
```

#### `config/app_config.yaml`
```yaml
app:
  # Application Info
  name: "RAG-Driven Investment Portfolio"
  version: "1.0.0"
  description: "AI-powered investment insights from real-time news analysis"
  
  # Environment
  environment: "development"  # development, staging, production
  
  # Mobile App
  mobile:
    api_base_url: "http://localhost:8000"
    refresh_interval: 300  # 5 minutes in seconds
    max_retries: 3
    timeout: 30
```

### Environment Variable Overrides

You can override any configuration value using environment variables:

```bash
# Override chunk size
export RAG_CHUNK_SIZE=1500

# Override server port
export API_SERVER_PORT=9000

# Override LLM model
export RAG_MODEL=gpt-4
```

## 📚 API Documentation

### Core Endpoints

#### GET `/fetchSummaries`
Returns the latest industry summaries.

**Response:**
```json
{
  "defense_summary": {
    "summary_text": "Recent defense industry developments...",
    "sources": [
      {
        "url": "https://www.reuters.com/...",
        "source": "Reuters",
        "timestamp": "2025-01-26T10:00:00Z"
      }
    ],
    "generated_at": "2025-01-26T10:30:00Z"
  },
  "semiconductor_summary": {
    "summary_text": "Recent semiconductor industry developments...",
    "sources": [...],
    "generated_at": "2025-01-26T10:30:00Z"
  }
}
```

#### GET `/fetchInvestmentIdeas`
Returns investment recommendations.

**Response:**
```json
{
  "long_term_stocks": [
    {
      "ticker": "LMT",
      "company_name": "Lockheed Martin",
      "reason": "Strong defense contract backlog...",
      "source_references": [...]
    }
  ],
  "short_term_options": [
    {
      "ticker": "AMD",
      "option_type": "call",
      "strike_price": 125.0,
      "expiration_date": "2025-02-08",
      "direction": "bullish",
      "reason": "Recent earnings beat...",
      "source_references": [...]
    }
  ],
  "generated_at": "2025-01-26T10:30:00Z"
}
```

### Management Endpoints

#### GET `/health`
Health check endpoint.

#### GET `/stats`
System statistics including vector store info.

#### GET `/config`
Get current configuration (without sensitive data).

#### POST `/trigger/ingestion`
Manually trigger data ingestion.

#### POST `/trigger/summarization`
Manually trigger summarization.

#### POST `/trigger/full-pipeline`
Manually trigger the complete pipeline.

### Search Endpoints

#### GET `/search/{industry}`
Search for news in a specific industry.

#### GET `/search/ticker/{ticker}`
Search for news by ticker symbol.

## 🔧 Configuration Management

### Configuration Manager

The system includes a `ConfigManager` class that:

- Loads YAML configuration files
- Provides environment variable overrides
- Validates configuration integrity
- Supports nested configuration access
- Enables runtime configuration reloading

### Adding New Industries

To add a new industry, update `config/rag_config.yaml`:

```yaml
rag:
  industries:
    technology:
      keywords: ["technology", "software", "cloud", ...]
      tickers: ["AAPL", "MSFT", "GOOGL", ...]
```

### Customizing Data Sources

To add new data sources, update `config/api_config.yaml`:

```yaml
api:
  data_sources:
    custom_api:
      enabled: true
      base_url: "https://api.example.com"
      api_key_env: "CUSTOM_API_KEY"
```

## 📱 Mobile App Features

- **Real-time Updates**: Automatic refresh based on configuration
- **Pull-to-Refresh**: Manual refresh capability
- **Source Links**: Clickable source references
- **Industry Summaries**: Defense and semiconductor insights
- **Investment Ideas**: Long-term stocks and short-term options
- **Modern UI**: Clean, professional interface
- **Dynamic Configuration**: Loads settings from API

## 🔍 Data Sources

### News Sources
- Reuters
- CNBC
- Wall Street Journal
- Bloomberg
- Yahoo Finance
- NewsAPI

### Financial Data
- Alpha Vantage
- Finnhub
- Yahoo Finance

### Industries Covered
- **Defense**: LMT, RTX, BA, GD, NOC, LHX, TDG, AJRD, KTOS
- **Semiconductor**: TSMC, AMD, NVDA, INTC, QCOM, AVGO, MU, TXN, ADI, KLAC, AMAT, LRCX

## 🚀 Deployment

### Production Setup

1. **Environment**: Use production-grade environment variables
2. **Configuration**: Update config files for production settings
3. **Database**: Consider using a production vector database (Pinecone, Weaviate)
4. **API Keys**: Secure API key management
5. **Monitoring**: Add logging and monitoring
6. **Scaling**: Consider containerization with Docker

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "run.py"]
```

### Environment-Specific Configs

Create environment-specific configuration files:

```bash
config/
├── rag_config.yaml          # Base RAG config
├── rag_config.prod.yaml     # Production RAG config
├── api_config.yaml          # Base API config
├── api_config.prod.yaml     # Production API config
├── app_config.yaml          # Base app config
└── app_config.prod.yaml     # Production app config
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Update configuration files if needed
5. Add tests
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## ⚠️ Disclaimer

This application is for educational and research purposes only. Investment decisions should not be based solely on AI-generated insights. Always conduct your own research and consult with financial advisors.

## 🆘 Support

For issues and questions:
1. Check the logs for error messages
2. Verify API keys are correctly configured
3. Ensure all dependencies are installed
4. Check the API documentation at `http://localhost:8000/docs`
5. Validate configuration files using the `/config` endpoint

## 🔄 Updates

The system automatically:
- Fetches new news based on configured intervals
- Updates summaries based on configured intervals
- Maintains a history of the last N updates (configurable)
- Refreshes the mobile app based on configured intervals
- Loads configuration from YAML files with environment variable overrides