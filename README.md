# 🤖 AI Chat Platform "Safe Space"

## Content of Project
* [General info](#-general-info)
* [Technologies](#-technologies)
* [Setup](#-setup)
* [More detailed information about modules](#-more-detailed-information-about-modules)
* [Application view](#-application-view)
* [Authors](#-authors)

---

## 📝 General info
This project is a modern, full-stack AI chat platform designed for a seamless user experience. **It was originally developed as a project for a Hackathon (Hacknarök)**, focusing on rapid deployment, high-performance message rendering, and a polished UI. It combines a Python backend with a reactive frontend, featuring rich text rendering, real-time animations, and built-in internationalization.

---

## 💻 Technologies
* **Frontend:** React 18, Vite, TypeScript
* **Styling:** Tailwind CSS, Shadcn/UI
* **Backend:** Python 3.10+, FastAPI
* **Containerization:** Docker & Docker Compose
* **Libraries:** React-Markdown, i18next (Multi-language support)

## ⚙️ Setup
To run this project locally using Docker:

```bash
# Sklonuj projekt
git clone [https://github.com/konszymanski/hacknarok-fiatpandas.git](https://github.com/konszymanski/hacknarok-fiatpandas.git)

# Wejdź do katalogu
cd hacknarok-fiatpandas

# Uruchom kontenery
docker-compose up --build
```

## 🔍 More detailed information about modules

### 🎨 Frontend Module (React & Vite)

* State Management: Efficient handling of chat history and user input using React hooks.

* Markdown Engine: Integrated react-markdown with remark-gfm to support GitHub-flavored markdown, including tables, task lists, and syntax highlighting for code blocks.

* Internationalization: Full i18next implementation allowing seamless switching between English and Polish.

* UI Components: Built using Shadcn/UI for a consistent and accessible design system.

### ⚙️ Backend Module (FastAPI)

* Asynchronous Logic: Utilizing Python's asyncio to handle multiple concurrent chat requests without blocking.

* API Architecture: RESTful endpoints for message processing, health checks, and language configuration.

* Security: CORS middleware configured for secure communication between the frontend and backend.

### 🤖 AI & Logic Integration

* Message Processing: Custom logic to simulate real-time AI "thinking" and streaming-like response delivery.

* Animation Triggers: Backend-controlled flags that trigger the frontend "shredding" effect for secure chat clearing.

## 🚀 Future Roadmap

* Scalability: Transitioning to a microservices architecture and implementing Redis for high-speed message caching.

* Monetization: Integrating Stripe API to support a "Pro" subscription model with advanced AI features.


## 👥 Authors

* Łukasz Spychała - Frontend  - https://github.com/Sercheedar

* Łukasz Całka - Backend - https://github.com/LukaszCalka1

* Tomasz Stępień - AI/ML - https://github.com/tomstepien

* Konrad Szymański - AI/ML - https://github.com/konszymanski

### Created with passion during a Hackathon challenge.
