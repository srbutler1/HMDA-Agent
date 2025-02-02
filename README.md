# HMDA Multi-Agent System

A multi-agent system for analyzing Home Mortgage Disclosure Act (HMDA) data and providing loan qualification assistance.

## Overview

This project consists of two main components:

1. **Customer-Facing Agent**
   - Helps users understand what types of loans they may qualify for in their region
   - Integrates HMDA data with regional census information
   - Provides personalized recommendations based on user inputs

2. **Research Analysis Agent**
   - Enables researchers to analyze HMDA data
   - Provides tools for data visualization and statistical analysis
   - Supports custom queries and data export

## Data Sources

- HMDA Data: Retrieved from FFIEC API (https://ffiec.cfpb.gov/v2/data-browser-api/view/csv)
- Census Data: Local integration of census flat files
- MSA/Regional Data: FFIEC census and demographic information

## Project Structure

```
.
├── agents/                 # Agent implementations
│   ├── customer/          # Customer-facing agent
│   └── research/          # Research analysis agent
├── data/                  # Data processing scripts and cached data
│   ├── census/           # Census data processing
│   ├── hmda/             # HMDA data integration
│   └── cache/            # Cached API responses
├── api/                   # API implementations
├── web/                   # Web interface
├── tests/                # Test suites
├── docs/                 # Documentation
└── docker/               # Docker configuration
```

## Requirements

- Python 3.8+
- Node.js 18+
- Docker
- PostgreSQL 13+

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/hmda-agent.git
cd hmda-agent
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Install Node.js dependencies:
```bash
cd web
npm install
```

5. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

6. Start the development environment:
```bash
docker-compose up -d
```

## Development

1. Start the API server:
```bash
python api/main.py
```

2. Start the web interface:
```bash
cd web
npm start
```

3. Run tests:
```bash
pytest tests/
```

## Docker Deployment

Build and run the containers:
```bash
docker-compose up --build
```

## API Documentation

The API documentation is available at `/docs` when running the server.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- FFIEC for providing the HMDA data
- Census Bureau for demographic data
- All contributors and researchers using this tool
