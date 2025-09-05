# MarkItDown

MarkItDown is a user-friendly desktop application designed to effortlessly convert web articles into clean, readable Markdown files. It's perfect for archiving content, creating a personal knowledge base, or preparing articles for publishing on platforms like Hugo, Jekyll, or Hexo.

## Features

*   **Modern & Intuitive GUI:** A clean and simple graphical interface built with PySide6.
*   **Batch Conversion:** Convert multiple URLs in a single session.
*   **Smart Content Extraction:** Intelligently cleans up clutter like ads, navigation bars, and footers to grab only the main article content.
*   **Image Handling:** Optionally downloads all images from the article and saves them locally for a complete, offline-first archive.
*   **Specialized Site Handling:** Includes custom logic to properly handle complex page structures, such as WeChat official account articles.
*   **Splash Screen:** A professional launch experience while the application loads.
*   **Console-Free Launch:** Starts directly as a GUI application without a command prompt window.

## Installation

To set up the project locally, you will need a working Conda installation.

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd Markitdown
    ```

2.  **Create and activate the Conda environment:**
    ```bash
    conda create --name markitdown python=3.10 -y
    conda activate markitdown
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Once installed, you can launch the application without needing to open a command line.

1.  Navigate to the project directory in your file explorer.
2.  Double-click the **`MarkItDown.vbs`** file.
3.  The application will start with a splash screen and then show the main window.

**How to convert:**
1.  Paste a URL into the top input field and click "Add +".
2.  Add as many URLs as you need to the list.
3.  Choose your desired output directory.
4.  Select options like "Download Images".
5.  Click the "Convert to Markdown" button to begin.

## Acknowledgements

This project stands on the shoulders of giants. We would like to thank the developers of these outstanding open-source libraries:

*   **PySide6:** For the powerful and modern GUI framework.
*   **Requests:** For robust and simple HTTP requests.
*   **BeautifulSoup4:** For its excellence in parsing and navigating HTML.
*   **MarkItDown:** For the core Markdown conversion engine.

## License

This project is licensed under the **MIT License**. You are free to use, modify, and distribute it as you see fit.
