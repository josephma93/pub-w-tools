import os

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3001))
    app.logger.info(f'Starting Flask app on port {port}.')
    app.run(host='0.0.0.0', port=port)
