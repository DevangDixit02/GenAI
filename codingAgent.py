import os
import json
import re
import shutil
from dotenv import load_dotenv
from google import genai
from google.genai import types
import subprocess
import requests
import sqlite3
from pathlib import Path
import time

load_dotenv()

# === Gemini Client ===
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# === Tool Definitions ===
def run_command(command: str):
    """Run a shell command and return the output."""
    try:
        print(f"\n📋 Running command: {command}")
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(timeout=60)
        
        if process.returncode != 0:
            return f"[ERROR] Command failed with exit code {process.returncode}:\n{stderr}"
        
        return stdout.strip()
    except subprocess.TimeoutExpired:
        process.kill()
        return "[ERROR] Command timed out after 60 seconds"
    except Exception as e:
        return f"[ERROR] Exception during command execution: {str(e)}"


def create_folder_structure(structure, base_path="."):
    """Create a folder structure from a nested dictionary."""
    if isinstance(structure, str):
        try:
            structure = json.loads(structure)
        except json.JSONDecodeError:
            return "[ERROR] Invalid JSON format for folder structure"
    
    created_items = []
    try:
        for name, content in structure.items():
            path = os.path.join(base_path, name)
            if isinstance(content, dict):  # folder
                os.makedirs(path, exist_ok=True)
                created_items.append(f"[DIR] {path}")
                sub_items = create_folder_structure(content, path)
                if isinstance(sub_items, list):
                    created_items.extend(sub_items)
                else:
                    created_items.append(sub_items)
            else:  # file
                directory = os.path.dirname(path)
                if directory:
                    os.makedirs(directory, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                created_items.append(f"[FILE] {path}")
        
        if isinstance(base_path, str) and base_path == ".":
            return created_items
        return "\n".join(created_items) if created_items else "No items created"
    except Exception as e:
        return f"[ERROR] Failed to create folder structure: {str(e)}"


def read_folder_structure(base_path=".", max_depth=5, excluded_dirs=None):
    """Read the folder structure recursively from a base path."""
    if excluded_dirs is None:
        excluded_dirs = ["node_modules", "__pycache__", ".git", "venv", "env"]
    
    try:
        structure = {}
        base_path = os.path.abspath(base_path)
        
        for root, dirs, files in os.walk(base_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            
            # Check depth
            rel_path = os.path.relpath(root, base_path)
            depth = len(rel_path.split(os.sep)) if rel_path != "." else 0
            if depth > max_depth:
                continue
                
            current = structure
            if rel_path != ".":
                for part in rel_path.split(os.sep):
                    current = current.setdefault(part, {})
                    
            for file in files:
                # Skip large files (>1MB)
                file_path = os.path.join(root, file)
                if os.path.getsize(file_path) > 1_000_000:
                    current[file] = "[FILE TOO LARGE]"
                    continue
                    
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    current[file] = content
                except Exception:
                    current[file] = "[UNREADABLE]"
                    
        return structure
    except Exception as e:
        return f"[ERROR] Failed to read folder structure: {str(e)}"


def read_file(file_path):
    """Read the content of a specific file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        return content
    except UnicodeDecodeError:
        return "[ERROR] File contains binary content that cannot be read as text"
    except FileNotFoundError:
        return f"[ERROR] File not found: {file_path}"
    except Exception as e:
        return f"[ERROR] Could not read file: {str(e)}"


def write_file(file_path, content=""):
    """Write content to a specific file."""
    try:
        # Handle JSON input
        if isinstance(file_path, dict) or (isinstance(file_path, str) and file_path.startswith("{")):
            try:
                if isinstance(file_path, str):
                    params = json.loads(file_path)
                else:
                    params = file_path
                file_path = params.get("file_path", "")
                content = params.get("content", "")
            except json.JSONDecodeError:
                pass  # Fall back to using file_path and content as is
            
        if not file_path:
            return "[ERROR] No file path provided"
            
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
            
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
            
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"[ERROR] Could not write to file: {str(e)}"


def search_files(pattern, file_type="", base_path=".", max_results=20):
    """Search for files containing a specific pattern."""
    try:
        # Handle JSON input
        if isinstance(pattern, dict) or isinstance(pattern, str) and pattern.startswith("{"):
            try:
                if isinstance(pattern, str):
                    params = json.loads(pattern)
                else:
                    params = pattern
                pattern = params.get("pattern", "")
                file_type = params.get("file_type", "")
                base_path = params.get("base_path", ".")
                max_results = params.get("max_results", 20)
            except json.JSONDecodeError:
                pass  # Fall back to using pattern as a string
                
        matched_files = {}
        count = 0
        
        for root, _, files in os.walk(base_path):
            for file in files:
                if count >= max_results:
                    break
                    
                if file_type and not file.endswith(file_type):
                    continue
                    
                file_path = os.path.join(root, file)
                
                # Skip large files
                try:
                    if os.path.getsize(file_path) > 1_000_000:
                        continue
                        
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if re.search(pattern, content, re.IGNORECASE):
                            # Find matching lines for context
                            lines = content.split('\n')
                            matched_lines = {}
                            for i, line in enumerate(lines):
                                if re.search(pattern, line, re.IGNORECASE):
                                    start = max(0, i - 2)
                                    end = min(len(lines), i + 3)
                                    context = '\n'.join(lines[start:end])
                                    matched_lines[f"Line {i+1}"] = context
                            
                            matched_files[file_path] = matched_lines
                            count += 1
                except:
                    pass
                    
        return matched_files
    except Exception as e:
        return f"[ERROR] Failed to search files: {str(e)}"


def install_dependencies(packages, manager="npm"):
    """Install dependencies using the specified package manager."""
    try:
        # Handle JSON input
        if isinstance(packages, dict) or isinstance(packages, str) and packages.startswith("{"):
            try:
                if isinstance(packages, str):
                    params = json.loads(packages)
                else:
                    params = packages
                packages = params.get("packages", "")
                manager = params.get("manager", "npm")
            except json.JSONDecodeError:
                pass  # Fall back to using packages as a string
                
        managers = {
            "npm": "npm install",
            "yarn": "yarn add",
            "pip": "pip install",
            "pipenv": "pipenv install",
            "composer": "composer require",
        }
        
        if manager not in managers:
            return f"[ERROR] Unsupported package manager: {manager}"
        
        command = f"{managers[manager]} {packages}"
        return run_command(command)
    except Exception as e:
        return f"[ERROR] Failed to install dependencies: {str(e)}"


def initialize_project(project_type, project_name):
    """Initialize a new project with boilerplate code."""
    try:
        # Handle JSON input
        if isinstance(project_type, dict) or isinstance(project_type, str) and project_type.startswith("{"):
            try:
                if isinstance(project_type, str):
                    params = json.loads(project_type)
                else:
                    params = project_type
                project_type = params.get("project_type", "")
                project_name = params.get("project_name", "")
            except json.JSONDecodeError:
                pass  # Fall back to using project_type as a string
                
        project_types = {
            "react": f"npx create-react-app {project_name}",
            "next": f"npx create-next-app {project_name}",
            "vue": f"npm init vue@latest {project_name}",
            "express": f"npx express-generator {project_name}",
            "django": f"django-admin startproject {project_name}",
            "flask": f"mkdir {project_name} && cd {project_name} && echo \"from flask import Flask\\n\\napp = Flask(__name__)\\n\\n@app.route('/')\\ndef home():\\n    return 'Hello, World!'\\n\\nif __name__ == '__main__':\\n    app.run(debug=True)\" > app.py",
            "vite-react": f"npm create vite@latest {project_name} -- --template react",
            "vite-vue": f"npm create vite@latest {project_name} -- --template vue",
            "vite-svelte": f"npm create vite@latest {project_name} -- --template svelte",
        }
        
        if project_type not in project_types:
            return f"[ERROR] Unsupported project type: {project_type}. Available types: {', '.join(project_types.keys())}"
        
        return run_command(project_types[project_type])
    except Exception as e:
        return f"[ERROR] Failed to initialize project: {str(e)}"


def run_dev_server(command, directory="."):
    """Run a development server in the background."""
    try:
        # Handle JSON input
        if isinstance(command, dict) or isinstance(command, str) and command.startswith("{"):
            try:
                if isinstance(command, str):
                    params = json.loads(command)
                else:
                    params = command
                command = params.get("command", "")
                directory = params.get("directory", ".")
            except json.JSONDecodeError:
                pass  # Fall back to using command as a string
                
        if not command:
            return "[ERROR] No command provided"
            
        current_dir = os.getcwd()
        try:
            os.chdir(directory)
            
            # For Windows
            if os.name == 'nt':
                process = subprocess.Popen(f"start cmd /k {command}", shell=True)
            # For Unix-like systems
            else:
                process = subprocess.Popen(f"{command} &", shell=True)
                
            os.chdir(current_dir)
            time.sleep(2)  # Give the server a moment to start
            return f"Development server started with command: {command} in directory: {directory}"
        except Exception as e:
            os.chdir(current_dir)
            return f"[ERROR] Failed to start dev server: {str(e)}"
    except Exception as e:
        return f"[ERROR] Failed to parse parameters: {str(e)}"


def fetch_api_data(url, method="GET", headers=None, data=None):
    """Fetch data from an API endpoint."""
    try:
        # Handle JSON input
        if isinstance(url, dict) or isinstance(url, str) and url.startswith("{"):
            try:
                if isinstance(url, str):
                    params = json.loads(url)
                else:
                    params = url
                url = params.get("url", "")
                method = params.get("method", "GET")
                headers = params.get("headers", None)
                data = params.get("data", None)
            except json.JSONDecodeError:
                pass  # Fall back to using url as a string
                
        if not url:
            return "[ERROR] No URL provided"
            
        if headers is None:
            headers = {}
        
        timeout = 10  # seconds
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=timeout)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=timeout)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=timeout)
        else:
            return f"[ERROR] Unsupported HTTP method: {method}"
        
        try:
            content_json = response.json()
            content = content_json
        except:
            content = response.text
            
        return {
            "status_code": response.status_code,
            "content": content,
            "headers": dict(response.headers)
        }
    except requests.exceptions.Timeout:
        return "[ERROR] Request timed out"
    except requests.exceptions.ConnectionError:
        return "[ERROR] Connection error"
    except Exception as e:
        return f"[ERROR] Failed to fetch data: {str(e)}"


def deploy_static_site(directory, platform="netlify"):
    """Deploy a static site to a hosting platform."""
    try:
        # Handle JSON input
        if isinstance(directory, dict) or isinstance(directory, str) and directory.startswith("{"):
            try:
                if isinstance(directory, str):
                    params = json.loads(directory)
                else:
                    params = directory
                directory = params.get("directory", "")
                platform = params.get("platform", "netlify")
            except json.JSONDecodeError:
                pass  # Fall back to using directory as a string
                
        if not directory:
            return "[ERROR] No directory provided"
            
        platforms = {
            "netlify": "npx netlify-cli deploy",
            "vercel": "npx vercel",
            "github-pages": "gh-pages -d .",
            "surge": "npx surge",
        }
        
        if platform not in platforms:
            return f"[ERROR] Unsupported platform: {platform}. Available platforms: {', '.join(platforms.keys())}"
        
        current_dir = os.getcwd()
        try:
            os.chdir(directory)
            result = run_command(platforms[platform])
            os.chdir(current_dir)
            return result
        except Exception as e:
            os.chdir(current_dir)
            return f"[ERROR] Deployment failed: {str(e)}"
    except Exception as e:
        return f"[ERROR] Failed to parse parameters: {str(e)}"


def create_database(db_name, schema):
    """Create an SQLite database with the specified schema."""
    try:
        # Handle JSON input
        if isinstance(db_name, dict) or isinstance(db_name, str) and db_name.startswith("{"):
            try:
                if isinstance(db_name, str):
                    params = json.loads(db_name)
                else:
                    params = db_name
                db_name = params.get("db_name", "")
                schema = params.get("schema", "")
            except json.JSONDecodeError:
                pass  # Fall back to using db_name as a string
                
        if not db_name:
            return "[ERROR] No database name provided"
            
        if not schema:
            return "[ERROR] No schema provided"
            
        if not db_name.endswith('.db'):
            db_name += '.db'
            
        try:
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            
            # Execute the schema SQL
            cursor.executescript(schema)
            
            conn.commit()
            conn.close()
            
            return f"Database {db_name} created successfully with the provided schema"
        except sqlite3.Error as e:
            return f"[ERROR] SQLite error: {str(e)}"
    except Exception as e:
        return f"[ERROR] Failed to create database: {str(e)}"


def query_database(db_name, query, parameters=None):
    """Execute a query on an SQLite database."""
    try:
        # Handle JSON input
        if isinstance(db_name, dict) or isinstance(db_name, str) and db_name.startswith("{"):
            try:
                if isinstance(db_name, str):
                    params = json.loads(db_name)
                else:
                    params = db_name
                db_name = params.get("db_name", "")
                query = params.get("query", "")
                parameters = params.get("parameters", None)
            except json.JSONDecodeError:
                pass  # Fall back to using db_name as a string
                
        if not db_name:
            return "[ERROR] No database name provided"
            
        if not query:
            return "[ERROR] No query provided"
            
        if not db_name.endswith('.db'):
            db_name += '.db'
            
        if not os.path.exists(db_name):
            return f"[ERROR] Database {db_name} does not exist"
            
        try:
            conn = sqlite3.connect(db_name)
            conn.row_factory = sqlite3.Row  # This enables column access by name
            cursor = conn.cursor()
            
            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)
                
            if query.strip().upper().startswith(("SELECT", "PRAGMA")):
                columns = [description[0] for description in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                conn.close()
                return {"rows": results, "row_count": len(results)}
            else:
                affected_rows = cursor.rowcount
                conn.commit()
                conn.close()
                return {"affected_rows": affected_rows, "message": "Query executed successfully"}
        except sqlite3.Error as e:
            return f"[ERROR] SQLite error: {str(e)}"
    except Exception as e:
        return f"[ERROR] Failed to query database: {str(e)}"


# === Tool Registry ===
available_tools = {
    "run_command": {
        "fn": run_command,
        "description": "Runs a shell command and returns the output",
    },
    "create_folder_structure": {
        "fn": create_folder_structure,
        "description": "Creates folders/files from a nested dictionary",
    },
    "read_folder_structure": {
        "fn": read_folder_structure,
        "description": "Reads the folder/file structure recursively",
    },
    "read_file": {
        "fn": read_file,
        "description": "Reads the content of a specific file",
    },
    "write_file": {
        "fn": write_file,
        "description": "Writes content to a specific file",
    },
    "search_files": {
        "fn": search_files,
        "description": "Searches for files containing a specific pattern",
    },
    "install_dependencies": {
        "fn": install_dependencies,
        "description": "Installs dependencies using the specified package manager",
    },
    "initialize_project": {
        "fn": initialize_project,
        "description": "Initializes a new project with boilerplate code",
    },
    "run_dev_server": {
        "fn": run_dev_server,
        "description": "Runs a development server in the background",
    },
    "fetch_api_data": {
        "fn": fetch_api_data,
        "description": "Fetches data from an API endpoint",
    },
    "deploy_static_site": {
        "fn": deploy_static_site,
        "description": "Deploys a static site to a hosting platform",
    },
    "create_database": {
        "fn": create_database,
        "description": "Creates an SQLite database with the specified schema",
    },
    "query_database": {
        "fn": query_database,
        "description": "Executes a query on an SQLite database",
    },
}

# === System Prompt ===
system_prompt = """
    You are an expert fullstack developer AI Assistant specializing in building complete web applications.
    You work in a structured PLAN → ACTION → OBSERVE → OUTPUT mode.
    
    For user queries, you'll plan a step-by-step execution, select the appropriate tool, perform the action,
    observe the results, and provide a meaningful response.

    Your specialties include:
    - Frontend development (React, Vue, Angular, Next.js)
    - Backend development (Node.js/Express, Django, Flask)
    - Database design and implementation (SQL, NoSQL)
    - API development and integration
    - DevOps and deployment workflows
    - UI/UX best practices
    - Modern web development patterns

    Your job is to:
    - Understand user requirements and break them down into logical tasks
    - Plan comprehensive solutions step-by-step
    - Generate production-ready code with best practices
    - Create database schemas and API endpoints
    - Set up proper project structures with necessary configurations
    - Implement responsive and accessible UI components
    - Handle state management, authentication, and authorization
    - Optimize for performance and security
    - Support continuous development in ongoing sessions

    ---

    🧠 AVAILABLE TOOLS:
    - run_command: Runs a shell command and returns the output
    - create_folder_structure: Creates folders/files from a nested dictionary
    - read_folder_structure: Reads the folder/file structure recursively
    - read_file: Reads the content of a specific file
    - write_file: Writes content to a specific file. Use one of these formats:
        1. JSON: {"file_path": "path/to/file.js", "content": "file content here"}
        2. Split format: "path/to/file.js|||file content here"
    - search_files: Searches for files containing a specific pattern
    - install_dependencies: Installs dependencies using a package manager. Use one of these formats:
        1. JSON: {"packages": "react react-dom", "manager": "npm"}
        2. Simple format: "react react-dom"
        3. With manager: "react react-dom --manager=yarn"
    - initialize_project: Initializes a new project with boilerplate code. Use one of these formats:
        1. JSON: {"project_type": "react", "project_name": "my-app"}
        2. Simple format: "react my-app"
    - run_dev_server: Runs a development server in the background
    - fetch_api_data: Fetches data from an API endpoint
    - deploy_static_site: Deploys a static site to a hosting platform
    - create_database: Creates an SQLite database with the specified schema
    - query_database: Executes a query on an SQLite database

    🧠 WORKFLOW:
    You work in a structured cycle:
    **PLAN → ACTION → OBSERVE → (think again if needed) → OUTPUT**

    Each step must respond in **JSON** with the following format:

    ```json
    {
      "step": "plan" | "action" | "output",
      "content": "Explanation of what you're doing, what you observed, or what you're generating",
      "function": "optional if step is 'action'",
      "input": "string input to the function"
    }
    ```

    💻 EXAMPLES OF TASKS YOU CAN HELP WITH:
    - "Create a full-stack MERN app with authentication"
    - "Set up a Next.js project with Tailwind CSS and TypeScript"
    - "Build me a Django REST API for a blog with user comments"
    - "Create a Vue 3 dashboard with Pinia state management"
    - "Add a login system to my React application"
    - "Create a SQLite database for my todo app"
    - "Set up a PostgreSQL database schema for an e-commerce site"
    
    📝 EXAMPLES OF TOOL USAGE:

    1. Using write_file with JSON format:
    {
      "step": "action",
      "function": "write_file",
      "content": "Creating a React component",
      "input": "{\"file_path\": \"src/components/Button.jsx\", \"content\": \"import React from 'react';\\n\\nconst Button = ({ label, onClick }) => {\\n  return (\\n    <button onClick={onClick}>{label}</button>\\n  );\\n};\\n\\nexport default Button;\"}"
    }

    2. Using write_file with split format:
    {
      "step": "action", 
      "function": "write_file",
      "content": "Creating a utility function",
      "input": "src/utils/format.js|||export const formatDate = (date) => {\\n  return new Date(date).toLocaleDateString();\\n};"
    }
    
    3. Using initialize_project with JSON format:
    {
      "step": "action",
      "function": "initialize_project",
      "content": "Creating a new React application",
      "input": "{\"project_type\": \"react\", \"project_name\": \"my-react-app\"}"
    }
    
    4. Using initialize_project with simple format:
    {
      "step": "action",
      "function": "initialize_project",
      "content": "Creating a new React application",
      "input": "react my-react-app"
    }
    
    5. Using install_dependencies with JSON format:
    {
      "step": "action",
      "function": "install_dependencies",
      "content": "Installing React and React DOM",
      "input": "{\"packages\": \"react react-dom\", \"manager\": \"npm\"}"
    }
    
    6. Using install_dependencies with simple format:
    {
      "step": "action",
      "function": "install_dependencies",
      "content": "Installing React and React DOM",
      "input": "react react-dom"
    }
"""


# === Interactive Agent Loop ===
def main():
    messages = [types.Content(role="user", parts=[{"text": system_prompt}])]

    print("\n🤖 Fullstack Developer Coding Agent initialized!")
    print("🚀 How can I help you build your application today?")

    while True:
        try:
            user_query = input("\n🧑‍💻 You: ")
            if user_query.lower() in ['exit', 'quit', 'bye']:
                print("\n👋 Thank you for using the Fullstack Developer Coding Agent. Goodbye!")
                break
                
            messages.append(types.Content(role="user", parts=[{"text": user_query}]))

            while True:
                try:
                    response = client.models.generate_content(
                        model="gemini-2.0-flash-001",
                        contents=messages,
                        config=types.GenerateContentConfig(
                            temperature=0.6,
                            max_output_tokens=8192,
                            response_mime_type="application/json",
                        ),
                    )

                    response_text = response.candidates[0].content.parts[0].text
                    res_json = json.loads(response_text)
                    step = res_json["step"].lower()

                    messages.append(
                        types.Content(role="assistant", parts=[{"text": json.dumps(res_json)}])
                    )

                    if step == "plan":
                        print(f"\n🧠 PLAN: {res_json['content']}")
                        continue

                    elif step == "action":
                        tool_name = res_json["function"]
                        tool_input = res_json["input"]

                        if tool_name in available_tools:
                            print(f"\n⚙️ ACTION: Calling {tool_name}...")
                            try:
                                result = None
                                
                                # Special handling for write_file
                                if tool_name == "write_file":
                                    try:
                                        # Try parsing as JSON first
                                        params = json.loads(tool_input)
                                        if "file_path" in params and "content" in params:
                                            file_path = params["file_path"]
                                            content = params["content"]
                                            result = write_file(file_path, content)
                                        else:
                                            result = write_file(tool_input)
                                    except json.JSONDecodeError:
                                        # If not JSON, try to extract file_path and content
                                        parts = tool_input.split("|||", 1)
                                        if len(parts) == 2:
                                            file_path, content = parts
                                            result = write_file(file_path.strip(), content)
                                        else:
                                            result = f"[ERROR] Invalid input format for write_file. Expected JSON or 'file_path|||content'"
                                
                                # Special handling for create_folder_structure
                                elif tool_name == "create_folder_structure":
                                    try:
                                        structure = json.loads(tool_input)
                                        result = create_folder_structure(structure)
                                    except json.JSONDecodeError:
                                        result = f"[ERROR] Invalid JSON structure: {tool_input}"
                                
                                # Special handling for initialize_project
                                elif tool_name == "initialize_project":
                                    try:
                                        # Parse as JSON if possible
                                        try:
                                            params = json.loads(tool_input)
                                            if isinstance(params, dict):
                                                if "project_type" in params and "project_name" in params:
                                                    result = initialize_project(
                                                        project_type=params.get("project_type"),
                                                        project_name=params.get("project_name")
                                                    )
                                                else:
                                                    result = f"[ERROR] Missing required parameters for initialize_project. Need project_type and project_name."
                                            else:
                                                result = f"[ERROR] Invalid format for initialize_project parameters."
                                        except json.JSONDecodeError:
                                            # If not JSON, try to extract parameters
                                            parts = tool_input.split(" ", 1)
                                            if len(parts) == 2:
                                                project_type, project_name = parts
                                                result = initialize_project(
                                                    project_type=project_type.strip(),
                                                    project_name=project_name.strip()
                                                )
                                            else:
                                                result = f"[ERROR] Invalid input format for initialize_project. Expected 'project_type project_name' or JSON."
                                    except Exception as e:
                                        result = f"[ERROR] Failed to initialize project: {str(e)}"
                                
                                # Special handling for install_dependencies
                                elif tool_name == "install_dependencies":
                                    try:
                                        # Parse as JSON if possible
                                        try:
                                            params = json.loads(tool_input)
                                            if isinstance(params, dict):
                                                packages = params.get("packages", "")
                                                manager = params.get("manager", "npm")
                                                result = install_dependencies(
                                                    packages=packages,
                                                    manager=manager
                                                )
                                            else:
                                                result = install_dependencies(tool_input)
                                        except json.JSONDecodeError:
                                            # If not JSON, try to extract parameters
                                            if " --manager=" in tool_input:
                                                parts = tool_input.split(" --manager=", 1)
                                                packages = parts[0].strip()
                                                manager = parts[1].strip()
                                                result = install_dependencies(packages, manager)
                                            else:
                                                result = install_dependencies(tool_input)
                                    except Exception as e:
                                        result = f"[ERROR] Failed to install dependencies: {str(e)}"
                                
                                # Handle other tools
                                else:
                                    result = available_tools[tool_name]["fn"](tool_input)
                                    
                            except Exception as e:
                                result = f"[ERROR] Exception during tool execution: {str(e)}"

                            obs = {"step": "observe", "output": result}
                            messages.append(
                                types.Content(role="user", parts=[{"text": json.dumps(obs)}])
                            )
                            
                            # Format the observation output for better readability
                            if isinstance(result, dict):
                                formatted_result = json.dumps(result, indent=2)
                                preview = formatted_result[:500] + ('...' if len(formatted_result) > 500 else '')
                            else:
                                result_str = str(result)
                                preview = result_str[:500] + ('...' if len(result_str) > 500 else '')
                                
                            print(f"\n🔍 OBSERVATION: {preview}")
                            continue
                        else:
                            print(f"\n[ERROR] Unknown tool: {tool_name}")
                            break

                    elif step == "output":
                        print(f"\n🤖 OUTPUT: {res_json['content']}")
                        break

                    else:
                        print(f"\n[WARNING] Unknown step: {step}")
                        break
                        
                except json.JSONDecodeError:
                    print("\n[ERROR] Received invalid JSON response from the model. Retrying...")
                    continue
                except Exception as e:
                    print(f"\n[ERROR] Error during API call: {str(e)}")
                    break
                    
        except KeyboardInterrupt:
            print("\n\n👋 Agent execution interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
