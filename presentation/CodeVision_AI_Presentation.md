# CodeVision AI - Course Project Presentation
## 8-Minute Presentation Slides

---

# SLIDE 1: TITLE SLIDE

## 🔮 CodeVision AI
### LLM-Powered Reverse Engineering Tool

**Presented by:**
- Sri Bhuvan Maddipudi (G01488473)
- Srilakshmi Praharshitha Gatta (G01475844)

**Course:** [Your Course Name]
**Date:** December 2024

---

# SLIDE 2: THE PROBLEM

## 😫 Understanding Code is Hard

### The Challenge:
- Joining a new project = weeks of reading code
- Legacy codebases have no documentation
- Tracing dependencies across 100+ files is tedious
- "What does this class do?" "Where is this function used?"

### Time Wasted:
- Developers spend **~60% of time** reading/understanding code
- Average onboarding time: **2-4 weeks** for new projects

> **"We spend more time reading code than writing it"**

---

# SLIDE 3: OUR SOLUTION

## 🔮 CodeVision AI

### What It Does:
✅ **Analyzes** entire codebases automatically
✅ **Generates** visual architecture diagrams
✅ **Explains** code in plain English using AI
✅ **Answers** any question about your project

### Input → Output:
```
Source Code Files  →  CodeVision AI  →  Visual Diagrams
                                    →  AI Explanations
                                    →  Interactive Chat
```

---

# SLIDE 4: VS GENERAL AI AGENTS

## 🤖 Why Not Just Use Claude Code or Copilot?

| Feature | Claude Code / Copilot | CodeVision AI |
|---------|----------------------|---------------|
| **Scope** | ONE file at a time | ENTIRE codebase |
| **Context** | Limited to current file | All files + relationships |
| **Output** | Text only | Visual diagrams + chat |
| **Purpose** | Code generation | Code comprehension |
| **Structure** | No awareness | Classes, deps, architecture |

### Key Insight:
> "Claude Code sees through a keyhole. CodeVision AI gives you the floor plan."

---

# SLIDE 5: KEY DIFFERENTIATORS

## 🎯 What Makes Us Different

### 1. Multi-File Analysis
- Parses ALL files in your project
- Extracts classes, functions, imports
- Builds complete dependency graph

### 2. Visual Diagrams
- Interactive tree visualization
- UML class diagrams
- Dependency flow charts

### 3. Project-Aware AI Chat
- AI knows about EVERY file
- Answer architecture questions
- Explain any component

---

# SLIDE 6: SYSTEM ARCHITECTURE

## 🏗️ How It's Built

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND                              │
│   Vanilla JS  +  D3.js (Tree)  +  Mermaid.js (UML)     │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 BACKEND (FastAPI)                        │
│            9 REST API Endpoints                         │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   PARSERS    │  │  LLM LAYER   │  │  DIAGRAMS    │
│              │  │              │  │              │
│ Python AST   │  │  LangChain   │  │  Mermaid     │
│ JS Regex     │  │  Google      │  │  PlantUML    │
│ 15+ langs    │  │  Gemini      │  │  Graphviz    │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

# SLIDE 7: TECHNICAL STACK

## 🔧 Technologies Used

### Backend
| Component | Technology |
|-----------|------------|
| Web Framework | FastAPI + Uvicorn |
| Language | Python 3.10+ |
| API Design | REST (9 endpoints) |

### Frontend
| Component | Technology |
|-----------|------------|
| Framework | Vanilla JavaScript |
| Tree Visualization | D3.js |
| UML Diagrams | Mermaid.js |
| Styling | CSS Variables (themes) |

### AI/ML
| Component | Technology |
|-----------|------------|
| LLM Orchestration | LangChain |
| Language Model | Google Gemini 1.5 Flash |
| Prompt Engineering | Custom templates |

---

# SLIDE 8: PARSERS DEEP DIVE

## 📝 How We Parse Code

### Python Parser (AST-based)
```python
# Uses Python's built-in Abstract Syntax Tree
tree = ast.parse(source_code)

# Extracts:
# - Classes with methods & attributes
# - Functions with parameters
# - Import dependencies
# - Type hints & decorators
```

### JavaScript Parser (Regex-based)
```javascript
// Pattern matching for JS/TS
class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?'

// Extracts:
// - ES6 classes
// - Functions & arrow functions
// - Import statements
// - TypeScript interfaces
```

### Supported Languages: 15+
Python, JavaScript, TypeScript, Java, Go, Rust, Ruby, PHP, C#, Swift, C, C++, Kotlin, and more

---

# SLIDE 9: LLM INTEGRATION

## 🧠 AI-Powered Analysis

### How It Works:
```
1. Parser extracts structured data
          ↓
2. Data formatted into prompt
          ↓
3. Sent to Google Gemini via LangChain
          ↓
4. AI generates summaries/answers
```

### LLM Features:
| Feature | What It Does |
|---------|--------------|
| Module Summaries | Explains what each file does |
| Relationship Analysis | Identifies patterns & architecture |
| Project Chat | Answers any question about code |
| Detailed Explanations | Deep-dive into specific modules |

### Why Gemini?
- Free tier available
- High-quality responses
- Fast inference

---

# SLIDE 10: DIAGRAM GENERATION

## 📊 Visual Output Formats

### Class Diagram (Mermaid)
```
classDiagram
    class UserService {
        -db
        +get_user(id)
        +create_user(data)
    }
    BaseService <|-- UserService
```

### Dependency Diagram
```
flowchart LR
    main --> parsers
    main --> llm
    main --> visualization
    parsers --> ast
```

### Formats Supported:
- **Mermaid** - Web rendering
- **PlantUML** - Documentation
- **Graphviz DOT** - Custom tools
- **JSON** - API integration

---

# SLIDE 11: DEMO TIME

## 🎬 Live Demonstration

### Demo Flow:

1️⃣ **Import Project**
   - Paste GitHub URL
   - Click "Clone & Analyze"

2️⃣ **View Tree Visualization**
   - Interactive zoom/pan
   - Click nodes for details

3️⃣ **View UML Diagrams**
   - Class diagrams
   - Dependency graphs

4️⃣ **AI Chat**
   - Ask: "What are the main components?"
   - Ask: "How does X work?"

---

# SLIDE 12: DEMO SCREENSHOTS

## 📸 CodeVision AI Interface

### [Screenshot 1: Main Dashboard]
- Upload panel on left
- Diagram view in center
- Detail panel on right

### [Screenshot 2: Tree Visualization]
- Interactive D3.js tree
- Zoom/pan controls
- Node details on click

### [Screenshot 3: UML Diagram]
- Class diagram with inheritance
- Methods and attributes shown

### [Screenshot 4: AI Chat]
- Question input
- Detailed AI response
- Full project context

---

# SLIDE 13: PROJECT STATISTICS

## 📈 What We Built

### Codebase Size:
| Component | Lines of Code |
|-----------|---------------|
| Backend (Python) | ~2,200 |
| Frontend (JS/HTML/CSS) | ~3,300 |
| **Total** | **~5,500** |

### Features:
| Metric | Count |
|--------|-------|
| API Endpoints | 9 |
| Languages Supported | 15+ |
| Diagram Formats | 4 |
| LLM Providers | 3 |

### Files:
- `backend/main.py` - 629 lines
- `llm/analyzer.py` - 814 lines
- `static/index.html` - 3,300+ lines
- `parsers/*.py` - 736 lines
- `visualization/diagram_generator.py` - 620 lines

---

# SLIDE 14: CHALLENGES & SOLUTIONS

## 🧩 Problems We Solved

### Challenge 1: Mermaid Syntax Errors
**Problem:** Special characters broke diagram rendering
**Solution:** Created `_sanitize_name()` function to clean all identifiers

### Challenge 2: LLM Context Limits
**Problem:** Large codebases exceeded token limits
**Solution:** Summarize and truncate intelligently, prioritize important info

### Challenge 3: Multi-Language Support
**Problem:** Each language has different syntax
**Solution:** AST for Python (accurate), Regex for others (flexible)

### Challenge 4: Real-time Updates
**Problem:** Browser caching showed old UI
**Solution:** Added no-cache headers, created `/app` endpoint

---

# SLIDE 15: FUTURE WORK

## 🚀 Roadmap

### Short-term:
- [ ] VS Code Extension
- [ ] More diagram types (Sequence diagrams)
- [ ] Export to PDF/PNG

### Long-term:
- [ ] RAG with vector database for huge codebases
- [ ] Git integration (analyze changes between commits)
- [ ] Collaborative features (share diagrams)
- [ ] Support for more languages

---

# SLIDE 16: REPOSITORY

## 📂 Source Code

### GitHub Repository:
# github.com/[your-username]/codevision-ai

### To Run Locally:
```bash
# Clone the repo
git clone https://github.com/[username]/codevision-ai.git

# Install dependencies
pip install -r requirements.txt

# Set up API key
echo "GOOGLE_API_KEY=your_key" > .env

# Run the server
python run.py

# Open http://localhost:8000
```

---

# SLIDE 17: SUMMARY

## 🎯 Key Takeaways

### What is CodeVision AI?
> An LLM-powered tool that helps developers understand unfamiliar codebases through visual diagrams and AI chat.

### Why is it better than general AI agents?
> Full project context, visual output, purpose-built for comprehension (not generation).

### How is it built?
> FastAPI backend + Vanilla JS frontend + LangChain/Gemini for AI + AST/Regex parsers

### Where can you find it?
> github.com/[your-username]/codevision-ai

---

# SLIDE 18: THANK YOU

## 🙏 Questions?

### Team:
- **Sri Bhuvan Maddipudi** (G01488473)
- **Srilakshmi Praharshitha Gatta** (G01475844)

### Contact:
- [Your Email]
- [Partner's Email]

### Repository:
**github.com/[your-username]/codevision-ai**

---

# END OF PRESENTATION

