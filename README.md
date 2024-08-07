# pub-w-tools

`pub-w-tools` is a versatile set of tools designed to handle and process various HTML content from the WOL site. The
primary functions include parsing HTML content from different types of articles into a structured JSON format and
retrieving the HTML of the current week's articles directly from the website.

## Disclaimer

This tool is intended for personal use only. The use of this tool must comply with the terms and conditions of the WOL.
Users are prohibited from redistributing, using the content for commercial purposes, or posting the content on any other
site. Please review the WOL's Terms and Conditions of Use before using this tool to ensure compliance.

## Usage

### Starting the Flask App

To start the Flask application, run:

```bash
flask run --port=3001
```

The app will run on `http://0.0.0.0:3001`.

### API Documentation

The API documentation for the available endpoints can be accessed at `/apidocs` and is autogenerated using Flasgger.

## Docker

The application is available as a Docker image on Docker Hub.

### Pulling the Latest Image

```bash
docker pull pub-w-tools:latest
```

### Running the Docker Container

```bash
docker run -d -p 3001:3001 joesofteng/pub-w-tools:latest
```

### Versioned Images

Versioned images are also available using the commit SHA as the tag:

```bash
docker pull joesofteng/pub-w-tools:{{ SHORT_SHA }}
# or 
docker pull joesofteng/pub-w-tools:latest

docker run -d -p 3001:3001 joesofteng/pub-w-tools:{{ SHORT_SHA }}
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

See the [LICENSE](./LICENSE) file for details.
