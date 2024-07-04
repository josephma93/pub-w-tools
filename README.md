# pub-w-tools

`pub-w-tools` is a set of tools designed to handle and process HTML content from W articles on the WOL site.
The primary functions include parsing the HTML of Watchtower articles into a structured JSON
format and retrieving the HTML of the current week's article directly from the website.

## Features

- **HTML to JSON Parsing:**
    - Receives HTML content of a Watchtower article.
    - Parses the HTML to extract key information and converts it into a structured JSON format for further processing.
- **Weekly Article Retrieval:**
    - Automatically fetches the HTML content of the current week's Watchtower article from the WO.

## Disclaimer

This tool is intended for personal use only. The use of this tool must comply with the terms and conditions of the WOL.
Users are prohibited from redistributing, using the content for commercial purposes, or posting the content on any other site.
Please review the WOL's Terms and Conditions of Use before using this tool to ensure compliance.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/pub-w-tools.git
    cd pub-w-tools
    ```

2. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Starting the Flask App

To start the Flask application, run:

```bash
python pub_w_tools.py
```

By default, the app will run on `http://0.0.0.0:3001`.

### Endpoints

#### 1. `/pub-w` (POST)

This endpoint accepts HTML content of a Watchtower article and returns a structured JSON representation.

- **URL:** `/pub-w`
- **Method:** `POST`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Body Parameter:**
    - `html` (string): The HTML content of the article.

- **Response:**
    - `200 OK` with JSON containing the parsed article.
    - `400 Bad Request` if the input HTML is not provided.

**Example Request:**

```bash
curl -X POST http://0.0.0.0:3001/pub-w -d "html=<html_content>"
```

#### 2. `/get-article` (GET)

This endpoint fetches the HTML of the current week's Watchtower article from the WOL.

- **URL:** `/get-article`
- **Method:** `GET`

- **Response:**
    - `200 OK` with the HTML content of the article.
    - Appropriate error messages and status codes if the article is not found or other errors occur during processing.

**Example Request:**

```bash
curl http://0.0.0.0:3001/get-article
```

## Docker

The application is available as a Docker image on Docker Hub.

### Pulling the Latest Image

```bash
docker pull pub-w-tools:latest
```

### Running the Docker Container

```bash
docker run -d -p 3001:3001 pub-w-tools:latest
```

### Versioned Images

Versioned images are also available using the commit SHA as the tag:

```bash
docker pull pub-w-tools:{{ SHORT_SHA }}
docker run -d -p 3001:3001 pub-w-tools:{{ SHORT_SHA }}
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

See the [LICENSE](./LICENSE) file for details.