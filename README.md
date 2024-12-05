# Booru Gallery

A Flask-based web gallery for viewing images downloaded with [gallery-dl](https://github.com/mikf/gallery-dl).

## Features

- Thumbnail generation for faster image loading
- Tag-based navigation and search
- Responsive grid layout
- Image metadata display
- Multi-platform support (Windows, Linux, macOS)
- Background service option for Windows

## Requirements

- Python 3.8 or higher
- ImageMagick (for thumbnail generation)
- gallery-dl downloaded images

## Installation

1. Clone this repository:
```bash
git clone https://github.com/rejaad/booru-gallery
cd booru-gallery
```

2. Choose your installation method:

### Windows
```batch
booru-windows.bat
```

### Linux
```bash
chmod +x start_booru.sh
./booru-linux.sh
```

### macOS
```bash
chmod +x start_booru_mac.sh
./booru-mac.sh
```

The scripts will:
- Create a Python virtual environment
- Install required dependencies
- Start the web server

## Configuration

Edit `config.py` to change:
- Database location
- Image directory paths
- Server settings

## Usage

1. Place your gallery-dl downloaded images in the specified directory
2. Run the appropriate startup script for your platform
3. Access the web interface at `http://localhost:5000`

## Development

To set up a development environment:

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## License

```
Copyright 2024 ReJaad

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

## Acknowledgments

- [gallery-dl](https://github.com/mikf/gallery-dl) for the image downloading functionality
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [ImageMagick](https://imagemagick.org/) and [Wand](https://docs.wand-py.org/) for image processing

## Contributing

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes
4. Push to your branch
5. Create a Pull Request

## Support

If you encounter any issues, please file them in the Issues section of this repository.
