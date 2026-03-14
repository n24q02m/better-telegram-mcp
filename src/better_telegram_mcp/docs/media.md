# Telegram Media

Send and download media files: photos, documents, voice messages, and videos.

## Actions

### send_photo
Send a photo.
- **chat_id** (required): Chat ID or username
- **file_path_or_url** (required): Local file path or URL
- **caption**: Photo caption

### send_file
Send a document/file.
- **chat_id** (required): Chat ID or username
- **file_path_or_url** (required): Local file path or URL
- **caption**: File caption

### send_voice
Send a voice message.
- **chat_id** (required): Chat ID or username
- **file_path_or_url** (required): Local file path or URL
- **caption**: Voice message caption

### send_video
Send a video.
- **chat_id** (required): Chat ID or username
- **file_path_or_url** (required): Local file path or URL
- **caption**: Video caption

### download
Download media from a message.
- **chat_id** (required): Chat ID or username
- **message_id** (required): Message containing media
- **output_dir**: Directory to save file (default: current directory)