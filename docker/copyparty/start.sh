#!/bin/bash

# Create config directory if it doesn't exist
mkdir -p ~/Documents/copyparty

# Pull the latest image
sudo docker pull copyparty/ac:latest

# Start the container
sudo docker-compose up -d

# Show status
sudo docker-compose ps

echo ""
echo "Copyparty is now running!"
echo "Web Interface: http://localhost:3923"
echo "WebDAV URL: http://localhost:3923/media/"
echo ""
echo "To view logs: sudo docker-compose logs -f"
echo "To stop: sudo docker-compose down"
