# Blender Generative AI

Overview
This project bridges the gap between AI-driven processing and 3D workflows in Blender. It consists of a lightweight Blender Addon (UI/Toggle) and a standalone AI engine that performs 3D modeling tasks based on natural language input. It can autonomously create, edit, and delete objects within the scene.

Getting Started
System Requirements
Blender: v5.1+

GPU: Minimum 2GB VRAM

Python: v3.12+

Installation
Install dependencies:
pip install requests langgraph langchain-google-genai langchain-openai langchain-core langchain-huggingface langchain-community faiss-cpu

API Setup:
Add your necessary API keys (OpenAI or Google) to the configuration section in Generative Logic.py.

Install Blender Addon:
In Blender, go to Edit -> Preferences -> Add-ons -> Install and select the downloaded .py addon file.

Usage
Run the Server Python script.

Run the Generative Logic.py script.

In Blender, go to the Scene Properties tab, locate the Generative AI panel, and click "Connect to Server."

Customizations (Local AI)
If you prefer not to use paid API keys, you can run the project locally using Ollama:

Download Ollama from the official website: https://ollama.com

Install the local library: pip install langchain-ollama

In the code, replace ChatOpenAI or ChatGenerativeAI with ChatOllama.

License
This project is licensed under the GNU General Public License v3.0 (GPLv3).
