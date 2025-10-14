# File: models/image_service.py

"""
Educational Image Service for Course Materials Generator

This module provides comprehensive image search and integration capabilities
for educational content, supporting multiple APIs and maintaining topic integrity.
"""

import os
import requests
import logging
import time
import hashlib
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from urllib.parse import urlencode
import json

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ImageData:
    """Data structure for image information."""
    url: str
    thumbnail_url: Optional[str]
    title: str
    alt_text: str
    attribution: str
    source: str  # 'unsplash', 'pixabay', 'pexels'
    width: int
    height: int
    download_url: Optional[str] = None
    photographer: Optional[str] = None
    photographer_url: Optional[str] = None


class ImageTracker:
    """Track used images to prevent duplicates across modules."""
    
    def __init__(self):
        self.used_images = set()
        self.used_urls = set()
        self.module_images = {}  # module_id -> [image_urls]
    
    def is_image_used(self, image_url: str) -> bool:
        """Check if an image URL has already been used."""
        return image_url in self.used_urls
    
    def add_image(self, module_id: int, image_data: ImageData) -> None:
        """Add an image to the tracker for a specific module."""
        self.used_urls.add(image_data.url)
        if module_id not in self.module_images:
            self.module_images[module_id] = []
        self.module_images[module_id].append(image_data.url)
    
    def get_module_images(self, module_id: int) -> List[str]:
        """Get all image URLs used for a specific module."""
        return self.module_images.get(module_id, [])
    
    def clear_module(self, module_id: int) -> None:
        """Clear images for a specific module (useful for regeneration)."""
        if module_id in self.module_images:
            for url in self.module_images[module_id]:
                self.used_urls.discard(url)
            del self.module_images[module_id]


class EducationalImageService:
    """
    Service for fetching relevant educational images from multiple APIs.
    
    Maintains topic integrity by using complete search terms and provides
    fallback mechanisms for reliability.
    """
    
    def __init__(self):
        """Initialize the image service with API configurations."""
        # API Keys from environment
        self.unsplash_key = os.environ.get('UNSPLASH_ACCESS_KEY')
        self.pixabay_key = os.environ.get('PIXABAY_API_KEY')
        self.pexels_key = os.environ.get('PEXELS_API_KEY')
        
        # API endpoints
        self.unsplash_url = "https://api.unsplash.com/search/photos"
        self.pixabay_url = "https://pixabay.com/api/"
        self.pexels_url = "https://api.pexels.com/v1/search"
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Educational-Course-Materials-Generator/1.0'
        })
        
        # Cache for search results (optional)
        self.cache = {}
        
        logger.info("Educational Image Service initialized")
        self._log_api_status()
    
    def _log_api_status(self):
        """Log which APIs are available."""
        apis_available = []
        if self.unsplash_key:
            apis_available.append("Unsplash")
        if self.pixabay_key:
            apis_available.append("Pixabay")
        if self.pexels_key:
            apis_available.append("Pexels")
        
        if apis_available:
            logger.info(f"Available image APIs: {', '.join(apis_available)}")
        else:
            logger.warning("No image API keys configured - will use placeholder images")
    
    def _generate_educational_search_terms(self, topic: str, context: str = "") -> List[str]:
        """
        Generate search terms that maintain topic integrity for educational content.
        Uses ONLY the pure topic name without any additions.
        
        Args:
            topic: Complete topic name (e.g., "Python Programming", "Digital Electronics")
            context: Additional context (IGNORED in this implementation)
            
        Returns:
            List containing only the pure topic name
        """
        # Clean the topic - remove special characters but preserve the meaning
        clean_topic = re.sub(r'[^\w\s-]', '', topic).strip()
        
        # Return ONLY the clean topic name - no additions whatsoever
        search_terms = [clean_topic]
        
        logger.debug(f"Generated pure search term for '{topic}': [{clean_topic}]")
        return search_terms
    
    def _search_unsplash(self, search_terms: List[str], limit: int = 10) -> List[ImageData]:
        """Search Unsplash for educational images with support for higher limits."""
        if not self.unsplash_key:
            logger.debug("Unsplash API key not available")
            return []
        
        images = []
        
        for term in search_terms[:3]:  # Try top 3 search terms
            try:
                # Support higher limits for 12+ modules
                params = {
                    'query': term,
                    'per_page': min(limit, 30),  # Unsplash max is 30 per request
                    'content_filter': 'low',
                    'order_by': 'relevant'
                }
                
                headers = {
                    'Authorization': f'Client-ID {self.unsplash_key}'
                }
                
                logger.info(f"🔍 DEBUGGING: Searching Unsplash for: '{term}' requesting {min(limit, 30)} images")
                response = self.session.get(
                    self.unsplash_url, 
                    params=params, 
                    headers=headers, 
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    total_results = data.get('total', 0)
                    results_count = len(data.get('results', []))
                    logger.info(f"🔍 DEBUGGING: Unsplash returned {results_count} images out of {total_results} total available for '{term}'")
                    
                    for idx, photo in enumerate(data.get('results', [])):
                        if len(images) >= limit:
                            break
                            
                        try:
                            photographer = photo.get('user', {}).get('name', 'Unknown')
                            photographer_url = photo.get('user', {}).get('links', {}).get('html', '')
                            
                            image_data = ImageData(
                                url=photo['urls']['regular'],
                                thumbnail_url=photo['urls']['small'],
                                title=photo.get('description') or photo.get('alt_description') or f"Educational image for {term}",
                                alt_text=photo.get('alt_description') or f"Educational content related to {term}",
                                attribution=f"Photo by {photographer} on Unsplash",
                                source='unsplash',
                                width=photo.get('width', 800),
                                height=photo.get('height', 600),
                                download_url=photo['links']['download'],
                                photographer=photographer,
                                photographer_url=photographer_url
                            )
                            images.append(image_data)
                            
                        except KeyError as e:
                            logger.warning(f"🔍 DEBUGGING: Skipping Unsplash image {idx+1} due to missing data: {e}")
                            continue
                    
                    if images:
                        logger.info(f"🔍 DEBUGGING: Successfully processed {len(images)} images from Unsplash for '{term}'")
                        break  # Found images with this term
                        
                elif response.status_code == 403:
                    logger.error(f"🔍 DEBUGGING: Unsplash API rate limit exceeded for '{term}'")
                    break
                else:
                    logger.warning(f"🔍 DEBUGGING: Unsplash API error for '{term}': {response.status_code}")
                    
            except requests.RequestException as e:
                logger.error(f"🔍 DEBUGGING: Unsplash request failed for '{term}': {e}")
                continue
            
            time.sleep(0.1)  # Rate limiting
        
        logger.info(f"🔍 DEBUGGING: Final result - Found {len(images)} images from Unsplash (requested {limit})")
        return images
        
    def _search_pixabay(self, search_terms: List[str], limit: int = 10) -> List[ImageData]:
        """Search Pixabay for educational images with detailed debugging."""
        if not self.pixabay_key:
            logger.debug("Pixabay API key not available")
            return []
        
        images = []
        
        for term in search_terms[:3]:  
            try:
                
                params = {
                    'key': self.pixabay_key,
                    'q': term,
                    'image_type': 'photo',
                    # 'orientation': 'horizontal',   
                    'category': 'education,business,computer,science',
                    'min_width': 400,               
                    'min_height': 300,             
                    'per_page': min(limit, 20),
                    'safesearch': 'true',
                    'order': 'popular'
                }
                
                logger.info(f"🔍 DEBUGGING: Searching Pixabay for: '{term}' with params: {params}")
                response = self.session.get(self.pixabay_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 🔍 DEBUG: Log what we got back
                    total_hits = data.get('totalHits', 0)
                    hits_count = len(data.get('hits', []))
                    logger.info(f"🔍 DEBUGGING: Pixabay returned {hits_count} images out of {total_hits} total available for '{term}'")
                    
                    for idx, photo in enumerate(data.get('hits', [])):
                        if len(images) >= limit:
                            break
                            
                        try:
                            user = photo.get('user', 'Pixabay User')
                            
                            # 🔍 DEBUG: Log image details
                            photo_width = photo.get('imageWidth', 'unknown')
                            photo_height = photo.get('imageHeight', 'unknown')
                            photo_url = photo['webformatURL']
                            
                            logger.debug(f"🔍 DEBUGGING: Pixabay Image {idx+1}: {photo_width}x{photo_height}, URL: {photo_url[:50]}...")
                            
                            image_data = ImageData(
                                url=photo_url,
                                thumbnail_url=photo['previewURL'],
                                title=photo.get('tags', '').replace(',', ', ') or f"Educational image for {term}",
                                alt_text=f"Educational content: {photo.get('tags', term)}",
                                attribution=f"Image by {user} from Pixabay",
                                source='pixabay',
                                width=photo.get('imageWidth', 800),
                                height=photo.get('imageHeight', 600),
                                photographer=user,
                                photographer_url=f"https://pixabay.com/users/{user}/"
                            )
                            images.append(image_data)
                            
                        except KeyError as e:
                            logger.warning(f"🔍 DEBUGGING: Skipping Pixabay image {idx+1} due to missing data: {e}")
                            continue
                    
                    if images:
                        logger.info(f"🔍 DEBUGGING: Successfully processed {len(images)} images from Pixabay for '{term}'")
                        break  # Found images with this term
                    else:
                        logger.warning(f"🔍 DEBUGGING: No valid images processed from {hits_count} Pixabay results for '{term}'")
                        
                else:
                    logger.warning(f"🔍 DEBUGGING: Pixabay API error for '{term}': {response.status_code}")
                    logger.warning(f"🔍 DEBUGGING: Response content: {response.text[:200]}...")
                    
            except requests.RequestException as e:
                logger.error(f"🔍 DEBUGGING: Pixabay request failed for '{term}': {e}")
                continue
            
            time.sleep(0.1)  # Rate limiting
        
        logger.info(f"🔍 DEBUGGING: Final result - Found {len(images)} images from Pixabay")
        return images
    
    def _search_pexels(self, search_terms: List[str], limit: int = 10) -> List[ImageData]:
        """Search Pexels for educational images."""
        if not self.pexels_key:
            logger.debug("Pexels API key not available")
            return []
        
        images = []
        headers = {'Authorization': self.pexels_key}
        
        for term in search_terms[:3]:  # Try top 3 search terms
            try:
                params = {
                    'query': term,
                    'per_page': min(limit, 80),
                    'orientation': 'landscape'
                }
                
                logger.debug(f"Searching Pexels for: '{term}'")
                response = self.session.get(
                    self.pexels_url, 
                    params=params, 
                    headers=headers, 
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for photo in data.get('photos', []):
                        if len(images) >= limit:
                            break
                            
                        try:
                            photographer = photo.get('photographer', 'Pexels User')
                            photographer_url = photo.get('photographer_url', '')
                            
                            image_data = ImageData(
                                url=photo['src']['large'],
                                thumbnail_url=photo['src']['medium'],
                                title=photo.get('alt', f"Educational image for {term}"),
                                alt_text=photo.get('alt', f"Educational content related to {term}"),
                                attribution=f"Photo by {photographer} from Pexels",
                                source='pexels',
                                width=photo.get('width', 800),
                                height=photo.get('height', 600),
                                photographer=photographer,
                                photographer_url=photographer_url
                            )
                            images.append(image_data)
                            
                        except KeyError as e:
                            logger.warning(f"Skipping Pexels image due to missing data: {e}")
                            continue
                    
                    if images:
                        break  # Found images with this term
                        
                elif response.status_code == 429:
                    logger.error("Pexels API rate limit exceeded")
                    break
                else:
                    logger.warning(f"Pexels API error for '{term}': {response.status_code}")
                    
            except requests.RequestException as e:
                logger.error(f"Pexels request failed for '{term}': {e}")
                continue
            
            time.sleep(0.1)  # Rate limiting
        
        logger.info(f"Found {len(images)} images from Pexels")
        return images
    
    def _generate_placeholder_images(self, topic: str, count: int = 3) -> List[ImageData]:
        """Generate placeholder images when APIs are unavailable."""
        placeholders = []
        
        for i in range(count):
            # Create a deterministic but varied placeholder
            topic_hash = hashlib.md5(f"{topic}_{i}".encode()).hexdigest()[:6]
            
            placeholder_data = ImageData(
                url=f"https://via.placeholder.com/800x600/4A90E2/FFFFFF?text={topic.replace(' ', '+').replace('&', 'and')}+{i+1}",
                thumbnail_url=f"https://via.placeholder.com/400x300/4A90E2/FFFFFF?text={topic.replace(' ', '+').replace('&', 'and')}+{i+1}",
                title=f"Educational Placeholder for {topic} - Image {i+1}",
                alt_text=f"Placeholder image representing {topic} concepts",
                attribution="Placeholder image - replace with actual educational content",
                source='placeholder',
                width=800,
                height=600,
                photographer="System Generated",
                photographer_url=""
            )
            placeholders.append(placeholder_data)
        
        logger.info(f"Generated {len(placeholders)} placeholder images for '{topic}'")
        return placeholders
    
    def search_educational_images(self, 
                                topic: str, 
                                context: str = "", 
                                count: int = 3,
                                tracker: Optional[ImageTracker] = None) -> List[ImageData]:
        """
        Search for educational images across all available APIs.
        Now optimized to support 12+ modules with unique images.
        """
        logger.info(f"Searching for {count} educational images for topic: '{topic}'")
        
        # Generate educational search terms (maintains topic integrity)
        search_terms = self._generate_educational_search_terms(topic, context)
        
        # Create cache key
        cache_key = f"{topic}_{context}_{count}"
        if cache_key in self.cache:
            logger.debug(f"Using cached results for '{topic}'")
            cached_images = self.cache[cache_key]
            if tracker:
                # Smart reuse logic
                unused_images = [img for img in cached_images if not tracker.is_image_used(img.url)]
                
                if len(unused_images) >= count:
                    logger.info(f"🔍 CACHE: Found {len(unused_images)} unused images, returning {count}")
                    return unused_images[:count]
                elif unused_images:
                    logger.info(f"🔍 CACHE: Found {len(unused_images)} unused images out of {count} needed. Supplementing with reused images.")
                    needed_reused = count - len(unused_images)
                    reused_images = [img for img in cached_images if img not in unused_images][:needed_reused]
                    logger.info(f"🔍 CACHE: Using {len(unused_images)} unused + {len(reused_images)} reused = {len(unused_images + reused_images)} total")
                    return unused_images + reused_images
                else:
                    logger.info(f"🔍 CACHE: All images for '{topic}' have been used. Reusing images from cache.")
                    return cached_images[:count]
            return cached_images[:count]
        
        logger.info(f"🔍 CACHE MISS: No cached results for '{topic}', fetching from APIs...")
        
        
        # Calculate how many images we need to support 12 modules
        images_needed_for_12_modules = 12 * count  # 12 * 3 = 36 images
        per_api_target = images_needed_for_12_modules // 3  # 36 / 3 = 12 images per API
        
        logger.info(f"🔍 TARGETING: {images_needed_for_12_modules} total images ({per_api_target} per API) to support 12 modules")
        
        # Collect images from all APIs with increased limits
        all_images = []
        
        # Try each API with higher limits
        try:
            # Unsplash: Get more images (was 8, now 15)
            unsplash_images = self._search_unsplash(search_terms, per_api_target + 3)  # 12 + 3 = 15
            all_images.extend(unsplash_images)
            logger.info(f"🔍 UNSPLASH: Collected {len(unsplash_images)} images")
        except Exception as e:
            logger.error(f"Unsplash search failed: {e}")
        
        
        try:
            # Pexels: Get more images (was 8, now 15)
            pexels_images = self._search_pexels(search_terms, per_api_target + 3)  # 12 + 3 = 15
            all_images.extend(pexels_images)
            logger.info(f"🔍 PEXELS: Collected {len(pexels_images)} images")
        except Exception as e:
            logger.error(f"Pexels search failed: {e}")

        try:
            # Pixabay: Get more images (was 8, now 15)  
            pixabay_images = self._search_pixabay(search_terms, per_api_target + 3)  # 12 + 3 = 15
            all_images.extend(pixabay_images)
            logger.info(f"🔍 PIXABAY: Collected {len(pixabay_images)} images")
        except Exception as e:
            logger.error(f"Pixabay search failed: {e}")
        
        # If no images found, use placeholders
        if not all_images:
            logger.warning(f"No images found for '{topic}', using placeholders")
            all_images = self._generate_placeholder_images(topic, images_needed_for_12_modules)
        
        # Remove duplicates by URL
        unique_images = []
        seen_urls = set()
        
        for image in all_images:
            if image.url not in seen_urls:
                unique_images.append(image)
                seen_urls.add(image.url)
        
        # If still not enough unique images, add placeholders to reach target
        if len(unique_images) < images_needed_for_12_modules:
            needed = images_needed_for_12_modules - len(unique_images)
            logger.info(f"🔍 PADDING: Adding {needed} placeholder images to reach target of {images_needed_for_12_modules}")
            placeholders = self._generate_placeholder_images(f"{topic}_additional", needed)
            unique_images.extend(placeholders)
        
        # Cache ALL collected images (not just requested count)
        cache_size = len(unique_images)  # Cache everything we found
        self.cache[cache_key] = unique_images[:cache_size]
        logger.info(f"🔍 CACHING: Stored {len(self.cache[cache_key])} images in cache for '{topic}' (target was {images_needed_for_12_modules})")
        
        # Return final images with tracker filtering
        if tracker:
            unused_images = [img for img in unique_images if not tracker.is_image_used(img.url)]
            
            if len(unused_images) >= count:
                final_images = unused_images[:count]
                logger.info(f"🔍 FRESH: Returning {len(final_images)} unused images for '{topic}'")
            elif unused_images:
                needed_reused = count - len(unused_images)
                reused_images = [img for img in unique_images if img not in unused_images][:needed_reused]
                final_images = unused_images + reused_images
                logger.info(f"🔍 FRESH: Using {len(unused_images)} unused + {len(reused_images)} reused images for '{topic}'")
            else:
                final_images = unique_images[:count]
                logger.info(f"🔍 FRESH: All images previously used, reusing {len(final_images)} images for '{topic}'")
        else:
            final_images = unique_images[:count]
        
        logger.info(f"Returning {len(final_images)} educational images for '{topic}'")
        
        return final_images
    
    def validate_image_url(self, url: str) -> bool:
        """Validate that an image URL is accessible."""
        try:
            response = self.session.head(url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_image_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get additional information about an image URL."""
        try:
            response = self.session.head(url, timeout=5)
            if response.status_code == 200:
                return {
                    'content_type': response.headers.get('content-type', ''),
                    'content_length': response.headers.get('content-length', ''),
                    'last_modified': response.headers.get('last-modified', ''),
                    'accessible': True
                }
        except Exception as e:
            logger.debug(f"Could not get info for image {url}: {e}")
        
        return {'accessible': False}


# Global instance for easy import
image_service = EducationalImageService()