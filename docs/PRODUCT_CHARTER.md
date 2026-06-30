# AutoQuant Product Charter

## Product Name
AutoQuant - Local Trading Strategy Validation Engine

## Owner Intent
Mohs / Mohsen aims to build a serious local strategy lab that helps create, test, improve, validate, and export Freqtrade-compatible trading strategies. The owner's goal is to establish a complete validation workflow that moves from strategy ideas to rigorously tested, export-ready trading strategies.

## What AutoQuant Is
AutoQuant is a complete local-only trading strategy validation application for one private user. It serves as a serious local strategy lab that helps:
- Create trading strategies from scratch
- Validate and improve existing strategies
- Repair and optimize uploaded strategy files
- Export Freqtrade-ready strategy configurations
- Provide structured validation workflows with robust testing

## What AutoQuant Is Not
AutoQuant is not:
- A SaaS product
- A public platform
- A deployment project
- A minimal demo
- A guaranteed profitable strategy generator
- A cloud-based service
- A multi-user system

## Core Rule
**AI suggests. Backend validates. Freqtrade tests. AutoQuant decides.**

This operating principle defines the workflow:
1. AI provides initial strategy suggestions, improvements, or repairs
2. Backend systems validate the strategy structure, logic, and parameters
3. Freqtrade runs comprehensive backtests and forward tests
4. AutoQuant's decision engine evaluates all results and determines strategy fitness

## Local-Only Architecture Principle
AutoQuant must run entirely on the user's own machine. All components, data, artifacts, and processing must remain local:
- Frontend: Next.js + React (local web interface)
- Backend: FastAPI + Python (local API server)
- Database: SQLite (local file-based database)
- AI: Ollama/local LLM integration (local inference)
- Trading engine: Freqtrade (local installation)
- Artifacts: local filesystem folders
- Secrets: `.env` file only, never hardcoded tokens

No cloud deployment, Docker deployment, Kubernetes, PostgreSQL, SaaS multi-user authentication, public hosting, or paid API dependencies as core requirements.

## Main User Journey
1. **Input Phase**: User provides strategy idea, uploads existing strategy file, or requests repair
2. **AI Phase**: Local LLM analyzes input and suggests strategy improvements or generates initial code
3. **Validation Phase**: Backend validates strategy structure, syntax, and parameter integrity
4. **Testing Phase**: Freqtrade executes backtests and validation checks on historical data
5. **Decision Phase**: AutoQuant evaluates metrics, robustness, and risk factors to determine strategy fitness
6. **Export Phase**: If strategy passes validation, export Freqtrade-ready `.py` strategy file and matching `.json` parameter file

## Final Output Expectation
When a strategy passes validation, AutoQuant must produce:
- **Strategy file**: Freqtrade-compatible `.py` strategy file
- **Parameter file**: Matching `.json` configuration file with all strategy parameters
- **Validation report**: Comprehensive test results, metrics, and decision rationale
- **Optional**: Export config files for direct Freqtrade deployment

## Non-Negotiable Safety Rule
AutoQuant does not guarantee profitable trading strategies. It is a validation engine that:
- Helps search for profitable candidates
- Requires every claim to be backed by tests, metrics, and robustness checks
- Provides clear decision logic for strategy acceptance
- Never presents untested strategies as profitable
- Always exposes risk factors and limitations

## Definition of Project Success
AutoQuant succeeds when it:
1. Provides a complete, structured validation workflow from idea to export
2. Generates strategies that pass Freqtrade backtesting with documented metrics
3. Maintains strict local-only architecture with no external dependencies
4. Delivers clear, explainable decision logic for strategy validation
5. Produces export-ready `.py` and `.json` files for approved strategies
6. Operates reliably on the user's local machine with predictable performance
