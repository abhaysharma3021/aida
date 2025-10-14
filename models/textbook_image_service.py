# File: models/textbook_image_service.py

"""
Textbook-Style Image Integration Service - No Duplicates, 4 Images Per Module
Embeds exactly 4 unique, relevant images per module with varied keywords
"""

import re
import requests
import logging
import os
from typing import Dict, List, Optional, Set
from urllib.parse import quote
import hashlib

logger = logging.getLogger(__name__)

class TextbookImageService:
    """Service to embed exactly 4 unique images per module with no duplicates."""
    
    def __init__(self):
        # API keys (supports multiple APIs with fallback)
        self.unsplash_access_key = os.environ.get('UNSPLASH_ACCESS_KEY')
        self.pixabay_key = os.environ.get('PIXABAY_API_KEY')
        self.pexels_key = os.environ.get('PEXELS_API_KEY')
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ASID Course Materials Generator 1.0'
        })
        
        # Track used images per module to prevent duplicates
        self.used_images_per_module: Dict[str, Set[str]] = {}
        self.images_added_per_module: Dict[str, int] = {}
        
        # Debug logging
        active_apis = []
        if self.unsplash_access_key:
            active_apis.append("Unsplash")
        if self.pixabay_key:
            active_apis.append("Pixabay")
        if self.pexels_key:
            active_apis.append("Pexels")
            
        if active_apis:
            logger.info(f"✅ Image APIs loaded: {', '.join(active_apis)}")
        else:
            logger.warning("❌ No image API keys found")
    
    def embed_images_in_content(self, content: str, module_title: str = "") -> str:
        """
        Embed exactly 4 unique images into module content with no duplicates.
        
        Args:
            content: The original markdown content
            module_title: The module title for context
            
        Returns:
            Enhanced content with exactly 4 embedded images
        """
        if not content:
            logger.warning("No content provided for image embedding")
            return content
        
        # Create a unique module key for tracking
        module_key = self._create_module_key(module_title, content)
        
        # Reset tracking for this module
        self.used_images_per_module[module_key] = set()
        self.images_added_per_module[module_key] = 0
        
        logger.info(f"🎯 Starting image embedding for module: {module_title}")
        logger.info(f"📄 Target: Exactly 4 unique images per module")
        
        # Split content into sections
        sections = self._split_content_into_sections(content)
        logger.info(f"📄 Split content into {len(sections)} sections")
        
        # Select exactly 4 sections for images (distributed evenly)
        sections_for_images = self._select_sections_for_images(sections, target_count=4)
        logger.info(f"🎯 Selected {len(sections_for_images)} sections for image placement")
        
        enhanced_sections = []
        
        for i, section in enumerate(sections):
            enhanced_section = section
            
            # Only add image if this section was selected AND we haven't reached limit
            if (i in sections_for_images and 
                self.images_added_per_module[module_key] < 4):
                
                logger.info(f"🖼️ Adding image {self.images_added_per_module[module_key] + 1}/4 to section {i+1}")
                
                # Get a unique image for this section
                image_data = self._get_unique_image_for_section(
                    section, module_title, module_key, i
                )
                
                if image_data:
                    image_html = self._create_textbook_image_html(image_data, section, i+1)
                    enhanced_section = self._insert_image_in_section(section, image_html)
                    
                    # Track this image to prevent duplicates
                    image_id = self._get_image_identifier(image_data)
                    self.used_images_per_module[module_key].add(image_id)
                    self.images_added_per_module[module_key] += 1
                    
                    logger.info(f"✅ Image {self.images_added_per_module[module_key]}/4 added from {image_data['source']}")
                else:
                    logger.warning(f"❌ No unique image found for section {i+1}")
            
            enhanced_sections.append(enhanced_section)
        
        result = '\n\n'.join(enhanced_sections)
        final_count = self.images_added_per_module[module_key]
        logger.info(f"🎉 Image embedding completed: {final_count}/4 images added to {module_title}")
        
        return result
    
    def _create_module_key(self, module_title: str, content: str) -> str:
        """Create a unique key for this module to track images."""
        # Use module title + content hash to create unique key
        content_hash = hashlib.md5(content[:500].encode()).hexdigest()[:8]
        return f"{module_title}_{content_hash}"
    
    def _select_sections_for_images(self, sections: List[str], target_count: int = 4) -> List[int]:
        """
        Select exactly 4 sections for image placement, distributed evenly throughout the content.
        
        Args:
            sections: List of content sections
            target_count: Number of images to place (default: 4)
            
        Returns:
            List of section indices where images should be placed
        """
        if len(sections) <= target_count:
            # If we have 4 or fewer sections, use all of them
            return list(range(len(sections)))
        
        selected_sections = []
        
        # Always include section 1 (after introduction)
        if len(sections) > 1:
            selected_sections.append(1)
        
        # Distribute remaining images evenly
        remaining_slots = target_count - len(selected_sections)
        remaining_sections = len(sections) - 2  # Exclude sections 0 and 1
        
        if remaining_slots > 0 and remaining_sections > 0:
            # Calculate spacing between images
            step = max(1, remaining_sections // remaining_slots)
            
            current_pos = 2  # Start from section 2
            for _ in range(remaining_slots):
                if current_pos < len(sections):
                    selected_sections.append(current_pos)
                    current_pos += step
        
        # Sort and ensure we don't exceed bounds
        selected_sections = sorted(set(selected_sections))
        return selected_sections[:target_count]
    
    def _get_unique_image_for_section(self, section: str, module_title: str, 
                                    module_key: str, section_index: int) -> Optional[Dict]:
        """
        Get a unique image for a section, ensuring no duplicates within the module.
        
        Args:
            section: The section content
            module_title: The module title
            module_key: Unique module identifier
            section_index: Index of the section (for variety)
            
        Returns:
            Image data dictionary or None
        """
        # Try multiple search strategies to get varied results
        max_attempts = 5
        used_images = self.used_images_per_module.get(module_key, set())
        
        for attempt in range(max_attempts):
            # Generate varied search terms for each attempt
            search_term = self._generate_varied_search_term(
                section, module_title, section_index, attempt
            )
            
            image_type = self._determine_image_type(section)
            
            logger.info(f"🔍 Attempt {attempt + 1}: Searching for '{search_term}' (type: {image_type})")
            
            # Get image using the search term
            image_data = self._get_single_image(search_term, image_type)
            
            if image_data:
                image_id = self._get_image_identifier(image_data)
                
                # Check if we've already used this image in this module
                if image_id not in used_images:
                    logger.info(f"✅ Found unique image: {image_id[:20]}...")
                    return image_data
                else:
                    logger.info(f"🔄 Image already used, trying different search...")
            else:
                logger.info(f"❌ No image found for attempt {attempt + 1}")
        
        logger.warning(f"⚠️ Could not find unique image after {max_attempts} attempts")
        return None
    
    def _generate_varied_search_term(self, section: str, module_title: str, 
                                   section_index: int, attempt: int) -> str:
        """
        Generate varied search terms to get different images for each section.
        
        Args:
            section: Section content
            module_title: Module title
            section_index: Which section this is (for variety)
            attempt: Which attempt this is (for fallbacks)
            
        Returns:
            Varied search term
        """
        # Extract different types of keywords based on attempt
        if attempt == 0:
            # First attempt: Use section heading + module context
            keywords = self._extract_section_heading_keywords(section)
            if module_title:
                clean_title = module_title.split(':')[-1].strip()
                keywords.insert(0, clean_title)
        
        elif attempt == 1:
            # Second attempt: Use technical terms from section
            keywords = self._extract_technical_keywords(section)
            
        elif attempt == 2:
            # Third attempt: Use action words and concepts
            keywords = self._extract_action_keywords(section)
            
        elif attempt == 3:
            # Fourth attempt: Use broader conceptual terms
            keywords = self._extract_broad_concepts(section, module_title)
            
        else:
            # Final attempt: Use very broad educational terms
            keywords = self._get_fallback_keywords(module_title)
        
        # Add variety based on section index
        variety_terms = self._get_variety_terms_by_index(section_index)
        if variety_terms:
            keywords.extend(variety_terms)
        
        # Combine and clean keywords
        search_term = ' '.join(keywords[:3])  # Use top 3 keywords
        return self._clean_search_term(search_term)
    
    def _extract_section_heading_keywords(self, section: str) -> List[str]:
        """Extract keywords from section headings."""
        keywords = []
        
        # Look for headings
        heading_matches = re.findall(r'^#{2,6}\s+(.+)$', section, re.MULTILINE)
        for heading in heading_matches:
            # Clean and extract meaningful words
            words = re.findall(r'\b[a-zA-Z]{3,}\b', heading.lower())
            keywords.extend(words[:2])
        
        return keywords
    
    def _extract_technical_keywords(self, section: str) -> List[str]:
        """Extract technical terms and proper nouns."""
        keywords = []
        
        # Find capitalized terms (likely technical terms)
        technical_terms = re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', section)
        keywords.extend(technical_terms[:3])
        
        # Find terms in code blocks or quotes
        code_terms = re.findall(r'`([^`]+)`', section)
        for term in code_terms:
            if len(term) > 2 and term.replace('_', '').replace('-', '').isalnum():
                keywords.append(term)
        
        return keywords[:3]
    
    def _extract_action_keywords(self, section: str) -> List[str]:
        """Extract action words and process-related terms."""
        action_words = [
            'implement', 'develop', 'create', 'build', 'design', 'analyze',
            'manage', 'process', 'execute', 'optimize', 'configure', 'deploy',
            'test', 'debug', 'integrate', 'monitor', 'secure', 'scale'
        ]
        
        keywords = []
        section_lower = section.lower()
        
        for action in action_words:
            if action in section_lower:
                keywords.append(action)
        
        return keywords[:3]
    
    def _extract_broad_concepts(self, section: str, module_title: str) -> List[str]:
        """Extract broader conceptual terms."""
        concepts = [
            'technology', 'business', 'education', 'development', 'management',
            'analysis', 'design', 'strategy', 'innovation', 'solution',
            'system', 'process', 'method', 'approach', 'framework'
        ]
        
        keywords = []
        section_lower = section.lower()
        
        for concept in concepts:
            if concept in section_lower:
                keywords.append(concept)
        
        # Add module-based concepts
        if module_title:
            if 'python' in module_title.lower():
                keywords.extend(['programming', 'coding', 'software'])
            elif 'data' in module_title.lower():
                keywords.extend(['analytics', 'statistics', 'visualization'])
            elif 'web' in module_title.lower():
                keywords.extend(['website', 'internet', 'digital'])
        
        return keywords[:3]
    
    def _get_fallback_keywords(self, module_title: str) -> List[str]:
        """Get fallback keywords when other methods fail."""
        fallbacks = ['education', 'learning', 'business']
        
        if module_title:
            # Extract any meaningful words from module title
            words = re.findall(r'\b[a-zA-Z]{3,}\b', module_title.lower())
            if words:
                return words[:2] + fallbacks[:1]
        
        return fallbacks
    
    def _get_variety_terms_by_index(self, section_index: int) -> List[str]:
        """Add variety terms based on section index to ensure different images."""
        variety_sets = [
            ['concept', 'illustration'],      # Section 0/4/8...
            ['example', 'practical'],         # Section 1/5/9...
            ['process', 'workflow'],          # Section 2/6/10...
            ['result', 'outcome']             # Section 3/7/11...
        ]
        
        set_index = section_index % len(variety_sets)
        return variety_sets[set_index]
    
    def _clean_search_term(self, search_term: str) -> str:
        """Clean and optimize the search term."""
        # Remove non-alphanumeric characters except spaces
        clean_term = re.sub(r'[^\w\s]', '', search_term)
        
        # Remove common stop words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = [word for word in clean_term.split() if word.lower() not in stop_words]
        
        # Return cleaned term
        return ' '.join(words[:3])  # Limit to 3 words max
    
    def _get_image_identifier(self, image_data: Dict) -> str:
        """Create a unique identifier for an image to prevent duplicates."""
        if image_data.get('source') == 'placeholder':
            # For placeholders, use the search term
            return f"placeholder_{image_data.get('alt_text', 'default')}"
        
        # For real images, use URL or ID
        if 'id' in image_data:
            return f"{image_data['source']}_{image_data['id']}"
        elif 'url' in image_data:
            # Extract unique part of URL
            url_hash = hashlib.md5(image_data['url'].encode()).hexdigest()[:10]
            return f"{image_data['source']}_{url_hash}"
        else:
            # Fallback
            return f"{image_data['source']}_{image_data.get('photographer', 'unknown')}"
    
    def _get_single_image(self, search_term: str, image_type: str = "concept") -> Optional[Dict]:
        """Get a single image from available APIs."""
        enhanced_search = self._enhance_search_term(search_term, image_type)
        
        # Try APIs in order of preference
        if self.unsplash_access_key:
            image = self._get_unsplash_image(enhanced_search)
            if image:
                return image
        
        if self.pixabay_key:
            image = self._get_pixabay_image(enhanced_search, image_type)
            if image:
                return image
        
        if self.pexels_key:
            image = self._get_pexels_image(enhanced_search)
            if image:
                return image
        
        # Return placeholder if no APIs available
        return self._get_placeholder_image(search_term)
    
    def _enhance_search_term(self, search_term: str, image_type: str) -> str:
        """Enhance search terms for better API results."""
        clean_term = re.sub(r'[^\w\s]', '', search_term.lower())
        
        # Add context based on image type
        context_map = {
            "concept": ["concept", "illustration"],
            "example": ["example", "practical"],
            "diagram": ["diagram", "chart"],
            "process": ["process", "workflow"],
            "tool": ["tool", "software"],
            "result": ["result", "visualization"]
        }
        
        context_terms = context_map.get(image_type, ["illustration"])
        enhanced = f"{clean_term} {context_terms[0]}"
        
        return enhanced.strip()
    
    # Include all the existing API methods (_get_unsplash_image, _get_pixabay_image, etc.)
    # [Previous API methods remain the same - I'll include the key ones]
    
    def _get_unsplash_image(self, search_term: str) -> Optional[Dict]:
        """Get image from Unsplash API."""
        try:
            url = "https://api.unsplash.com/search/photos"
            params = {
                'query': search_term,
                'per_page': 1,
                'orientation': 'landscape',
                'content_filter': 'high',
                'order_by': 'relevant'
            }
            headers = {
                'Authorization': f'Client-ID {self.unsplash_access_key}'
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                if results:
                    photo = results[0]
                    return {
                        'id': photo['id'],
                        'url': photo['urls']['regular'],
                        'thumbnail': photo['urls']['small'],
                        'alt_text': photo.get('alt_description', search_term),
                        'attribution': f"Photo by {photo['user']['name']} on Unsplash",
                        'photographer': photo['user']['name'],
                        'source': 'unsplash'
                    }
        except Exception as e:
            logger.error(f"Error fetching from Unsplash: {str(e)}")
        
        return None
    
    def _get_pixabay_image(self, search_term: str, image_type: str) -> Optional[Dict]:
        """Get image from Pixabay API."""
        try:
            url = "https://pixabay.com/api/"
            
            category_map = {
                "concept": "education",
                "diagram": "computer", 
                "tool": "computer",
                "process": "business",
                "example": "business"
            }
            category = category_map.get(image_type, "education")
            
            params = {
                'key': self.pixabay_key,
                'q': search_term.replace(' ', '+'),
                'image_type': 'photo',
                'orientation': 'horizontal',
                'category': category,
                'min_width': 640,
                'per_page': 1,
                'safesearch': 'true'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                hits = data.get('hits', [])
                if hits:
                    photo = hits[0]
                    return {
                        'id': str(photo['id']),
                        'url': photo['webformatURL'],
                        'thumbnail': photo['previewURL'],
                        'alt_text': photo.get('tags', search_term),
                        'attribution': f"Image by {photo['user']} from Pixabay",
                        'photographer': photo['user'],
                        'source': 'pixabay'
                    }
        except Exception as e:
            logger.error(f"Error fetching from Pixabay: {str(e)}")
        
        return None
    
    def _get_pexels_image(self, search_term: str) -> Optional[Dict]:
        """Get image from Pexels API."""
        try:
            url = "https://api.pexels.com/v1/search"
            params = {
                'query': search_term,
                'per_page': 1,
                'orientation': 'landscape'
            }
            headers = {
                'Authorization': self.pexels_key
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                photos = data.get('photos', [])
                if photos:
                    photo = photos[0]
                    return {
                        'id': str(photo['id']),
                        'url': photo['src']['large'],
                        'thumbnail': photo['src']['medium'],
                        'alt_text': photo.get('alt', search_term),
                        'attribution': f"Photo by {photo['photographer']} from Pexels",
                        'photographer': photo['photographer'],
                        'source': 'pexels'
                    }
        except Exception as e:
            logger.error(f"Error fetching from Pexels: {str(e)}")
        
        return None
    
    def _get_placeholder_image(self, search_term: str) -> Dict:
        """Generate a placeholder image."""
        encoded_term = quote(search_term[:20])
        return {
            'id': f'placeholder_{encoded_term}',
            'url': f'https://via.placeholder.com/800x450/4a90e2/ffffff?text={encoded_term}',
            'thumbnail': f'https://via.placeholder.com/400x225/4a90e2/ffffff?text={encoded_term}',
            'alt_text': f'Illustration: {search_term}',
            'attribution': 'Placeholder image',
            'photographer': 'Placeholder Service',
            'source': 'placeholder'
        }
    
    # Include remaining helper methods from the original implementation
    def _split_content_into_sections(self, content: str) -> List[str]:
        """Split content into logical sections."""
        sections = re.split(r'\n(?=#{2,4}\s)', content)
        
        if len(sections) == 1:
            sections = re.split(r'\n\s*\n', content)
        
        return [section.strip() for section in sections if len(section.strip()) > 100]
    
    def _determine_image_type(self, section: str) -> str:
        """Determine the best image type for a section."""
        section_lower = section.lower()
        
        if any(term in section_lower for term in ['example', 'case study', 'scenario']):
            return "example"
        elif any(term in section_lower for term in ['process', 'workflow', 'steps']):
            return "process"
        elif any(term in section_lower for term in ['diagram', 'chart', 'structure']):
            return "diagram"
        elif any(term in section_lower for term in ['tool', 'software', 'interface']):
            return "tool"
        elif any(term in section_lower for term in ['result', 'output', 'visualization']):
            return "result"
        else:
            return "concept"
    
    def _create_textbook_image_html(self, image_data: Dict, section: str, image_number: int) -> str:
        """Create HTML for a textbook-style image with caption."""
        caption = self._generate_image_caption(image_data, section)
        figure_num = f"Figure {image_number}"
        
        html = f'''
<div class="textbook-image">
    <figure class="figure">
        <img src="{image_data['url']}" 
             alt="{image_data['alt_text']}" 
             class="figure-img img-fluid rounded textbook-img"
             loading="lazy">
        <figcaption class="figure-caption">
            <strong>{figure_num}:</strong> {caption}
        </figcaption>
        <div class="image-attribution">
            <small class="text-muted">{image_data['attribution']}</small>
        </div>
    </figure>
</div>
        '''
        return html.strip()
    
    def _generate_image_caption(self, image_data: Dict, section: str) -> str:
        """Generate a meaningful caption for the image."""
        lines = section.split('\n')
        
        for line in lines:
            heading_match = re.match(r'^#{2,6}\s+(.+)$', line.strip())
            if heading_match:
                heading = heading_match.group(1).strip()
                return f"Visual representation of {heading.lower()}"
        
        return f"Supporting visual for {image_data['alt_text']}"
    
    def _insert_image_in_section(self, section: str, image_html: str) -> str:
        """Insert image at the optimal position within a section."""
        lines = section.split('\n')
        insertion_point = 0
        
        in_first_paragraph = False
        for i, line in enumerate(lines):
            line = line.strip()
            
            if re.match(r'^#{2,6}\s+', line):
                insertion_point = i + 1
                continue
            
            if line and not in_first_paragraph:
                in_first_paragraph = True
            elif in_first_paragraph and not line:
                insertion_point = i
                break
            elif i > 5:
                insertion_point = i
                break
        
        lines.insert(insertion_point, '')
        lines.insert(insertion_point + 1, image_html)
        lines.insert(insertion_point + 2, '')
        
        return '\n'.join(lines)


# Singleton instance
textbook_image_service = TextbookImageService()