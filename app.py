from flask import Flask, render_template, request, send_from_directory, url_for, redirect, flash
import os
import json
import glob
from datetime import datetime
from models import db, Image, init_db
from config import Config
import logging
from tqdm import tqdm
from sqlalchemy import func, or_
from wand.image import Image as WandImage
from multiprocessing import Pool, cpu_count
from math import ceil
import warnings
from settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load settings
settings = Settings()

def generate_single_thumbnail(args):
    """Generate a single thumbnail using ImageMagick."""
    source_path, thumb_path, width = args
    try:
        with WandImage(filename=source_path) as img:
            # Strip metadata to reduce size
            img.strip()
            
            # Calculate height maintaining aspect ratio
            ratio = width / img.width
            height = int(img.height * ratio)
            
            # Resize using high-quality Lanczos filter
            img.resize(width, height, filter='lanczos2')
            
            # Set compression quality
            img.compression_quality = settings.get('thumbnails', 'quality')
            
            # Optimize output format based on original
            if thumb_path.lower().endswith('.png'):
                img.format = 'png'
                img.options['png:compression-level'] = str(settings.get('thumbnails', 'compression_level'))
            else:
                img.format = 'jpeg'
            
            img.save(filename=thumb_path)
            return True
    except Exception as e:
        logger.error(f"Error generating thumbnail for {source_path}: {str(e)}")
        return False

def setup_image_paths(app):
    """Setup image directories and process images/thumbnails."""
    images_dir = os.path.join(app.static_folder, settings.get('paths', 'images_folder'))
    thumbnails_dir = os.path.join(app.static_folder, settings.get('paths', 'thumbnails_folder'))
    
    # Create directories if they don't exist
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(thumbnails_dir, exist_ok=True)
    
    # Flag files to track processing status
    flag_file = os.path.join(images_dir, '.images_copied')
    thumbnail_flag = os.path.join(thumbnails_dir, '.thumbnails_generated')
    
    def process_images():
        """Copy images and generate thumbnails if needed."""
        if not os.path.exists(flag_file):
            logger.info("Copying images to static directory...")
            copy_images(images_dir)
            
        if not os.path.exists(thumbnail_flag):
            logger.info("Generating thumbnails...")
            
            # Get list of images that need thumbnails
            image_files = []
            for filename in os.listdir(images_dir):
                if any(filename.endswith(ext) for ext in ['.jpg', '.png', '.gif', '.jpeg']):
                    thumb_path = os.path.join(thumbnails_dir, filename)
                    if not os.path.exists(thumb_path):
                        source_path = os.path.join(images_dir, filename)
                        image_files.append((source_path, thumb_path, settings.get('thumbnails', 'width')))

            if image_files:
                # Use configured percentage of CPU cores
                num_processes = ceil(cpu_count() * (settings.get('processing', 'cpu_usage_percent') / 100))
                logger.info(f"Starting thumbnail generation with {num_processes} processes")
                
                with Pool(processes=num_processes) as pool:
                    results = list(tqdm(
                        pool.imap_unordered(generate_single_thumbnail, image_files),
                        total=len(image_files),
                        desc="Generating thumbnails"
                    ))
                    
                    successful = sum(1 for r in results if r)
                    logger.info(f"Successfully generated {successful} thumbnails")

            # Create flag file
            with open(thumbnail_flag, 'w') as f:
                f.write(f"Thumbnails generated on {datetime.now()}")
    
    return process_images

def copy_images(images_dir):
    """Copy images from source directory to static folder."""
    source_dir = settings.get('paths', 'source_images')
    
    # Count total files to copy
    total_files = len([f for f in os.listdir(source_dir) 
                      if any(f.endswith(ext) for ext in ['.jpg', '.png', '.gif', '.jpeg'])])
    
    if total_files == 0:
        logger.warning("No image files found in source directory")
        return
    
    # Copy files with progress bar
    copied = 0
    for filename in tqdm(os.listdir(source_dir), total=total_files, desc="Copying images"):
        if any(filename.endswith(ext) for ext in ['.jpg', '.png', '.gif', '.jpeg']):
            src_path = os.path.join(source_dir, filename)
            dst_path = os.path.join(images_dir, filename)
            
            if not os.path.exists(dst_path):
                try:
                    os.copy2(src_path, dst_path)
                    copied += 1
                    if copied % 1000 == 0:
                        logger.info(f"Copied {copied}/{total_files} images")
                except Exception as e:
                    logger.error(f"Error copying {filename}: {str(e)}")

def load_images_from_json(path):
    """Load image data from JSON files into database."""
    batch_size = settings.get('processing', 'batch_size')
    processed = 0
    json_files = [f for f in os.listdir(path) if f.endswith('.json')]
    
    for i in tqdm(range(0, len(json_files), batch_size)):
        batch_files = json_files[i:i + batch_size]
        batch = []
        
        for filename in batch_files:
            try:
                with open(os.path.join(path, filename), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Convert tag arrays to comma-separated strings
                    tags_general = ','.join(data.get('tags_general', [])) if isinstance(data.get('tags_general'), list) else data.get('tags_general', '')
                    tags_artist = ','.join(data.get('tags_artist', [])) if isinstance(data.get('tags_artist'), list) else data.get('tags_artist', '')
                    tags_character = ','.join(data.get('tags_character', [])) if isinstance(data.get('tags_character'), list) else data.get('tags_character', '')
                    tags_copyright = ','.join(data.get('tags_copyright', [])) if isinstance(data.get('tags_copyright'), list) else data.get('tags_copyright', '')
                    tags_meta = ','.join(data.get('tags_meta', [])) if isinstance(data.get('tags_meta'), list) else data.get('tags_meta', '')

                    def parse_datetime(dt_str):
                        if not dt_str:
                            return None
                        try:
                            return datetime.fromisoformat(dt_str)
                        except (ValueError, TypeError):
                            return None

                    image = Image(
                        id=data['id'],
                        created_at=parse_datetime(data['created_at']) or datetime.min,
                        updated_at=parse_datetime(data['updated_at']) or datetime.min,
                        up_score=int(data.get('up_score', 0)),
                        down_score=int(data.get('down_score', 0)),
                        score=int(data.get('score', 0)),
                        source=str(data.get('source', '')),
                        md5=str(data.get('md5', '')),
                        rating=str(data.get('rating', '')),
                        is_pending=bool(data.get('is_pending', False)),
                        is_flagged=bool(data.get('is_flagged', False)),
                        is_deleted=bool(data.get('is_deleted', False)),
                        uploader_id=data.get('uploader_id'),
                        approver_id=data.get('approver_id'),
                        last_noted_at=parse_datetime(data.get('last_noted_at')),
                        last_comment_bumped_at=parse_datetime(data.get('last_comment_bumped_at')),
                        fav_count=int(data.get('fav_count', 0)),
                        tag_string=str(data.get('tag_string', '')),
                        tag_count=int(data.get('tag_count', 0)),
                        tag_count_general=int(data.get('tag_count_general', 0)),
                        tag_count_artist=int(data.get('tag_count_artist', 0)),
                        tag_count_character=int(data.get('tag_count_character', 0)),
                        tag_count_copyright=int(data.get('tag_count_copyright', 0)),
                        file_ext=str(data.get('file_ext', '')),
                        file_size=int(data.get('file_size', 0)),
                        image_width=int(data.get('image_width', 0)),
                        image_height=int(data.get('image_height', 0)),
                        parent_id=data.get('parent_id'),
                        has_children=bool(data.get('has_children', False)),
                        is_banned=bool(data.get('is_banned', False)),
                        pixiv_id=str(data.get('pixiv_id', '')),
                        last_commented_at=parse_datetime(data.get('last_commented_at')),
                        has_active_children=bool(data.get('has_active_children', False)),
                        bit_flags=int(data.get('bit_flags', 0)),
                        tag_count_meta=int(data.get('tag_count_meta', 0)),
                        has_large=bool(data.get('has_large', False)),
                        has_visible_children=bool(data.get('has_visible_children', False)),
                        tags_general=tags_general,
                        tags_artist=tags_artist,
                        tags_character=tags_character,
                        tags_copyright=tags_copyright,
                        tags_meta=tags_meta
                    )
                    batch.append(image)
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                continue
        
        if batch:
            try:
                db.session.bulk_save_objects(batch)
                db.session.commit()
                processed += len(batch)
                logger.info(f"Processed {processed}/{len(json_files)} files")
            except Exception as e:
                logger.error(f"Error committing batch: {str(e)}")
                db.session.rollback()

def booru_webui(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__, 
                static_folder=os.path.join(os.path.dirname(__file__), 'static'),
                static_url_path='/static')
    
    # Load configuration
    app.config.from_object(config_class)
    
    # Ensure static directories exist
    os.makedirs(app.static_folder, exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, 'images'), exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, 'thumbnails'), exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, 'css'), exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    
    # Setup image processing
    process_images = setup_image_paths(app)
    
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Process images if not in debug/reloader mode
        if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            process_images()
    
    # Context processor for templates
    @app.context_processor
    def inject_settings():
        return {
            'settings': settings,
            'now': datetime.now()
        }
    
    @app.route('/')
    def index():
        """Home page route."""
        # Get basic statistics
        total_images = Image.query.count()
        active_images = Image.query.filter(
            Image.is_deleted == False,
            Image.is_banned == False
        ).count()

        # Get top tags
        tags = {}
        for image in Image.query.limit(1000):
            for tag_type in ['general', 'artist', 'character', 'copyright', 'meta']:
                tags_str = getattr(image, f'tags_{tag_type}', '')
                if tags_str:
                    for tag in tags_str.split(','):
                        tag = tag.strip()
                        if tag:
                            tags[tag] = tags.get(tag, 0) + 1

        top_tags = dict(sorted(tags.items(), 
                             key=lambda x: x[1], 
                             reverse=True)[:settings.get('ui', 'tag_cloud_limit')])

        stats = {
            'total_images': total_images,
            'active_images': active_images,
            'top_tags': top_tags
        }

        return render_template('index.html', stats=stats)

    @app.route('/gallery')
    def gallery():
        """Gallery page route."""
        try:
            page = request.args.get('page', 1, type=int)
            images_per_page = settings.get('gallery', 'images_per_page')
            
            # Build base query
            query = Image.query

            # Apply filters
            if settings.get('filters', 'exclude_deleted'):
                query = query.filter(Image.is_deleted == False)
            if settings.get('filters', 'exclude_banned'):
                query = query.filter(Image.is_banned == False)
            
            # Get total count for pagination
            total_count = query.count()
            max_pages = (total_count + images_per_page - 1) // images_per_page

            # Validate page number
            page = max(1, min(page, max_pages))

            # Apply sorting
            sort_by = settings.get('gallery', 'sort_by')
            sort_order = settings.get('gallery', 'sort_order')
            
            if sort_order == 'desc':
                query = query.order_by(getattr(Image, sort_by).desc())
            else:
                query = query.order_by(getattr(Image, sort_by).asc())

            # Paginate results
            pagination = query.paginate(
                page=page,
                per_page=images_per_page,
                error_out=False
            )

            return render_template('gallery.html',
                                 images=pagination.items,
                                 pagination=pagination,
                                 current_page=page,
                                 total_pages=max_pages)

        except Exception as e:
            logger.error(f"Error in gallery route: {str(e)}")
            return f"An error occurred: {str(e)}", 500

    @app.route('/image/<int:image_id>')
    def view_image(image_id):
        """Single image view route."""
        try:
            image = Image.query.get_or_404(image_id)

            # Get previous and next image IDs
            prev_image = Image.query.filter(
                Image.id < image_id,
                Image.is_deleted == False,
                Image.is_banned == False
            ).order_by(Image.id.desc()).first()

            next_image = Image.query.filter(
                Image.id > image_id,
                Image.is_deleted == False,
                Image.is_banned == False
            ).order_by(Image.id.asc()).first()

            return render_template('image.html',
                                 image=image,
                                 prev_id=prev_image.id if prev_image else None,
                                 next_id=next_image.id if next_image else None)

        except Exception as e:
            logger.error(f"Error viewing image {image_id}: {str(e)}")
            return f"Error viewing image: {str(e)}", 500

    @app.route('/tagcloud')
    def tagcloud():
        """Tag cloud view route."""
        logger.info("Accessing tag cloud")
        tag_counts = {}

        # Apply filters from settings
        query = Image.query
        if settings.get('filters', 'exclude_deleted'):
            query = query.filter(Image.is_deleted == False)
        if settings.get('filters', 'exclude_banned'):
            query = query.filter(Image.is_banned == False)

        # Get all qualified images
        images = query.all()

        # Process tags
        for image in images:
            for tag_type in ['general', 'artist', 'character', 'copyright', 'meta']:
                tags_str = getattr(image, f'tags_{tag_type}', '')
                if tags_str:
                    for tag in tags_str.split(','):
                        tag = tag.strip()
                        if tag:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Sort tags by count and take top N as configured
        tag_limit = settings.get('ui', 'tag_cloud_limit')
        sorted_tags = dict(sorted(tag_counts.items(),
                                key=lambda x: x[1],
                                reverse=True)[:tag_limit])

        logger.info(f"Generated tag cloud with {len(sorted_tags)} tags")
        return render_template('tagcloud.html', tags=sorted_tags)

    @app.route('/search')
    def search():
        """Search route for finding images by tags."""
        query = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        
        if not query:
            return redirect(url_for('gallery'))
            
        try:
            # Split query into individual tags
            search_tags = [tag.strip() for tag in query.split(',') if tag.strip()]
            
            # Build base query
            base_query = Image.query
            
            # Apply filters from settings
            if settings.get('filters', 'exclude_deleted'):
                base_query = base_query.filter(Image.is_deleted == False)
            if settings.get('filters', 'exclude_banned'):
                base_query = base_query.filter(Image.is_banned == False)
            
            # Search across all tag types
            if search_tags:
                conditions = []
                for tag in search_tags:
                    tag_condition = or_(
                        Image.tags_general.like(f'%{tag}%'),
                        Image.tags_artist.like(f'%{tag}%'),
                        Image.tags_character.like(f'%{tag}%'),
                        Image.tags_copyright.like(f'%{tag}%'),
                        Image.tags_meta.like(f'%{tag}%')
                    )
                    conditions.append(tag_condition)
                base_query = base_query.filter(*conditions)
            
            # Paginate results
            page_size = settings.get('gallery', 'images_per_page')
            pagination = base_query.paginate(
                page=page,
                per_page=page_size,
                error_out=False
            )
            
            return render_template('search.html',
                                 query=query,
                                 images=pagination.items,
                                 pagination=pagination)
                                 
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            flash("An error occurred while searching. Please try again.")
            return redirect(url_for('gallery'))

    @app.route('/debug/images')
    def debug_images():
        """Debug route for checking image processing status."""
        if not settings.get('server', 'debug'):
            return "Debug mode is disabled", 403
            
        static_folder = app.static_folder
        images_dir = os.path.join(static_folder, settings.get('paths', 'images_folder'))

        try:
            files = os.listdir(images_dir)
            image_files = [f for f in files if f.endswith(('.jpg', '.png', '.gif', '.jpeg'))]

            # Get sample database records
            db_images = Image.query.limit(5).all()

            debug_info = {
                'static_folder': static_folder,
                'images_dir': images_dir,
                'total_files': len(files),
                'total_images': len(image_files),
                'sample_files': image_files[:5],
                'database_records': [
                    {
                        'id': img.id,
                        'md5': img.md5,
                        'file_ext': img.file_ext,
                        'expected_filename': f"{img.md5}.{img.file_ext}"
                    }
                    for img in db_images
                ]
            }

            return render_template('debug.html', debug_info=debug_info)
        except Exception as e:
            return f"Error: {str(e)}", 500

    @app.before_first_request
    def load_data():
        """Load initial data from JSON files if database is empty."""
        logger.info("Checking database status...")
        path = settings.get('paths', 'source_json')
    
        if not os.path.exists(path):
            logger.error(f"Data directory not found: {path}")
            return
        
        if not Image.query.first():
            logger.info("No images in database, loading from JSON...")
            try:
                file_count = len([f for f in os.listdir(path) if f.endswith('.json')])
                logger.info(f"Found {file_count} JSON files to process")
                load_images_from_json(path)
                logger.info("Data loading completed")
            except Exception as e:
                logger.error(f"Error loading data: {str(e)}")
        else:
            logger.info("Database already contains images, skipping load")

    @app.route('/static/images/<path:filename>')
    def serve_image(filename):
        """Serve image files from static directory."""
        return send_from_directory(app.static_folder + '/images', filename)

    @app.route('/static/thumbnails/<path:filename>')
    def serve_thumbnail(filename):
        """Serve thumbnail files from static directory."""
        return send_from_directory(app.static_folder + '/thumbnails', filename)

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        db.session.rollback()
        return render_template('500.html'), 500

    return app

if __name__ == '__main__':
    app = booru_webui()
    logger.info("Starting Flask application...")
    app.run(
        host=settings.get('server', 'host'),
        port=settings.get('server', 'port'),
        debug=settings.get('server', 'debug')
    )