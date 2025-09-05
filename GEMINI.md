# Project: MarkItDown

## Project Overview

This project, "MarkItDown," is a desktop application for Windows designed to convert web articles into clean, readable Markdown files. It features a graphical user interface (GUI) and supports batch conversions, image downloading, and handling for specific complex websites like WeChat articles.

The application is built with Python and offers two GUI implementations:
*   **PySide6:** A modern, feature-rich UI which is the primary interface for the application.
*   **Tkinter:** A more basic, alternative UI.

The architecture is modular, separating concerns into different packages:
*   `markitdown_app/core`: Handles the core logic of HTML to Markdown conversion, image processing, and filename generation. It utilizes the `MarkItDown` and `BeautifulSoup4` libraries.
*   `markitdown_app/services`: Manages the conversion process in a background thread to keep the UI responsive.
*   `markitdown_app/io`: Deals with file I/O, including configuration management (`setting.json`) and logging.
*   `markitdown_app/ui`: Contains the UI code, with sub-packages for `pyside` and `tkinter`. It uses a ViewModel (`viewmodel.py`) to decouple the UI from the application's business logic.
*   `markitdown_app/types`: Defines custom data types and structures used throughout the application.

## Building and Running

### Dependencies

The project's Python dependencies are listed in `requirements.txt`. They can be installed using pip:

```bash
pip install -r requirements.txt
```

### Running the Application

There are several ways to run the application:

1.  **VBScript (Recommended for end-users):**
    The `MarkItDown.vbs` script is the intended way to launch the application without a console window. It activates the specified Conda environment and then executes the main application script.

    *Before running, you may need to configure the `condaPath` and `condaEnvName` variables inside `MarkItDown.vbs`.*

2.  **PySide6 GUI (Main application):**
    To run the main PySide6 application directly, use the following command:

    ```bash
    pythonw MarkURLdown.pyw
    ```
    or
    ```bash
    python markitdown_app/app/main_pyside.py
    ```

3.  **Tkinter GUI (Alternative):**
    To run the Tkinter version of the application, use this command:

    ```bash
    python markitdown_app/app/main_tk.py
    ```

## Development Conventions

*   **GUI:** The primary and most feature-complete GUI is implemented using PySide6. The Tkinter version serves as a fallback or alternative.
*   **Modularity:** The code is organized into distinct modules for UI, core logic, services, and I/O.
*   **ViewModel:** A ViewModel pattern is used to separate UI logic from the core business logic, allowing for easier maintenance and testing.
*   **Concurrency:** Long-running tasks, such as converting multiple URLs, are executed in a separate thread to prevent the GUI from freezing.
*   **Configuration:** Application settings and URL lists can be imported and exported as JSON files. A default `setting.json` file can be placed in the project root for development.
*   **Entry Points:** The main entry point for the PySide6 application is `MarkURLdown.pyw`, which also handles the display of a splash screen.
