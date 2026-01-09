# AI Sports Buyer
AI Sports Buyer is a scenario-driven AI assistant that helps users make practical, low-risk decisions when purchasing sports and outdoor equipment.
Instead of recommending large numbers of products, the system focuses on identifying what is truly necessary for a given activity and user context, and helps users choose efficiently within one or two interactions.

---

## Key Features
- Scenario-based equipment recommendations (e.g. skiing, cycling, outdoor training)
- Product comparison with clear decision guidance
- Lightweight user profiling based on historical behavior data
- Streaming AI responses for better interaction experience
- Mobile-friendly front-end interface
---
## Project Structure
├─ index.html        Front-end interface (static web page)  
├─ server_back.py    FastAPI back-end service handling requests and streaming responses  
├─ llm_direct.py     Wrapper for large language model API calls  
├─ requirements.txt  Python dependency definitions  
├─ runtime.txt       Python runtime version for deployment environments  
├─ data/             Sample user profile data (Excel format)


## How It Works
- The front-end is a static web page that collects user input and displays AI responses.
- The back-end is a FastAPI service that:
  - Loads user profile data
  - Identifies user intent (recommendation, comparison, general inquiry)
  - Calls a large language model to generate responses
- The system uses server-side processing to keep API keys secure.
---

## Usage Notes
- This project requires a running back-end service to function.
- GitHub Pages can host the front-end UI, but AI responses require a deployed back-end.
- API keys must be provided via environment variables and should not be committed to the repository.

---

## Intended Use
- AI product recommendation demos
- Portfolio or prototype projects
- Exploration of AI-assisted decision-making systems
