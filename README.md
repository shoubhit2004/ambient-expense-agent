# 💰 Ambient Expense Agent using Google ADK 2.0

An AI-powered expense approval workflow built using **Google Agent Development Kit (ADK) 2.0** and **Gemini**. The agent automatically approves low-value expense claims and routes higher-value claims to a **Human-in-the-Loop (HITL)** approval workflow using a graph-based architecture.

> **Project Context**
>
> This project was built during **Kaggle's 5-Day Intensive Vibe Coding: Building 10x AI Agents** course by Google. The project was created using a **vibe coding workflow** with Antigravity IDE and Google Agents CLI while learning the Google ADK ecosystem.
>
> The objective of this project was to understand:
> - Google ADK 2.0
> - Graph-based AI Workflows
> - Human-in-the-Loop Agents
> - Gemini-powered AI Agents
> - AI Agent development lifecycle

---

# 🚀 Features

- 🤖 Google ADK 2.0 Graph Workflow
- 🧠 Gemini-powered Expense Information Extraction
- 💵 Automatic approval for expenses below **$100**
- 👨‍💼 Human-in-the-Loop review for expenses **$100 and above**
- 🔄 Resumable workflow using `RequestInput`
- 📋 Structured outputs using Pydantic Models
- ✅ Local testing using ADK Web UI

---

# 🏗 Workflow

```text
User Expense

        │
        ▼

 Gemini Extractor Agent

        │
        ▼

 Expense Classifier

      /       \

< $100      >= $100

   │             │

Auto          Human Review

Approve       (RequestInput)

      \       /

        ▼

 Final Decision
```

---

# 🛠 Tech Stack

- Python
- Google ADK 2.0
- Google Gemini
- Google Agents CLI
- Pydantic
- FastAPI (ADK Runtime)
- Antigravity IDE

---

# 📂 Project Structure

```
ambient-expense-agent
│
├── app
│   ├── agent.py
│   ├── __init__.py
│   └── app_utils
│
├── deployment
├── tests
├── README.md
├── pyproject.toml
└── uv.lock
```

---

# 🧠 How it Works

### Step 1

The user submits an expense in natural language.

Example:

```
I had lunch with a client yesterday. The expense was $45.
```

---

### Step 2

Gemini extracts structured information:

```json
{
  "amount": 45,
  "description": "Lunch with client"
}
```

---

### Step 3

The classifier evaluates the amount.

- Expense < $100 → Auto Approved
- Expense ≥ $100 → Manual Review

---

### Step 4

For higher-value claims, the workflow pauses and requests human approval using **RequestInput**.

---

### Step 5

The workflow resumes and returns the final approval or rejection.

---

# 📸 Screenshots

Add your screenshots here.

# ▶️ Running the Project

Clone the repository

```bash
git clone <your-repository-url>
```

Navigate into the project

```bash
cd ambient-expense-agent
```

Install dependencies

```bash
uv sync
```

Set your Gemini API Key

Create a `.env` file:

```env
GOOGLE_API_KEY=YOUR_API_KEY
```

Run the application

```bash
uv run adk web
```

Open:

```
http://127.0.0.1:8000
```

---

# 🧪 Example Test Cases

### Auto Approval

Input

```
I had lunch with a client yesterday. The expense was $45.
```

Result

```
APPROVED
```

---

### Human Review

Input

```
Business trip hotel cost $250.
```

Result

```
Manager Approval Required
```

Manager

```
yes
```

Final

```
APPROVED
```

---

# 📚 Learning Outcomes

Through this project I learned:

- Building AI Agents with Google ADK 2.0
- Designing Graph-based Agent Workflows
- Human-in-the-Loop AI Systems
- Gemini Integration
- Prompt-driven AI Development
- AI Agent Testing using ADK Web

---

# 📌 Notes

This project was created as part of the **Kaggle 5-Day Intensive Vibe Coding: Building 10x AI Agents** course.

The implementation was generated using a **vibe coding workflow** with Antigravity IDE and Google Agents CLI as part of the learning experience. The project was then configured, executed, debugged, tested, and validated locally to understand the complete AI agent development workflow.

---

# 📄 License

This project is intended for educational and portfolio purposes.
