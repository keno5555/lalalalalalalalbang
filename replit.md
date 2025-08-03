# Overview

MusicFlow Bot is a fully functional Telegram music bot that provides seamless music download functionality with an attractive interactive interface. The bot accepts shared music links and delivers high-quality audio files with professional user experience. Users can download individual tracks, entire playlists, and albums with quality selection options, all through an intuitive button-based interface that eliminates boring text interactions.

**Status**: Production-ready and successfully tested with Spotify integration and audio downloads.

**Latest Update (Aug 3, 2025)**: Successfully configured main.py for Render deployment with Flask web server, fixed quality/file size info in audio captions, and resolved "Download Another" button functionality.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework Architecture
The application is built using the python-telegram-bot library with an event-driven architecture. The main entry point (`main.py`) initializes the Telegram application and registers handlers for different types of user interactions (commands, messages, and callback queries).

## Modular Component Design
The system follows a modular architecture with separate components for different responsibilities:

- **Handlers Module**: Manages all Telegram bot interactions including commands, messages, and button callbacks
- **Spotify Client**: Handles Spotify Web API integration for metadata extraction from shared links
- **Audio Processor**: Manages audio search and download operations using yt-dlp
- **Demo Songs**: Provides a rotating collection of demo tracks for testing functionality
- **Utils Module**: Contains helper functions for URL parsing and keyboard generation

## Music Processing Pipeline
The bot implements a multi-stage processing pipeline:
1. URL validation and Spotify ID extraction using regex patterns
2. Metadata retrieval from Spotify API for track/playlist information
3. Audio search and download via yt-dlp with configurable quality settings
4. File management using temporary directories with hash-based naming

## Quality Selection System
The bot offers three audio quality tiers (128kbps, 192kbps, 320kbps) through an interactive keyboard interface. Quality preferences are passed through the download pipeline to configure yt-dlp extraction parameters.

## Concurrent Processing
The system supports concurrent downloads with configurable limits to optimize performance while preventing resource exhaustion. Async/await patterns are used throughout for non-blocking operations.

## Configuration Management
All configuration settings including API credentials, quality options, download limits, and bot messages are centralized in a configuration module using environment variables for sensitive data.

# External Dependencies

## Spotify Web API
- **Service**: Spotify Web API for music metadata extraction
- **Authentication**: Client credentials flow using client ID and secret
- **Library**: spotipy Python client library
- **Purpose**: Extract track information, artist details, and playlist contents from Spotify URLs

## YouTube/Audio Download Service
- **Service**: yt-dlp for audio search and download functionality
- **Purpose**: Search for tracks based on metadata and download audio files
- **Features**: Multiple quality options, format conversion, and metadata embedding

## Telegram Bot API
- **Service**: Telegram Bot API for user interaction
- **Library**: python-telegram-bot for async bot framework
- **Features**: Message handling, inline keyboards, callback queries, and file uploads

## Flask Web Service (Deployment)
- **Service**: Flask web framework for Render deployment
- **Purpose**: Keep bot alive on Render hosting platform with health endpoints
- **Features**: Health check endpoints, bot process monitoring, subprocess management
- **Endpoints**: `/` for status, `/health` for health checks

## Environment Variables
Required environment variables for external service integration:
- `TELEGRAM_BOT_TOKEN`: Bot authentication token from BotFather
- `SPOTIFY_CLIENT_ID`: Spotify application client identifier
- `SPOTIFY_CLIENT_SECRET`: Spotify application client secret

## File System Dependencies
- Temporary file system storage for audio processing
- Hash-based file naming for conflict prevention
- Automatic cleanup of downloaded files

# Deployment Configuration

## Render Web Service Integration
The bot is configured for deployment on Render as a web service with the following components:

### Flask Web Application (`main.py`)
- Runs Flask web server on PORT environment variable (defaults to 10000)
- Provides multiple endpoints: `/`, `/health`, `/status`, `/api/status`
- Root endpoint returns simple "SpotifyPulse bot is running!" message
- Beautiful status page at `/status` with real-time updates and animated elements
- Telegram bot runs in background thread with proper asyncio event loop
- Flask web server runs on main thread for Render compatibility

### Deployment Files
- `Procfile`: Specifies `web: python main.py` as start command
- `requirements.txt`: Complete dependency list with version hashes
- `runtime.txt`: Python 3.11.9 runtime specification
- `README.md`: Comprehensive setup and deployment guide
- `DEPLOYMENT.md`: Detailed Render deployment instructions
- `.gitignore`: Git exclusion rules for clean repository

### Health Monitoring
- Root endpoint (`/`) returns bot status and service information
- Health endpoint (`/health`) provides detailed health metrics
- Bot process monitoring with automatic restart on failure
- Status tracking with last-seen timestamps for uptime verification

This configuration ensures the bot remains active on Render's platform while maintaining all existing music download functionality.