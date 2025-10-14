"""
Enhanced Course Materials Generation Module - With Image Integration and Tone Selection

This module generates comprehensive, textbook-style course materials with extensive content,
detailed explanations, multiple examples, REAL assessment questions, and integrated educational images.
Maintains all existing functionality while adding professional image integration.
"""

import json
import re
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Groq client and Image Service
from models.groq_client import GroqClient
from models.image_service import EducationalImageService, ImageTracker, ImageData                                                                                 

                                 
class TextbookStyleCourseMaterialsGenerator:
    """Class for generating comprehensive, textbook-style course materials with integrated images and tone selection."""
    
    def __init__(self, design_data: Dict[str, Any]):
        """
        Initialize with the course design data from Phase 2.
        
        Args:
            design_data: Dictionary containing the course design information
        """
        self.design_data = design_data
        self.course_structure = design_data.get("course_structure", "")
        self.instructional_strategies = design_data.get("instructional_strategies", "")
        self.assessment_plan = design_data.get("assessment_plan", "")
        self.task_analysis = design_data.get("task_analysis", "")
        self.audience_analysis = design_data.get("audience_analysis", "")
        self.course_topic = design_data.get("course_topic", "")
        self.audience_type = design_data.get("audience_type", "beginner")
        
        # Initialize image service and tracker
        self.image_service = EducationalImageService()
        self.image_tracker = ImageTracker()                                      
        # Extracted data for easy access
        self.modules = self._extract_modules_from_structure()
        # Image configuration
        self.images_per_module = 3
        self.figure_counter = 1  # Global figure counter across all modules
    def get_tone_instructions(self, tone: str) -> str:
        """
        Get specific instructions for the selected tone.
        
        Args:
            tone: The selected tone ('default', 'optimistic', 'entertaining', 'humanized')
                       
                      
                         
                           
                          
                        
                        
                        
                      
                      
                      
            
        Returns:
            String with tone-specific instructions for content generation
        """
        tone_instructions = {
            'default': """
            TONE: Professional & Academic
            - Use clear, authoritative, and scholarly language
            - Maintain formal tone throughout
            - Focus on comprehensive explanations and technical accuracy
            - Use professional terminology appropriately
            - Present information objectively and systematically
            - Examples should be realistic and professionally relevant
            """,
            
            'optimistic': """
            TONE: Optimistic & Encouraging
            - Use positive, motivational language that encourages learners
            - Emphasize success, growth, and achievement opportunities
            - Frame challenges as exciting learning opportunities
            - Use phrases like "You will master...", "This empowers you to...", "Great opportunity to..."
            - Highlight benefits and positive outcomes regularly
            - Encourage confidence building: "You're building valuable skills..."
            - Use success-oriented language: "achieve", "excel", "succeed", "thrive"
            """,
            
            'entertaining': """
            TONE: Engaging & Entertaining
            - Use creative, fun, and engaging approaches
            - Include analogies, metaphors, and relatable comparisons
            - Add appropriate humor and personality to explanations
            - Use storytelling elements and interesting scenarios
            - Create memorable examples and vivid descriptions
            - Use engaging openings: "Imagine if...", "Picture this...", "Here's a fun way to think about..."
            - Make learning feel like an adventure or discovery
            - Use creative language while maintaining educational value
            """,
            
            'humanized': """
            TONE: Conversational & Personal
            - Write as if speaking directly to a friend or mentee
            - Use first and second person ("I", "you", "we")
            - Include personal insights and relatable experiences
            - Use conversational phrases: "Let me tell you...", "You know how...", "I've found that..."
            - Share tips and advice in a mentoring style
            - Acknowledge common struggles: "I know this can be tricky at first..."
            - Use informal but professional language
            - Create a sense of personal connection and support
            """
        }
        
        return tone_instructions.get(tone, tone_instructions['default'])
                                                          
        
    def sanitize_module_title(self, title: str) -> str:
        replacements = {
            '&': 'and',
            '@': 'at',
            '#': 'sharp',
            '%': 'percent',
            '$': 'dollar',
            '!': 'excl',
            '*': 'star',
            '+': 'plus',
            '=': 'eq',
            '<': 'lt',
            '>': 'gt',
            
        }
        return ''.join(replacements.get(c, c) for c in title)                                                   
    def _extract_modules_from_structure(self) -> List[Dict[str, Any]]:
        """Extract module information from course structure for easier processing."""
        modules = []
        
        # Try to extract modules from the course structure markdown
        if isinstance(self.course_structure, str):
            # Pattern to match module headers like "### Module 1: Title" or "## Module 1: Title"
            #module_pattern = r'#{2,3}\s+Module\s+(\d+):\s+([^\n]+)'
            #module_pattern = r'(?i)#{2,3}\s*Module\s*(\d+)\s*:\s*([^\n]+)'
            module_pattern = r'(?i)#{1,4}\s*\*{0,3}\s*Module\s*(\d+)\s*:\s*([^\n*]+)'                                                                                                                                      
            matches = re.finditer(module_pattern, self.course_structure)
            
            module_positions = []
            
            for match in matches:
                module_num = int(match.group(1))
                module_title = match.group(2).strip()
                module_positions.append({
                    'number': module_num,
                    'title': module_title,
                    'start': match.start(),
                    'match': match
                })
            
            # Extract content for each module
            for i, pos in enumerate(module_positions):
                # Get content between this module and the next (or end)
                start = pos['start']
                if i < len(module_positions) - 1:
                    end = module_positions[i + 1]['start']
                    module_content = self.course_structure[start:end]
                else:
                    module_content = self.course_structure[start:]
                
                # Extract learning objectives
                objectives = []
                obj_pattern = r'(?:Learning Objectives?|Module Learning Objectives?).*?(?=\n(?:Topics?|Key Activities?|Assessment|Module \d+|$))'
                obj_match = re.search(obj_pattern, module_content, re.DOTALL | re.IGNORECASE)
                
                if obj_match:
                    obj_text = obj_match.group(0)
                    obj_items = re.findall(r'[-•*]\s*([^\n]+)', obj_text)
                    objectives = [obj.strip() for obj in obj_items]
                
                # Extract topics
                topics = []
                topics_pattern = r'(?:Topics? Covered?|Key Topics?).*?(?=\n(?:Key Activities?|Assessment|Module \d+|$))'
                topics_match = re.search(topics_pattern, module_content, re.DOTALL | re.IGNORECASE)
                
                if topics_match:
                    topics_text = topics_match.group(0)
                    topic_items = re.findall(r'[-•*]\s*([^\n]+)', topics_text)
                    topics = [topic.strip() for topic in topic_items]
                
                modules.append({
                    "number": pos['number'],
                    #"title": pos['title'],
                    "title": self.sanitize_module_title(pos["title"]),                                                  
                    "objectives": objectives,
                    "topics": topics,
                    "content": module_content
                })
                
        # Fallback: create basic module structure if parsing fails
        if not modules:
            logger.warning("Could not extract modules from course structure. Creating default structure.")
            task_sections = re.findall(r'[A-Z]\.\s+([^\n]+)', str(self.task_analysis))
            num_modules = len(task_sections) if task_sections else 4
            
            for i in range(num_modules):
                modules.append({
                    "number": i + 1,
                    "title": f"Module {i + 1}",
                    "objectives": [],
                    "topics": []
                })
                
        return modules
    
    def _get_image_insertion_points(self, content: str) -> List[Tuple[int, str]]:
        """
        Determine strategic points in the content to insert images.
        
        Args:
            content: The markdown content
            
        Returns:
            List of (position, context) tuples for image insertion
        """
        # Split content into lines for analysis
        lines = content.split('\n')
        insertion_points = []
        
        # Find major sections (headers)
        section_positions = []
        for i, line in enumerate(lines):
            if re.match(r'^#{2,4}\s+', line.strip()):
                section_positions.append((i, line.strip()))
        
        if len(section_positions) >= 3:
            # Strategy: Insert after introduction, middle section, and near end
            # Point 1: After first major section (introduction)
            if len(section_positions) > 0:
                pos = section_positions[0][0] + 3  # 3 lines after header
                context = "introduction"
                insertion_points.append((pos, context))
            
            # Point 2: Middle section
            if len(section_positions) > 2:
                mid_idx = len(section_positions) // 2
                pos = section_positions[mid_idx][0] + 3
                context = "middle_content"
                insertion_points.append((pos, context))
            
            # Point 3: Near end but before summary
            if len(section_positions) > 1:
                # Insert before last section or 3/4 through content
                last_section_pos = section_positions[-2][0] if len(section_positions) > 2 else section_positions[-1][0]
                pos = max(last_section_pos - 5, len(lines) * 3 // 4)
                context = "advanced_content"
                insertion_points.append((pos, context))
        
        else:
            # Fallback: distribute evenly through content
            content_length = len(lines)
            positions = [
                (content_length // 4, "introduction"),
                (content_length // 2, "middle_content"),
                (content_length * 3 // 4, "advanced_content")
            ]
            insertion_points.extend(positions)
        
        return insertion_points
    
    def _create_image_html(self, image_data: ImageData, figure_num: int, context: str, topic: str) -> str:
        """
        Create HTML figure element for an image with proper styling and attribution.
        
        Args:
            image_data: ImageData object containing image information
            figure_num: Figure number for caption
            context: Context where image is being inserted
            topic: Topic for contextual caption
            
        Returns:
            HTML string for the image figure
        """
        # Generate contextual caption based on context and topic
        context_captions = {
            "introduction": f"Overview of {topic} showing key concepts and applications",
            "middle_content": f"Detailed view of {topic} implementation and practical examples", 
            "advanced_content": f"Advanced {topic} techniques and real-world applications"
        }
        
        contextual_caption = context_captions.get(context, f"Educational content related to {topic}")
        
        # Use image title if available and relevant, otherwise use contextual caption
        if image_data.title and len(image_data.title) > 10 and topic.lower() in image_data.title.lower():
            caption_text = image_data.title
        else:
            caption_text = contextual_caption
        
        html = f'''
<div class="textbook-image">
    <figure class="figure">
        <img src="{image_data.url}" alt="{image_data.alt_text}" class="figure-img img-fluid rounded" loading="lazy">
        <figcaption class="figure-caption"><strong>Figure {figure_num}:</strong> {caption_text}</figcaption>
        <div class="image-attribution"><small>{image_data.attribution}</small></div>
    </figure>
</div>
'''
        return html
    
    def _extract_corrected_course_topic_from_audience_analysis(self) -> str:
        """
        Extract the corrected course topic from the audience analysis.
        Falls back to original course topic if extraction fails.
        """
        if not self.audience_analysis:
            return self.course_topic
        
        try:
            # Look for "Course Topic: [Topic Name]" in the audience analysis
            import re
            
            # Pattern to match "Course Topic: Something" or "* Course Topic: Something"
            patterns = [
                r'\*\s*Course Topic:\s*([^\n\r*]+)',  # "* Course Topic: Python Programming"
                r'Course Topic:\s*([^\n\r*]+)',       # "Course Topic: Python Programming"
                r'Topic:\s*([^\n\r*]+)'               # Fallback: "Topic: Python Programming"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, self.audience_analysis, re.IGNORECASE)
                if match:
                    corrected_topic = match.group(1).strip()
                    # Clean up any extra formatting
                    corrected_topic = re.sub(r'[*\[\]]+', '', corrected_topic).strip()
                    
                    if corrected_topic and len(corrected_topic) > 2:
                        logger.info(f"Extracted corrected course topic: '{corrected_topic}' from audience analysis")
                        return corrected_topic
            
            # If no pattern matches, return original
            logger.debug("Could not extract corrected course topic from audience analysis, using original")
            return self.course_topic
            
        except Exception as e:
            logger.warning(f"Error extracting corrected course topic: {e}, using original")
            return self.course_topic
                                                                        
    def _embed_images_in_content(self, content: str, module_number: int, module_title: str) -> str:
        """
        Embed images strategically throughout the content.
        
        Args:
            content: The markdown content
            module_number: Module number for tracking
            module_title: Module title for image search
            
        Returns:
            Content with embedded images
        """
        # Get the corrected course topic from audience analysis
        corrected_topic = self._extract_corrected_course_topic_from_audience_analysis()
                                                               
        # Search for relevant images
        try:
            images = self.image_service.search_educational_images(
                topic= corrected_topic,
                context="education tutorial learning",
                count=self.images_per_module,
                tracker=self.image_tracker
            )
            
            if not images:
                logger.warning(f"No images found for corrected topic '{corrected_topic}' for Module {module_number}: {module_title}")
                return content
            
            # Track the images for this module
            for image in images:
                self.image_tracker.add_image(module_number, image)
            
        except Exception as e:
            logger.error(f"Failed to fetch images for corrected topic '{corrected_topic}' for Module {module_number}: {e}")
            return content
        
        # Find insertion points
        insertion_points = self._get_image_insertion_points(content)
        
        # Split content into lines
        lines = content.split('\n')
        
        # Insert images at strategic points (reverse order to maintain line numbers)
        for i, (image, (line_pos, context)) in enumerate(zip(images, insertion_points)):
            if line_pos < len(lines):
                image_html = self._create_image_html(
                    image, 
                    self.figure_counter, 
                    context, 
                    module_title
                )
                
                # Insert the image HTML
                lines.insert(line_pos + i, image_html)
                self.figure_counter += 1
                
                logger.debug(f"Inserted Figure {self.figure_counter - 1} at line {line_pos} for Module {module_number}")
        
        return '\n'.join(lines)                                                                             
    def generate_all_materials(self, 
                              selected_modules: List[int] = None, 
                              components: List[str] = None,
                              detail_level: str = "comprehensive",
                              content_tone: str = "default",  # NEW: Tone parameter
                              additional_notes: str = "") -> Dict[str, Any]:
        """
        Generate comprehensive textbook-style materials for specified modules with selected tone.
        """
        if selected_modules is None:
            selected_modules = list(range(1, len(self.modules) + 1))
            
        if components is None:
            components = ["lesson_plans", "content", "activities", "assessments", "instructor_guides"]
            
        # Validate tone
        valid_tones = ['default', 'optimistic', 'entertaining', 'humanized']
        if content_tone not in valid_tones:
            content_tone = 'default'               
        # Reset figure counter for this generation
        self.figure_counter = 1                                          
        materials = {
            "metadata": {
                "course_topic": self.course_topic,
                "audience_type": self.audience_type,
                "generated_date": datetime.now().strftime("%B %d, %Y at %H:%M"),
                "detail_level": detail_level,
                "content_tone": content_tone,  # NEW: Store tone in metadata                                  
                "total_modules": len(self.modules),
                "generated_modules": len(selected_modules),
                "style": "comprehensive_textbook_with_images",
                "additional_notes": additional_notes,
                "images_per_module": self.images_per_module
            },
            "modules": []
        }
        
        for module_idx in selected_modules:
            if module_idx < 1 or module_idx > len(self.modules):
                continue
                
            module = self.modules[module_idx - 1]
            module_materials = {
                "number": module_idx, 
                "title": module["title"], 
                "components": {}
            }
            
            logger.info(f"Generating comprehensive materials for Module {module_idx}: {module['title']} in {content_tone} tone")
            
            # Generate content first (needed for assessments)
            module_content = None
            if "content" in components:
                logger.info(f"  - Generating comprehensive textbook content with embedded images in {content_tone} tone...")
                module_content = self.generate_comprehensive_content(module_idx, detail_level, content_tone, additional_notes)
                module_materials["components"]["content"] = module_content
            
            # Generate assessments with real questions based on content
            if "assessments" in components:
                logger.info(f"  - Generating real assessment questions in {content_tone} tone...")
                module_materials["components"]["assessments"] = self.generate_real_assessments(
                    module_idx, detail_level, module_content, content_tone, additional_notes
                )
            
            # Generate other components
            if "lesson_plans" in components:
                logger.info(f"  - Generating detailed lesson plan in {content_tone} tone...")
                module_materials["components"]["lesson_plan"] = self.generate_detailed_lesson_plan(module_idx, detail_level, content_tone, additional_notes)
                
            if "activities" in components:
                logger.info(f"  - Generating extensive activities  in {content_tone} tone...")
                module_materials["components"]["activities"] = self.generate_comprehensive_activities(module_idx, detail_level, content_tone, additional_notes)
                
            if "instructor_guides" in components:
                logger.info(f"  - Generating detailed instructor guide in {content_tone} tone...")
                module_materials["components"]["instructor_guide"] = self.generate_comprehensive_instructor_guide(module_idx, detail_level, content_tone, additional_notes)
                
            materials["modules"].append(module_materials)
            
        return materials
    
    def generate_comprehensive_content(self, module_idx: int,  detail_level: str = "comprehensive", 
                                     content_tone: str = "default", additional_notes: str = "") -> Dict[str, Any]:
        """
        Generate comprehensive, textbook-style instructional content with embedded images.
        """
        if module_idx < 1 or module_idx > len(self.modules):
            return {"error": "Invalid module index"}
            
        module = self.modules[module_idx - 1]
        module_title = module.get("title", f"Module {module_idx}")
        
        # Extract specific task analysis content for this module
        task_content = self._extract_task_content_for_module(module_idx)
        
        # Get tone-specific instructions
        tone_instructions = self.get_tone_instructions(content_tone)
        # Generate comprehensive content
        client = GroqClient()
        
        # Generate main content with more detailed topic coverage
        main_content_prompt = f"""
        You are creating a comprehensive, textbook-style chapter for Module {module_idx}: {module_title} 
        in a {self.audience_type} level course on {self.course_topic}.
        
        {tone_instructions}
        
        IMPORTANT: Apply the tone consistently throughout ALL sections while maintaining educational quality.
        
        

        
        This should be extensive, detailed educational content similar to what you'd find in a professional textbook,
        but written in the specified tone style.
        
        MODULE CONTEXT:
        - Title: {module_title}
        - Learning Objectives: {json.dumps(module.get('objectives', []))}
        - Topics to Cover: {json.dumps(module.get('topics', []))}
        
        TASK ANALYSIS CONTENT:
        {task_content}
        
        AUDIENCE: {self.audience_type} level learners
        
        ADDITIONAL REQUIREMENTS:
        {additional_notes if additional_notes else "No additional requirements specified."}
        Create a comprehensive textbook chapter that includes:
        
        ## Chapter {module_idx}: {module_title}
        
        ### Learning Outcomes
        By the end of this chapter, you will be able to:
        [List 5-7 specific, measurable learning outcomes based on the module objectives]
        
        ### Chapter Overview
        [2-3 paragraph overview of what this chapter covers and why it's important]
        
        ### Introduction
        [Engaging 3-4 paragraph introduction that:
        - Hooks the reader with a real-world scenario or interesting fact
        - Explains the relevance and importance of this topic
        - Previews what will be covered
        - Connects to previous chapters if applicable]
 









 
        
        ### Detailed Topic Coverage
        
        CRITICAL REQUIREMENT: For EACH topic listed in the module topics ({json.dumps(module.get('topics', []))}), 
        create a comprehensive section with clear subsection breaks:
        
        #### [Topic Name from the module topics list]
        
        **Comprehensive Overview**
        [3-4 paragraphs providing a thorough introduction to this specific topic]
        
        **Core Concepts**
        - **Definition**: Clear, precise definition of the topic
        - **Theoretical Foundation**: 2-3 paragraphs explaining the underlying theory
        - **Key Components**: Detailed breakdown of all components (with explanations for each)
        - **How It Works**: Step-by-step explanation of processes or mechanisms
        - **Mathematical/Technical Details**: Any formulas, algorithms, or technical specifications
        
        **Detailed Examples**
        [Provide 2-3 comprehensive examples specifically for this topic:
        - Example 1: Basic/Simple application
        - Example 2: Intermediate/Typical use case  
        - Example 3: Advanced/Complex scenario
        Each example should include setup, process, and outcome]
                                     
                                                                                  
        
                                             
                                                                     
        
        **Practical Applications**
        [2-3 paragraphs on real-world applications of this specific topic]
        
        **Common Challenges and Solutions**
        - Challenge 1: [Description and solution]
        - Challenge 2: [Description and solution]
        - Challenge 3: [Description and solution]
        
        **Best Practices**
        [List of 5-7 best practices for this topic]
        
        **Integration with Other Concepts**
        [How this topic relates to other topics in the module]
        
        ### Synthesis and Integration
        [2-3 paragraphs showing how all topics work together]
        
        ### Practical Implementation Guide
        [Step-by-step guide for implementing the concepts learned]
        
        ### Tools and Resources
                                                          
        
        #### Essential Tools
        [Software, equipment, or resources needed - be specific]
        
        #### Additional Resources
        - Recommended readings
        - Online tutorials
        - Practice platforms
        - Professional communities
        
        ### Chapter Summary
        [Comprehensive summary that reinforces all key points from each topic]
        
        ### Key Terms Glossary
        [All important terms with clear definitions, organized alphabetically]
        
                                                      
                                                                                 
                                                        
                                                        
                                                                                   
                                                                                 
        
        Make this content:
        - EXTREMELY detailed for each topic listed in the module
        - Each topic section should be 800-1200 words
        - Total chapter length should be 8000-12000 words
        - Include specific examples, not generic ones
        - Appropriate for {self.audience_type} level
        - Rich with practical applications
        - Professional and authoritative while maintaining the specified tone
        - Engaging and well-structured
                                                                                     
        
        TONE CONSISTENCY: Every section, explanation, example, and instruction must consistently reflect the {content_tone} tone while maintaining educational effectiveness.
        
        IMPORTANT: Do not skip any topic from the module topics list. Each topic must have its own comprehensive section.
        
        NOTE: Images will be automatically inserted at strategic points in this content, so write flowing, continuous text that can accommodate image integration.
        """
        
        main_content_response = client.generate(main_content_prompt)
        
        # Embed images in the content
        content_with_images = self._embed_images_in_content(
            main_content_response, 
                                
                 
            module_idx, 
                                      
                                  
            module_title
        )                                                               
        # Return structured content
        comprehensive_content = {
            "main_content": content_with_images,  # Content now has embedded images
            "content_structure": {
                "estimated_reading_time": "45-60 minutes",
                "word_count_estimate": "8000-12000 words",
                "complexity_level": self.audience_type,
                "content_tone": content_tone,
 
                "prerequisite_knowledge": self._determine_prerequisites(module_idx),
                "learning_path": self._create_learning_path(module),
                "images_included": self.images_per_module,
                "figure_numbers": list(range(self.figure_counter - self.images_per_module, self.figure_counter))
            },
            "metadata": {
                "module_number": module_idx,
                "module_title": module_title,
                "generated_date": datetime.now().strftime("%B %d, %Y at %H:%M"),
                "detail_level": detail_level,
                "content_type": "comprehensive_textbook_chapter_with_images",
                "content_tone": content_tone,
                "images_embedded": True
            }
        }
        
        return comprehensive_content
    
    def generate_real_assessments(self, module_idx: int, detail_level: str = "comprehensive", 
                                 module_content: Dict[str, Any] = None, content_tone: str = "default",
                                 additional_notes: str = "") -> Dict[str, Any]:
        """
        Generate real assessment questions based on actual module content with specified tone.
        """
        if module_idx < 1 or module_idx > len(self.modules):
            return {"error": "Invalid module index"}
            
        module = self.modules[module_idx - 1]
        module_title = module.get("title", f"Module {module_idx}")
        
        # Get the actual content that was generated
        content_text = ""
        if module_content and "main_content" in module_content:
            content_text = module_content["main_content"]
        else:
            # If no content provided, get task analysis content
            content_text = self._extract_task_content_for_module(module_idx)
        
        # Get tone instructions
        tone_instructions = self.get_tone_instructions(content_tone)                               
        client = GroqClient()
        
        # Generate assessment questions based on actual content
        assessment_prompt = f"""
        You are creating REAL assessment questions based on the ACTUAL CONTENT of Module {module_idx}: {module_title}.
        
        {tone_instructions}
        
        IMPORTANT: While maintaining assessment rigor and accuracy, apply the specified tone to:
        - Question instructions and explanations
        - Feedback and answer explanations
        - Encouraging messages and tips
        - Assessment introductions and conclusions                                                                                                                                 
        Here is the ACTUAL MODULE CONTENT that students will have learned:
        
        {content_text}
        
        ADDITIONAL REQUIREMENTS:
        {additional_notes if additional_notes else "No additional requirements specified."}                                                                                              
        Based on this SPECIFIC CONTENT, create comprehensive assessments that test students on what they actually learned in this module.
        
        ## Comprehensive Assessment Suite for Module {module_idx}: {module_title}
        
        ### 1. Knowledge Check Questions (Based on Content)
        
        Create 15-20 questions that test specific facts, concepts, and information from the module content above.
        
        #### Multiple Choice Questions (8-10 questions)
        
        **Question 1:**
        Based on the module content, [specific question about a concept discussed]?
        a) [Option based on content]
        b) [Option based on content] 
        c) [Option based on content]
        d) [Option based on content]
        
        **Correct Answer:** [Letter] - [Explanation referencing specific part of the content]
        **Content Reference:** [Quote the specific section from the content that supports this answer]
        **Learning Objective Tested:** [Which module objective this tests]
        
        [Continue with 7-9 more multiple choice questions, each based on specific content from the module]
        
        #### True/False Questions (5-6 questions)
        
        **Question 1:**
        True or False: [Statement that can be verified from the module content]
        
        **Correct Answer:** [True/False] - [Explanation with reference to specific content]
        **Content Reference:** [Quote from the module content that proves this answer]
        **Learning Objective Tested:** [Which objective this addresses]
        
        [Continue with 4-5 more True/False questions]
        
        #### Short Answer Questions (4-5 questions)
        
        **Question 1:**
        [Question requiring 2-3 sentence answer based on module content]
        
        **Sample Correct Answer:** [2-3 sentences that demonstrate understanding of the specific content covered]
        **Key Points Required:** [List of key points that must be included for full credit]
        **Content Reference:** [Specific sections of content that contain the answer]
        
        [Continue with 3-4 more short answer questions]
        
        ### 2. Application Questions (Based on Examples from Content)
        
        Create 8-10 questions that ask students to apply concepts from the module content to new situations.
        
        #### Scenario-Based Questions (5-6 questions)
        
        **Question 1:**
        [Present a scenario similar to but different from examples in the content]
        Based on what you learned about [specific concept from content], how would you [apply concept to scenario]?
        
        **Sample Correct Answer:** [Detailed answer showing application of specific concepts from the module]
        **Assessment Rubric:**
        - Excellent (4): [Criteria based on content understanding]
        - Good (3): [Criteria based on content understanding]
        - Satisfactory (2): [Criteria based on content understanding]  
        - Needs Improvement (1): [Criteria based on content understanding]
        **Content Connection:** [How this connects to specific module content]
        
        [Continue with 4-5 more scenario questions]
        
        #### Problem-Solving Questions (3-4 questions)
        
        **Question 1:**
        [Problem that requires using methods/processes taught in the module]
        
        **Step-by-Step Solution:** [Solution using specific techniques from module content]
        **Common Mistakes:** [Mistakes students might make based on content complexity]
        **Full Credit Answer:** [What constitutes a complete, correct answer]
        
        [Continue with 2-3 more problem-solving questions]
        
        ### 3. Analysis and Synthesis Questions
        
        Create 4-5 questions that require students to analyze, compare, or synthesize information from the module.
        
        **Question 1:**
        Compare and contrast [two concepts covered in the module content]. Provide specific examples from the module content.
        
        **Sample Answer:** [Answer that demonstrates understanding of both concepts with specific references to module content]
        **Grading Criteria:** [What elements must be present for full credit]
        **Content References:** [Specific parts of module content students should reference]
        
        ### 4. Practical Assessment Project
        
        Design a hands-on project that requires students to demonstrate mastery of the concepts covered in this specific module.
        
        **Project Description:** [Project that incorporates multiple concepts from the module content]
        
        **Project Requirements:**
        1. [Requirement based on specific module content]
        2. [Requirement based on specific module content]
        3. [Requirement based on specific module content]
        [Continue with 5-8 requirements total]
        
        **Deliverables:**
        - [Specific deliverable that demonstrates understanding]
        - [Specific deliverable that demonstrates understanding]
        - [Specific deliverable that demonstrates understanding]
        
        **Grading Rubric:**
        - **Concept Application (30%):** [How well student applies specific concepts from module]
        - **Technical Accuracy (25%):** [Correctness based on module content standards]
        - **Completeness (20%):** [Coverage of all required module elements]
        - **Quality of Explanation (15%):** [Clear demonstration of understanding]
        - **Innovation/Creativity (10%):** [Going beyond basic requirements while staying true to content]
        
        **Timeline:** [Realistic timeline for completion]
        **Resources Provided:** [What students can use, referencing module content]
        
        ### 5. Self-Assessment Tools
        
        Create tools for students to assess their own understanding of the module content.
        
        #### Knowledge Self-Check (15-20 items)
        Rate your understanding of each concept from the module (1=Don't understand, 5=Fully understand):
        
        1. [Specific concept from module content] (1-5)
        2. [Specific concept from module content] (1-5)
        [Continue with all major concepts covered]
        
        #### Skills Self-Assessment
        Can you do the following based on what you learned in this module? (Yes/No/Partially)
        
        1. [Specific skill taught in module] - [Yes/No/Partially]
        2. [Specific skill taught in module] - [Yes/No/Partially]
        [Continue with all skills covered]
        
        ### 6. Answer Keys and Explanations
        
        For every question above, provide:
        - Complete correct answer
        - Explanation of why it's correct
        - Reference to specific module content
        - Common wrong answers and why they're incorrect
        - Tips for students who get it wrong                                                                             
        CRITICAL REQUIREMENTS:
        1. ALL questions must be answerable using ONLY the module content provided
        2. ALL answers must reference specific parts of the module content
        3. Questions should test understanding of the ACTUAL concepts taught, not general knowledge
        4. Include questions at different difficulty levels appropriate for {self.audience_type} learners
        5. Cover ALL major topics discussed in the module content
        6. Provide complete, detailed answer keys
        7. Make questions specific and relevant to the course topic: {self.course_topic}
        8. Apply {content_tone} tone consistently in all instructions and feedback while maintaining assessment integrity
        """
        
        assessments_response = client.generate(assessment_prompt)
        
        # Generate additional practice questions
        practice_prompt = f"""
        Based on the same module content for Module {module_idx}: {module_title}, create 10 additional practice questions 
        with complete answers that students can use for self-study.
        
        {tone_instructions}   
        These should be similar in style to the assessment questions but focus on reinforcing key concepts.
        Each question should include:
        - The question (presented in {content_tone} tone)
        - Multiple choice options (if applicable)
        - Complete correct answer with explanation (in {content_tone} tone)
        - Reference to specific module content
        - Study tip related to the concept (in {content_tone} tone)
        
        Format as:
        
        ## Practice Questions for Module {module_idx}
        
        **Practice Question 1:**
        [Question based on module content]
        
        **Answer:** [Complete answer with explanation in {content_tone} tone]
        **Content Reference:** [Specific section of module content]
        **Study Tip:** [Helpful tip for remembering this concept in {content_tone} tone]
        
        [Continue for all 10 questions, covering different aspects of the module content]
        """
        
        practice_response = client.generate(practice_prompt)
        
        return {
            "comprehensive_assessments": assessments_response,
            "practice_questions": practice_response,
            "assessment_overview": {
                "total_questions": "35-45 assessment questions + 10 practice questions",
                "content_tone": content_tone,  # NEW: Track tone                             
                "question_types": [
                    "Multiple Choice (8-10 questions)",
                    "True/False (5-6 questions)",
                    "Short Answer (4-5 questions)",
                    "Scenario-Based (5-6 questions)",
                    "Problem-Solving (3-4 questions)",
                    "Analysis/Synthesis (4-5 questions)",
                    "Practice Questions (10 questions)"
                ],
                "assessment_features": [
                    "All questions based on actual module content",
                    "Complete answer keys with explanations",
                    "Content references for each question",
                    "Practical application project",
                    "Self-assessment tools",
                    "Grading rubrics included",
                    f"All instructions in {content_tone} tone"
                ],
                "estimated_assessment_time": "2-3 hours for full assessment suite"
            },
            "metadata": {
                "module_number": module_idx,
                "module_title": module_title,
                "generated_date": datetime.now().strftime("%B %d, %Y at %H:%M"),
                "detail_level": detail_level,
                "assessment_type": "content_based_real_questions",
                "content_tone": content_tone,  # NEW: Store tone           
                "content_based": True
            }
        }
    
    def generate_detailed_lesson_plan(self, module_idx: int, detail_level: str = "comprehensive",
                                    content_tone: str = "default", additional_notes: str = "") -> Dict[str, Any]:
        """
        Generate a detailed lesson plan for comprehensive content delivery with specified tone.
        """
        if module_idx < 1 or module_idx > len(self.modules):
            return {"error": "Invalid module index"}
            
        module = self.modules[module_idx - 1]
        module_title = module.get("title", f"Module {module_idx}")
        
        tone_instructions = self.get_tone_instructions(content_tone)
        
        client = GroqClient()
        
        prompt = f"""
        Create a comprehensive lesson plan for delivering the extensive content of Module {module_idx}: {module_title}.
        
        {tone_instructions}
        
        IMPORTANT: Incorporate the specified tone into:
        - Instructor guidance and facilitation notes
        - Student interaction suggestions
        - Activity descriptions and instructions
        - Assessment and feedback approaches
        
        This lesson plan should accommodate the delivery of rich, textbook-style content to {self.audience_type} level learners.
        
        ADDITIONAL REQUIREMENTS:
        {additional_notes if additional_notes else "No additional requirements specified."}
        
        ## Comprehensive Lesson Plan: {module_title}
        
        ### Session Overview
        - **Duration**: 3-4 hours (with breaks) or split into 2-3 shorter sessions
        - **Format**: Interactive lecture with extensive engagement
        - **Materials**: Comprehensive content, multimedia, hands-on materials
        - **Tone Style**: {content_tone} - maintain consistently throughout session
        
        ### Pre-Session Preparation (60-90 minutes)
                                                                
                                                               
                                                                             
        
        #### Instructor Preparation
        - Review all chapter content thoroughly
        - Prepare multimedia presentations
        - Set up interactive elements
        - Prepare handouts and materials
        - Test all technology
        - Practice {content_tone} tone delivery style
        
        #### Student Preparation
        - Pre-reading assignments (with {content_tone} tone instructions)
        - Prerequisite knowledge check
        - Preparation materials to review
        
        ### Detailed Session Structure
        
        #### Opening Phase (20-30 minutes)
        1. **Welcome and Objectives** (5 minutes)
           - Clear learning outcomes (presented in {content_tone} tone)
           - Session roadmap
           - Expectation setting
        
        2. **Engagement Hook** (10-15 minutes)
           - Real-world scenario or case (delivered in {content_tone} tone)
           - Interactive discussion
           - Problem-based opener
        
        3. **Knowledge Activation** (10 minutes)
           - Prior knowledge assessment
           - Connection to previous modules
           - Mental preparation for new content
        
        #### Core Content Delivery (120-150 minutes)
        
        **Segment 1: Foundational Concepts** (40-50 minutes)
        - Detailed content delivery method (using {content_tone} tone)
        - Interactive elements every 10-15 minutes
        - Visual aids and demonstrations
        - Check for understanding
        - Q&A opportunities
        
        **Break** (10-15 minutes)
        
        **Segment 2: Advanced Applications** (40-50 minutes)
        - Case study analysis (presented in {content_tone} tone)
        - Hands-on exercises
        - Group work and discussions
        - Problem-solving activities
        
        **Break** (10-15 minutes)
        
        **Segment 3: Practical Implementation** (40-50 minutes)
        - Real-world applications (explained in {content_tone} tone)
        - Tool demonstrations
        - Practice opportunities
        - Skill development activities
        
        #### Integration and Assessment (30-40 minutes)
        1. **Synthesis Activities** (15-20 minutes)
           - Concept mapping
           - Summary creation
           - Peer teaching (using {content_tone} tone)
        
        2. **Formative Assessment** (10-15 minutes)
           - Quick comprehension checks
           - Application exercises
           - Self-assessment tools
        
        3. **Wrap-up and Preview** (5-10 minutes)
           - Key takeaways summary (in {content_tone} tone)
           - Next session preview
           - Assignment of follow-up work
        
        ### Instructional Strategies for Each Phase
        
        #### Content Delivery Techniques
        - **Chunking**: Break complex content into digestible segments
        - **Scaffolding**: Build complexity gradually
        - **Multimodal**: Use visual, auditory, and kinesthetic approaches
        - **Interactive**: Engage every 10-15 minutes
        - **Contextual**: Provide real-world connections
        - **Tone Consistency**: Maintain {content_tone} tone throughout
        
        #### Engagement Strategies (in {content_tone} tone)
        - Think-pair-share activities
        - Polling and voting
        - Breakout discussions
        - Hands-on demonstrations
        - Case study analysis
        - Role-playing scenarios
        
        ### Assessment Integration
        
        #### Continuous Assessment (using {content_tone} tone for feedback)
        - Exit tickets after each segment
        - Real-time polling
        - Observation checklists
        - Peer feedback
        
        #### Culminating Assessment
        - Comprehensive application task
        - Portfolio development
        - Presentation or demonstration
        
        ### Differentiation Strategies
        
        #### For Advanced Learners
        - Extension activities (presented in {content_tone} tone)
        - Leadership roles
        - Additional challenges
        - Independent projects
        
        #### For Struggling Learners
        - Additional support materials (in {content_tone} tone)
        - Peer partnerships
        - Simplified explanations
        - Extra practice time
        
        ### Technology Integration
        - Interactive presentations
        - Online collaboration tools
        - Multimedia resources
        - Digital assessment tools
        - Virtual simulations
        
        ### Materials and Resources Needed
        
        #### Essential Materials
        [Comprehensive list of everything needed]
        
        #### Optional Enhancements
        [Additional materials that could improve the experience]
        
        ### Timing Flexibility
        
        #### Extended Format (3-4 hours)
        [Detailed breakdown for full session]
        
        #### Split Format (2-3 shorter sessions)
        [How to divide content across multiple sessions]
        
        #### Compressed Format (1.5-2 hours)
        [Essential elements if time is limited]
        
        ### Follow-up Activities
        - Homework assignments (instructions in {content_tone} tone)
        - Independent study guides
        - Peer collaboration projects
        - Real-world application tasks
        
        ### Tone Implementation Guide for Instructors
        
        #### Maintaining {content_tone.title()} Tone
        - Specific phrases and language patterns to use
        - Examples of appropriate explanations in this tone
        - Student interaction strategies that support the tone
        - Methods for providing encouraging feedback
        
        Create a lesson plan that can effectively deliver comprehensive, textbook-level content while maintaining high engagement and the {content_tone} tone consistently.
        """
        
        lesson_plan_response = client.generate(prompt)
        
        return {
            "comprehensive_lesson_plan": lesson_plan_response,
            "metadata": {
                "module_number": module_idx,
                "module_title": module_title,
                "generated_date": datetime.now().strftime("%B %d, %Y at %H:%M"),
                "detail_level": detail_level,
                "content_tone": content_tone,
                "session_duration": "3-4 hours or multiple shorter sessions",
                "preparation_time": "60-90 minutes"
                                                                                               
            }
        }
    
    def generate_comprehensive_activities(self, module_idx: int, detail_level: str = "comprehensive",
                                        content_tone: str = "default", additional_notes: str = "") -> Dict[str, Any]:
        """
        Generate extensive learning activities for comprehensive content with specified tone.
        """
        if module_idx < 1 or module_idx > len(self.modules):
            return {"error": "Invalid module index"}
            
        module = self.modules[module_idx - 1]
        module_title = module.get("title", f"Module {module_idx}")
        
        tone_instructions = self.get_tone_instructions(content_tone)
        
        client = GroqClient()
        
        prompt = f"""
        Create a comprehensive collection of learning activities for Module {module_idx}: {module_title}.
        
        {tone_instructions}
        
        IMPORTANT: Apply the specified tone to:
        - Activity instructions and descriptions
        - Facilitation guidance
        - Student interaction prompts
        - Assessment criteria and feedback
        
        These activities should support the delivery and reinforcement of extensive, textbook-style content.
        
        ADDITIONAL REQUIREMENTS:
        {additional_notes if additional_notes else "No additional requirements specified."}
        
        Generate 8-12 diverse activities that include:
        
        ### Category 1: Content Engagement Activities (2-3 activities)
        
        #### Activity: Interactive Content Exploration
        - **Type**: Guided Discovery
        - **Duration**: 25-30 minutes
        - **Purpose**: Deep engagement with core concepts (explained in {content_tone} tone)
        - **Materials**: Content chunks, exploration guides
        - **Process**: 
          1. Divide content into exploration stations
          2. Students rotate through stations
          3. Each station focuses on one key concept
          4. Interactive elements at each station
          5. Synthesis discussion at the end
        - **Assessment**: Concept mapping completion
        - **Technology**: QR codes for multimedia content
        - **Instructor Notes**: [Guidance for maintaining {content_tone} tone during facilitation]
        
        ### Category 2: Application Activities (3-4 activities)
        
        #### Activity: Real-World Case Analysis
        - **Type**: Case Study Analysis
        - **Duration**: 45-60 minutes
        - **Purpose**: Apply concepts to authentic scenarios (presented in {content_tone} tone)
        - **Materials**: Detailed case studies, analysis frameworks
        - **Process**:
          1. Present complex, multi-faceted case
          2. Teams analyze different aspects
          3. Apply module concepts to case
          4. Develop solutions or recommendations
          5. Present findings to class
        - **Assessment**: Solution quality and reasoning
        - **Extensions**: Additional cases, alternative solutions
        - **Tone Integration**: [Specific ways to maintain {content_tone} throughout activity]
        
        ### Category 3: Collaborative Learning Activities (2-3 activities)
        
        #### Activity: Expert Groups and Teaching
        - **Type**: Jigsaw Method
        - **Duration**: 50-70 minutes
        - **Purpose**: Deep learning through teaching others (facilitated in {content_tone} tone)
        - **Materials**: Expert topic assignments, teaching resources
        - **Process**:
          1. Assign expert topics to groups
          2. Expert groups master their topic
          3. Prepare teaching materials
          4. Teach other groups their topic (using {content_tone} approach)
          5. All groups learn about all topics
        - **Assessment**: Teaching effectiveness and peer learning
        - **Technology**: Collaborative digital tools
        - **Tone Guidelines**: [How to encourage students to use {content_tone} in their teaching]
        
        ### Category 4: Skill Development Activities (2-3 activities)
        
        #### Activity: Progressive Skill Building
        - **Type**: Scaffolded Practice
        - **Duration**: 40-60 minutes
        - **Purpose**: Build competency in key skills (guided with {content_tone} support)
        - **Materials**: Practice scenarios, skill checklists
        - **Process**:
          1. Demonstrate skill components
          2. Guided practice with feedback (in {content_tone} tone)
          3. Independent practice
          4. Peer review and feedback
          5. Skill demonstration
        - **Assessment**: Skill demonstration rubric
        - **Differentiation**: Multiple difficulty levels
        - **Encouragement Strategies**: [Ways to provide {content_tone} feedback and support]
        
        ### Category 5: Creative and Critical Thinking Activities (1-2 activities)
        
        #### Activity: Innovation Challenge
        - **Type**: Design Thinking
        - **Duration**: 60-90 minutes
        - **Purpose**: Creative application of concepts (facilitated in {content_tone} tone)
        - **Materials**: Design thinking templates, prototyping materials
        - **Process**:
          1. Present innovation challenge
          2. Empathize and define problems
          3. Ideate solutions using module concepts
          4. Prototype and test ideas
          5. Present innovations
        - **Assessment**: Innovation quality and concept integration
        - **Extensions**: Implementation planning
        - **Motivation Techniques**: [How to inspire creativity using {content_tone} approach]
        
        For each activity, provide:
        
        ### Detailed Implementation Guide
        - Pre-activity setup
        - Step-by-step facilitation (maintaining {content_tone} tone)
        - Timing for each phase
        - Materials checklist
        - Technology requirements
        - Assessment methods
        - Troubleshooting tips
        - Variations and extensions
        
        ### Differentiation Options
        - Advanced learner challenges (presented in {content_tone} tone)
        - Support for struggling learners (using {content_tone} encouragement)
        - Cultural adaptations
        - Technology alternatives
        
        ### Integration with Content
        - Specific concepts reinforced
        - Learning objectives addressed
        - Connection to other activities
        - Assessment alignment
        
        ### Tone Implementation Strategies
        - Specific language patterns for {content_tone} facilitation
        - Ways to encourage student engagement within the tone framework
        - Methods for providing tone-appropriate feedback
        - Techniques for maintaining tone consistency throughout activities
        
        Create activities that are engaging, educationally sound, and appropriate for {self.audience_type} learners dealing with comprehensive content, all delivered in the {content_tone} tone.
        """
        
        activities_response = client.generate(prompt)
        
        return {
            "comprehensive_activities": activities_response,
            "activity_overview": {
                "total_activities": "8-12 diverse activities",
                "content_tone": content_tone,
                "categories": [
                    "Content Engagement",
                    "Application",
                    "Collaborative Learning", 
                    "Skill Development",
                    "Creative and Critical Thinking"
                ],
                "estimated_total_time": "4-6 hours",
                "recommended_usage": "Select 3-5 activities per session based on learning objectives",
                "tone_integration": f"All activities designed with {content_tone} tone facilitation"
            },
            "metadata": {
                "module_number": module_idx,
                "module_title": module_title,
                "generated_date": datetime.now().strftime("%B %d, %Y at %H:%M"),
                "detail_level": detail_level,
                "content_tone": content_tone,
                "activity_complexity": "comprehensive"
            }
        }
    
    def generate_comprehensive_instructor_guide(self, module_idx: int, detail_level: str = "comprehensive",
                                              content_tone: str = "default", additional_notes: str = "") -> Dict[str, Any]:
        """
        Generate detailed instructor guide for comprehensive content delivery with tone implementation.
        """
        if module_idx < 1 or module_idx > len(self.modules):
            return {"error": "Invalid module index"}
            
        module = self.modules[module_idx - 1]
        module_title = module.get("title", f"Module {module_idx}")
        
        tone_instructions = self.get_tone_instructions(content_tone)
        
        client = GroqClient()
        
        prompt = f"""
        Create a comprehensive instructor guide for delivering extensive, textbook-style content for Module {module_idx}: {module_title}.
        
        {tone_instructions}
        
        IMPORTANT: This guide should help instructors effectively deliver content in the {content_tone} tone by providing:
        - Specific guidance on maintaining the tone throughout instruction
        - Examples of how to present content in the specified tone
        - Strategies for encouraging student engagement within the tone framework
        - Methods for providing feedback and assessment in the specified tone
        
        This guide should support instructors in effectively delivering rich, detailed educational content to {self.audience_type} level learners.
        
        ADDITIONAL REQUIREMENTS:
        {additional_notes if additional_notes else "No additional requirements specified."}
        
        ## Comprehensive Instructor Guide: {module_title}
        
        ### Module Overview for Instructors
        
        #### Content Scope and Depth
        - **Estimated Content Volume**: 8,000-12,000 words equivalent
        - **Reading Time**: 45-60 minutes for students
        - **Teaching Time**: 3-4 hours or multiple sessions
        - **Complexity Level**: {self.audience_type} with comprehensive depth
        - **Content Tone**: {content_tone} - must be maintained consistently
        - **Prerequisites**: [List essential prerequisite knowledge]
        - **Integrated Images**: {self.images_per_module} educational images included in content
        
        #### Key Teaching Challenges
        - Managing extensive content without overwhelming students
        - Maintaining engagement throughout lengthy sessions
        - Ensuring deep understanding vs. surface coverage
        - Balancing theory with practical application
        - Accommodating different learning paces
        - Consistently applying {content_tone} tone throughout instruction
        - Effectively using integrated images for enhanced learning
        
        ### Pre-Instruction Preparation (2-3 Hours)
        
        #### Content Mastery Preparation
        1. **Deep Content Review** (60-90 minutes)
           - Read all content materials thoroughly
           - Identify key concepts and relationships
           - Note potential student difficulty areas
           - Prepare additional examples in {content_tone} style
           - Research current applications
           - Review integrated images and their educational purpose
        
        2. **Tone Preparation** (30-45 minutes)
           - Practice delivering content in {content_tone} tone
           - Prepare tone-appropriate examples and analogies
           - Develop {content_tone} feedback strategies
           - Plan tone-consistent student interactions
        
        3. **Instructional Planning** (45-60 minutes)
           - Plan content chunking strategy
           - Design engagement checkpoints
           - Prepare multimedia elements
           - Set up interactive components
           - Plan assessment touchpoints
           - Plan how to reference and discuss integrated images
        
        4. **Material and Technology Setup** (30-45 minutes)
           - Test all technology components
           - Prepare handouts and resources
           - Set up learning environment
           - Organize materials for easy access
           - Prepare backup plans
           - Ensure image display capabilities
        
        ### {content_tone.title()} Tone Implementation Guide
        
        #### Core Tone Principles for {content_tone.title()} Delivery
        [Specific guidelines for maintaining {content_tone} tone]
        
        #### Language Patterns and Phrases
        - **Recommended phrases**: [List of {content_tone}-appropriate phrases for instruction]
        - **Avoid these phrases**: [Language patterns that conflict with {content_tone} tone]
        - **Transition phrases**: [How to move between topics while maintaining tone]
        - **Question framing**: [How to ask questions in {content_tone} style]
        
        #### Tone-Specific Teaching Strategies
        
        **For {content_tone.title()} Tone:**
        - Content delivery methods that support this tone
        - Student interaction approaches
        - Feedback and encouragement strategies
        - Error correction techniques that maintain tone
        - Ways to handle difficult or resistant students while staying in tone
        
        #### Examples of Tone Implementation
        
        **Explaining Complex Concepts in {content_tone.title()} Tone:**
        [Specific examples of how to explain difficult concepts using {content_tone} approach]
        
        **Providing Feedback in {content_tone.title()} Tone:**
        [Examples of constructive feedback delivery using {content_tone} style]
        
        **Encouraging Participation in {content_tone.title()} Tone:**
        [Strategies for drawing out quiet students using {content_tone} approach]
        
        ### Content Delivery Strategies
        
        #### Chunking Strategy for Extensive Content
        **Chunk 1: Foundation Building** (45-60 minutes)
        - **Content Focus**: Core concepts and definitions
        - **Delivery Method**: Interactive lecture with frequent checks (in {content_tone} tone)
        - **Engagement**: Every 10-15 minutes
        - **Assessment**: Quick comprehension checks
        - **Transition**: Clear bridge to next chunk
        - **Tone Application**: [Specific ways to apply {content_tone} in this phase]
        - **Image Integration**: Reference Figure 1 to enhance understanding
        
        **Chunk 2: Deep Dive Analysis** (45-60 minutes)
        - **Content Focus**: Detailed explanations and examples
        - **Delivery Method**: Guided exploration and discussion (using {content_tone} facilitation)
        - **Engagement**: Case studies and scenarios
        - **Assessment**: Application exercises
        - **Transition**: Synthesis activity
        - **Tone Application**: [How to maintain {content_tone} during complex explanations]
        - **Image Integration**: Use Figure 2 to illustrate key processes
        
        **Chunk 3: Practical Application** (45-60 minutes)
        - **Content Focus**: Real-world applications and skills
        - **Delivery Method**: Hands-on activities and practice (with {content_tone} support)
        - **Engagement**: Interactive exercises
        - **Assessment**: Performance demonstrations
        - **Transition**: Integration and summary
        - **Tone Application**: [Ways to encourage practice using {content_tone} approach]
        - **Image Integration**: Reference Figure 3 for advanced applications
        
        #### Engagement Maintenance Strategies (with {content_tone.title()} Tone)
        
        **Every 10-15 Minutes**:
        - Pose reflection questions (framed in {content_tone} style)
        - Quick pair-share activities
        - Polling or voting
        - Stand and stretch breaks
        - Concept check quizzes (with {content_tone} feedback)
        - Reference integrated images for visual reinforcement
        
        **Every 30-45 Minutes**:
        - Major activity or exercise (facilitated in {content_tone} tone)
        - Group discussions
        - Case study analysis
        - Problem-solving scenarios
        - Application challenges
        - Image-based discussions and analysis
        
        **Every 60-90 Minutes**:
        - Formal break (10-15 minutes)
        - Energy re-engagement activity (using {content_tone} motivation)
        - Major transition activity
        - Progress assessment
        - Goal refocusing (with {content_tone} encouragement)
        
        ### Image Integration and Utilization
        
        #### Effective Use of Integrated Images
        - **Figure References**: How to naturally reference figures during instruction
        - **Visual Learning**: Using images to support different learning styles
        - **Discussion Prompts**: Questions to ask about images to deepen understanding
        - **Accessibility**: Ensuring image descriptions support all learners
        
        #### Image-Based Activities
        - **Figure Analysis**: Students analyze and discuss what they see
        - **Concept Mapping**: Connect images to key concepts being taught
        - **Comparison Activities**: Compare figures to identify patterns
        - **Real-World Connections**: Link images to student experiences
        
        ### Assessment Integration and Management
        
        #### Real-Time Assessment Strategies (using {content_tone} tone)
        - **Content-Based Questions**: Use actual module content for immediate checks
        - **Application Scenarios**: Test understanding through real examples
        - **Peer Teaching**: Students explain concepts to each other (using {content_tone} approach)
        - **Quick Quizzes**: 3-5 questions based on just-covered material
        - **Exit Tickets**: Summary of key learnings and questions
        - **Image-Based Questions**: Use integrated figures for visual assessment
        
        #### Assessment Data Management
        - Real-time tracking methods
        - Quick documentation strategies
        - Student progress monitoring
        - Intervention decision points
        - Feedback delivery systems (using {content_tone} approach)
        
        ### Technology Integration Guide
        
        #### Essential Technology Tools
        - **Presentation Software**: Advanced features usage
        - **Polling Tools**: Real-time engagement
        - **Collaboration Platforms**: Group work management
        - **Assessment Tools**: Quick check systems
        - **Multimedia Tools**: Rich content delivery
        - **Image Display**: High-quality image presentation
        
        #### Technology Troubleshooting
        - Common issues and solutions
        - Backup delivery methods
        - Student technology support (provided in {content_tone} manner)
        - Accessibility considerations
        - Emergency procedures
        - Image display backup plans
        
        ### Student Support Strategies (using {content_tone.title()} Tone)
        
        #### For Overwhelmed Students
        - Content chunking reminders (delivered with {content_tone} support)
        - Study strategy guidance
        - Additional support resources
        - One-on-one check-ins (using {content_tone} approach)
        - Stress management techniques
        - Visual learning support through images
        
        #### For Advanced Students
        - Extension challenges (presented in {content_tone} tone)
        - Leadership opportunities
        - Independent exploration
        - Peer teaching roles
        - Advanced applications
        - Additional image analysis activities
        
        #### For Struggling Students
        - Prerequisite review (with {content_tone} encouragement)
        - Simplified explanations (maintaining {content_tone} tone)
        - Additional examples
        - Extra practice time
        - Alternative assessments
        - Visual learning support through integrated images
        
        ### Tone-Specific Troubleshooting
        
        #### When Students Don't Respond to {content_tone.title()} Tone
        - Alternative approaches while maintaining core tone principles
        - Ways to adjust tone intensity without losing authenticity
        - Strategies for different personality types
        - Cultural sensitivity considerations
        
        #### Maintaining Tone During Difficult Moments
        - Handling student resistance using {content_tone} approach
        - Dealing with disruptive behavior while staying in character
        - Managing time pressure without abandoning tone
        - Handling technical difficulties gracefully
        
        ### Quality Assurance Checklist
        
        #### Before Each Session
        - [ ] Content thoroughly reviewed
        - [ ] {content_tone.title()} tone examples prepared
        - [ ] All materials ready
        - [ ] Technology tested
        - [ ] Environment set up
        - [ ] Backup plans ready
        - [ ] Tone delivery practiced
        - [ ] Image display verified
        
        #### During Each Session
        - [ ] {content_tone.title()} tone maintained consistently
        - [ ] Engagement every 10-15 minutes
        - [ ] Regular comprehension checks
        - [ ] Time management monitoring
        - [ ] Student energy assessment
        - [ ] Tone-appropriate adjustments implemented
        - [ ] Images referenced effectively
        
        #### After Each Session
        - [ ] Student feedback collected (using {content_tone} approach)
        - [ ] Assessment data reviewed
        - [ ] Session effectiveness evaluated
        - [ ] Tone consistency self-assessed
        - [ ] Improvements identified
        - [ ] Next session prepared
        - [ ] Image effectiveness evaluated
        
        ### Assessment Answer Keys and Guidance
        
        #### Using Real Assessment Questions with {content_tone.title()} Tone
        - How to integrate content-based questions during instruction
        - Techniques for creating spontaneous questions from content
        - Methods for checking student understanding of specific concepts
        - Strategies for providing immediate feedback in {content_tone} style
        
        #### Grading Comprehensive Assessments
        - Guidelines for evaluating content-based responses
        - Rubrics for application and analysis questions
        - Methods for providing meaningful feedback in {content_tone} tone
        - Strategies for identifying and addressing knowledge gaps
        
        
        ### Professional Development for {content_tone.title()} Tone Mastery
        
        #### Self-Assessment Tools
        - Tone consistency checklist
        - Student feedback analysis
        - Video review techniques
        - Peer observation forms
        
        #### Continuous Improvement
        - Ways to refine {content_tone} delivery
        - Student response monitoring
        - Adaptation strategies
        - Advanced tone techniques
        
        Create an instructor guide that empowers educators to deliver comprehensive, engaging, and effective instruction with extensive content while maintaining the {content_tone} tone consistently and ensuring real learning occurs.
        """
        
        instructor_guide_response = client.generate(prompt)
        
        return {
            "comprehensive_instructor_guide": instructor_guide_response,
            "guide_overview": {
                "preparation_time": "2-3 hours",
                "delivery_time": "3-4 hours or multiple sessions",
                "content_tone": content_tone,
                "key_features": [
                    "Content chunking strategies",
                    "Engagement maintenance",
                    "Real-time assessment integration",
                    "Technology support",
                    "Student support strategies",
                    "Assessment guidance",
                    f"Complete {content_tone} tone implementation guide",
                    "Image integration strategies"
                ],
                "support_level": "comprehensive",
                "tone_support": f"Detailed guidance for consistent {content_tone} tone delivery",
                "visual_support": "Guidance for effective use of integrated educational images"
            },
            "metadata": {
                "module_number": module_idx,
                "module_title": module_title,
                "generated_date": datetime.now().strftime("%B %d, %Y at %H:%M"),
                "detail_level": detail_level,
                "content_tone": content_tone,
                "guide_type": "comprehensive_delivery_with_tone_and_images"
            }
        }
    def save_materials(self, materials: Dict[str, Any], filepath: str) -> None:
        """
        Save generated materials to a file.
        
        Args:
            materials: Dictionary containing all generated materials
            filepath: Path to save the materials to
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(materials, f, indent=2)
            
    @staticmethod
    def load_materials(filepath: str) -> Dict[str, Any]:
        """
        Load previously generated materials from a file.
        
        Args:
            filepath: Path to load the materials from
            
        Returns:
            Dictionary containing the loaded materials
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Helper Methods
    def _extract_task_content_for_module(self, module_idx: int) -> str:
        """Extract relevant task analysis content for a specific module."""
        if not self.task_analysis:
            return "No task analysis available"
        
        task_analysis_str = str(self.task_analysis) if self.task_analysis else ""
        
        # Map module index to task analysis sections (A, B, C, etc.)
        section_letter = chr(64 + module_idx)  # 1->A, 2->B, etc.
        
        # Try to find the section in task analysis
        section_pattern = f"{section_letter}\\. [^\\n]+.*?(?=[A-Z]\\. |$)"
        match = re.search(section_pattern, task_analysis_str, re.DOTALL)
        
        if match:
            return match.group(0)
        else:
            return f"Task content for module {module_idx} - comprehensive coverage of {self.course_topic} concepts"
    
    def _determine_prerequisites(self, module_idx: int) -> List[str]:
        """Determine prerequisite knowledge for a module."""
        prerequisites = []
        
        if module_idx > 1:
            prerequisites.append(f"Completion of Module {module_idx - 1}")
        
        # Add general prerequisites based on course topic and audience level
        if self.audience_type == "beginner":
            prerequisites.append("Basic computer literacy")
            prerequisites.append("High school level mathematics")
        elif self.audience_type == "intermediate":
            prerequisites.append("Foundational knowledge in the subject area")
            prerequisites.append("Some practical experience")
        elif self.audience_type == "advanced":
            prerequisites.append("Extensive background in the field")
            prerequisites.append("Professional experience")
        
        return prerequisites
    
    def _create_learning_path(self, module: Dict) -> Dict[str, Any]:
        """Create a learning path for the module."""
        return {
            "estimated_study_time": "4-6 hours for thorough understanding",
            "recommended_approach": "Read, practice, apply, assess",
            "support_resources": "Additional examples, practice exercises, peer discussions",
            "mastery_indicators": [
                "Can explain all key concepts clearly",
                "Can apply concepts to new situations", 
                "Can identify and correct common mistakes",
                "Can teach concepts to others"
            ]
        }


# Updated helper function with tone and image support
def generate_course_materials(design_data: Dict[str, Any], 
                             selected_modules: List[int] = None,
                             components: List[str] = None,
                             detail_level: str = "comprehensive",
                             content_tone: str = "default",
                             additional_notes: str = "") -> Dict[str, Any]:
    """
    Generate comprehensive, textbook-style course materials with real assessment questions, 
    tone selection, and integrated educational images.
    
    Args:
        design_data: Course design data from Phase 2
        selected_modules: List of module indexes to generate materials for
        components: List of component types to generate
        detail_level: Level of detail for generation
        content_tone: Tone style for content generation ('default', 'optimistic', 'entertaining', 'humanized')
        additional_notes: Additional requirements or customization notes
        
    Returns:
        Dictionary containing comprehensive generated materials with specified tone and images
    """
    generator = TextbookStyleCourseMaterialsGenerator(design_data)
    return generator.generate_all_materials(selected_modules, components, detail_level, content_tone, additional_notes)

# Backward compatibility - keep the original class name as an alias
class CourseMaterialsGenerator(TextbookStyleCourseMaterialsGenerator):
    """Alias for backward compatibility."""
    pass