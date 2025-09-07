## Project Overview

This project is a desktop application named **MarkItDown**, designed to convert web articles into clean, readable Markdown files. It features a modern graphical user interface (GUI) built with **Python** and the **PySide6** (Qt) framework.

The application's core functionality is to fetch content from a given URL, extract the main article, convert it from HTML to Markdown, and save it locally. It includes advanced features like batch processing, session management (saving/loading URL lists and settings), and optional image downloading.

The architecture is modular and extensible:

*   **UI Layer (`markitdown_app/ui`):** A PySide6-based GUI that is decoupled from the core logic via a ViewModel (`viewmodel.py`). It supports internationalization with English and Chinese locales.
*   **Service Layer (`markitdown_app/services`):** The `convert_service.py` orchestrates the conversion process in a background thread to keep the UI responsive.
*   **Core Logic (`markitdown_app/core`):**
    *   A **handler registry** (`registry.py`) acts as a dispatcher, routing URLs to the appropriate handler.
    *   **Specialized handlers** exist for complex websites like WeChat (`weixin_handler.py`), Zhihu (`zhihu_handler.py`), and WordPress (`wordpress_handler.py`).
    *   A **generic handler** (`generic_handler.py`) provides a fallback for any other website.
    *   The crawling mechanism is multi-strategy, using **Playwright**, **httpx**, and **requests** to maximize success rates against anti-bot measures.
    *   The final HTML-to-Markdown conversion is handled by `html_to_md.py`.
*   **I/O and Configuration (`markitdown_app/io`):** Manages configuration, session data, and writing files to disk.

## Building and Running

### Prerequisites

*   Python 3.10+
*   A virtual environment (recommended)

### Installation

1.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Install Playwright browsers:**
    This step is required for the advanced crawling features to work correctly, especially for sites with heavy anti-bot protection.
    ```bash
    playwright install
    ```

### Running the Application

The application is designed to be run directly from the file explorer.

1.  Navigate to the project's root directory.
2.  Double-click the **`MarkItDown.vbs`** script.

This will launch the GUI application. Alternatively, you can run the main entry point directly:

```bash
python MarkURLdown.pyw
```

### Running Tests

The project contains a `tests` directory with unit and integration tests. While a specific test runner is not explicitly defined in the project files, `pytest` is a common choice for Python projects. To run tests, you would typically execute:

```bash
# TODO: Confirm the exact test command.
pytest
```

## Development Conventions

*   **Architecture:** The project follows a Model-View-ViewModel (MVVM) like pattern, with a clear separation between the UI (`ui`), business logic (`services`), and core functionalities (`core`).
*   **Modularity:** The handler system in `core/registry.py` is designed for easy extension. To add support for a new website, a developer can create a new handler function and add it to the `HANDLERS` list.
*   **Error Handling:** Handlers are designed to fail gracefully. If a specialized handler fails or determines it cannot process a URL, it returns `None`, allowing the registry to fall back to the generic handler.
*   **Concurrency:** The UI remains responsive during conversions by running the main processing loop in a separate thread (`threading.Thread` in `convert_service.py`). Progress is reported back to the UI using a callback system with `ProgressEvent` objects.
*   **Coding Style:** The code generally follows standard Python conventions (PEP 8). It uses type hints (`from __future__ import annotations`) for improved code clarity and maintainability.
*   **Dependencies:** Key dependencies are managed in `requirements.txt`. The project leverages modern libraries like `PySide6`, `httpx`, and `Playwright`.
