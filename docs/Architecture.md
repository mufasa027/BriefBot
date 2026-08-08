# CipherBrief Architecture

CipherBrief is an autonomous, AI-driven newsroom that operates on a continuous loop of data ingestion, processing, and publishing.

## Core Components

### 1. Collectors (`collectors/`)
Responsible for fetching raw data from the outside world. Currently implements RSS polling across 8 major news sources using `feedparser`.

### 2. Database (`database/`)
SQLite database managed via SQLAlchemy. Stores two primary tables:
- `news`: Raw incoming articles.
- `stories`: Clustered events combining multiple articles.

### 3. Story Engine (`story_engine/`)
The brain of the system.
- **Similarity**: Detects when two articles discuss the same event using Jaccard similarity and Entity overlap.
- **Clustering**: Groups articles into `Story` objects.
- **Editorial**: Evaluates which stories meet the quality threshold for publishing based on coverage score.

### 4. AI Layer (`ai/`)
Interfaces with LLMs via OpenRouter.
- **Ranker**: Scores virality and importance.
- **Generator**: Synthesizes headlines, captions, and hashtags.

### 5. Designer (`designer/`)
Python/OpenCV-based rendering engine that dynamically generates Instagram-ready graphics with text overlays and background images.

### 6. Publisher (`publisher/`)
Handles export to GitHub Storage and direct API posting to Instagram.

### 7. Dashboard (`app.py`)
A Streamlit interface for human-in-the-loop oversight. Allows editors to view stories, preview rendered graphics, and manually approve or reject posts.
