"""
Enhanced Course Materials Generation Module - With Real Assessment Questions

This module generates comprehensive, textbook-style course materials with extensive content,
detailed explanations, multiple examples, and REAL assessment questions based on actual module content.
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

# Import Groq client
from models.groq_client import GroqClient


class TextbookStyleCourseMaterialsGenerator:
    """Class for generating comprehensive, textbook-style course materials with real assessments."""
    
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
        
        # Extracted data for easy access
        self.modules = self._extract_modules_from_structure()
        
    def _extract_modules_from_structure(self) -> List[Dict[str, Any]]:
        """Extract module information from course structure for easier processing."""
        modules = []
        
        # Try to extract modules from the course structure markdown
        if isinstance(self.course_structure, str):
            # Pattern to match module headers like "### Module 1: Title" or "## Module 1: Title"
            module_pattern = r'#{2,3}\s+Module\s+(\d+):\s+([^\n]+)'
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
                    "title": pos['title'],
                    "objectives": objectives,
                    "topics": topics,
                    "content": module_content
                })
                
        # Fallback: create basic module structure if parsing fails
        if not modules:
            logger.warning("Could not extract modules from course structure. Creating default structure.")
            task_sections = re.findall(r'[A-Z]\.\s+([^\n]+)', self.task_analysis)
            num_modules = len(task_sections) if task_sections else 4
            
            for i in range(num_modules):
                modules.append({
                    "number": i + 1,
                    "title": f"Module {i + 1}",
                    "objectives": [],
                    "topics": []
                })
                
        return modules
    
    def generate_all_materials(self, 
                              selected_modules: List[int] = None, 
                              components: List[str] = None,
                              detail_level: str = "comprehensive") -> Dict[str, Any]:
        """
        Generate comprehensive textbook-style materials for specified modules.
        """
        if selected_modules is None:
            selected_modules = list(range(1, len(self.modules) + 1))
            
        if components is None:
            components = ["lesson_plans", "content", "activities", "assessments", "instructor_guides"]
            
        materials = {
            "metadata": {
                "course_topic": self.course_topic,
                "audience_type": self.audience_type,
                "generated_date": datetime.now().strftime("%B %d, %Y at %H:%M"),
                "detail_level": detail_level,
                "total_modules": len(self.modules),
                "generated_modules": len(selected_modules),
                "style": "comprehensive_textbook"
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
            
            logger.info(f"Generating comprehensive materials for Module {module_idx}: {module['title']}")
            
            # Generate content first (needed for assessments)
            module_content = None
            if "content" in components:
                logger.info(f"  - Generating comprehensive textbook content...")
                module_content = self.generate_comprehensive_content(module_idx, detail_level)
                module_materials["components"]["content"] = module_content
            
            # Generate assessments with real questions based on content
            if "assessments" in components:
                logger.info(f"  - Generating real assessment questions...")
                module_materials["components"]["assessments"] = self.generate_real_assessments(
                    module_idx, detail_level, module_content
                )
            
            # Generate other components
            if "lesson_plans" in components:
                logger.info(f"  - Generating detailed lesson plan...")
                module_materials["components"]["lesson_plan"] = self.generate_detailed_lesson_plan(module_idx, detail_level)
                
            if "activities" in components:
                logger.info(f"  - Generating extensive activities...")
                module_materials["components"]["activities"] = self.generate_comprehensive_activities(module_idx, detail_level)
                
            if "instructor_guides" in components:
                logger.info(f"  - Generating detailed instructor guide...")
                module_materials["components"]["instructor_guide"] = self.generate_comprehensive_instructor_guide(module_idx, detail_level)
                
            materials["modules"].append(module_materials)
            
        return materials
    
    def generate_comprehensive_content(self, module_idx: int, detail_level: str = "comprehensive") -> Dict[str, Any]:
        """
        Generate comprehensive, textbook-style instructional content.
        """
        if module_idx < 1 or module_idx > len(self.modules):
            return {"error": "Invalid module index"}
            
        module = self.modules[module_idx - 1]
        module_title = module.get("title", f"Module {module_idx}")
        
        # Extract specific task analysis content for this module
        task_content = self._extract_task_content_for_module(module_idx)
        
        # Generate comprehensive content
        client = GroqClient()
        
        # Generate main content with more detailed topic coverage
        main_content_prompt = f"""
        You are creating a comprehensive, textbook-style chapter for Module {module_idx}: {module_title} 
        in a {self.audience_type} level course on {self.course_topic}.
        
        This should be extensive, detailed educational content similar to what you'd find in a professional textbook.
        
        MODULE CONTEXT:
        - Title: {module_title}
        - Learning Objectives: {json.dumps(module.get('objectives', []))}
        - Topics to Cover: {json.dumps(module.get('topics', []))}
        
        TASK ANALYSIS CONTENT:
        {task_content}
        
        AUDIENCE: {self.audience_type} level learners
        
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
        create a comprehensive section with:
        
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
        - Professional and authoritative
        - Engaging and well-structured
        
        IMPORTANT: Do not skip any topic from the module topics list. Each topic must have its own comprehensive section.
        """
        
        main_content_response = client.generate(main_content_prompt)
        
        # Return structured content
        comprehensive_content = {
            "main_content": main_content_response,
            "content_structure": {
                "estimated_reading_time": "45-60 minutes",
                "word_count_estimate": "8000-12000 words",
                "complexity_level": self.audience_type,
                "prerequisite_knowledge": self._determine_prerequisites(module_idx),
                "learning_path": self._create_learning_path(module)
            },
            "metadata": {
                "module_number": module_idx,
                "module_title": module_title,
                "generated_date": datetime.now().strftime("%B %d, %Y at %H:%M"),
                "detail_level": detail_level,
                "content_type": "comprehensive_textbook_chapter"
            }
        }
        
        return comprehensive_content
    
    def generate_real_assessments(self, module_idx: int, detail_level: str = "comprehensive", 
                                 module_content: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate real assessment questions based on actual module content.
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
        
        client = GroqClient()
        
        # Generate assessment questions based on actual content
        assessment_prompt = f"""
        You are creating REAL assessment questions based on the ACTUAL CONTENT of Module {module_idx}: {module_title}.
        
        Here is the ACTUAL MODULE CONTENT that students will have learned:
        
        {content_text}
        
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
        """
        
        assessments_response = client.generate(assessment_prompt)
        
        # Generate additional practice questions
        practice_prompt = f"""
        Based on the same module content for Module {module_idx}: {module_title}, create 10 additional practice questions 
        with complete answers that students can use for self-study.
        
        These should be similar in style to the assessment questions but focus on reinforcing key concepts.
        Each question should include:
        - The question
        - Multiple choice options (if applicable)
        - Complete correct answer with explanation
        - Reference to specific module content
        - Study tip related to the concept
        
        Format as:
        
        ## Practice Questions for Module {module_idx}
        
        **Practice Question 1:**
        [Question based on module content]
        
        **Answer:** [Complete answer with explanation]
        **Content Reference:** [Specific section of module content]
        **Study Tip:** [Helpful tip for remembering this concept]
        
        [Continue for all 10 questions, covering different aspects of the module content]
        """
        
        practice_response = client.generate(practice_prompt)
        
        return {
            "comprehensive_assessments": assessments_response,
            "practice_questions": practice_response,
            "assessment_overview": {
                "total_questions": "35-45 assessment questions + 10 practice questions",
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
                    "Grading rubrics included"
                ],
                "estimated_assessment_time": "2-3 hours for full assessment suite"
            },
            "metadata": {
                "module_number": module_idx,
                "module_title": module_title,
                "generated_date": datetime.now().strftime("%B %d, %Y at %H:%M"),
                "detail_level": detail_level,
                "assessment_type": "content_based_real_questions",
                "content_based": True
            }
        }
    
    def generate_detailed_lesson_plan(self, module_idx: int, detail_level: str = "comprehensive") -> Dict[str, Any]:
        """
        Generate a detailed lesson plan for comprehensive content delivery.
        """
        if module_idx < 1 or module_idx > len(self.modules):
            return {"error": "Invalid module index"}
            
        module = self.modules[module_idx - 1]
        module_title = module.get("title", f"Module {module_idx}")
        
        client = GroqClient()
        
        prompt = f"""
        Create a comprehensive lesson plan for delivering the extensive content of Module {module_idx}: {module_title}.
        
        This lesson plan should accommodate the delivery of rich, textbook-style content to {self.audience_type} level learners.
        
        ## Comprehensive Lesson Plan: {module_title}
        
        ### Session Overview
        - **Duration**: 3-4 hours (with breaks) or split into 2-3 shorter sessions
        - **Format**: Interactive lecture with extensive engagement
        - **Materials**: Comprehensive content, multimedia, hands-on materials
        
        ### Pre-Session Preparation (60-90 minutes)
        
        #### Instructor Preparation
        - Review all chapter content thoroughly
        - Prepare multimedia presentations
        - Set up interactive elements
        - Prepare handouts and materials
        - Test all technology
        
        #### Student Preparation
        - Pre-reading assignments
        - Prerequisite knowledge check
        - Preparation materials to review
        
        ### Detailed Session Structure
        
        #### Opening Phase (20-30 minutes)
        1. **Welcome and Objectives** (5 minutes)
           - Clear learning outcomes
           - Session roadmap
           - Expectation setting
        
        2. **Engagement Hook** (10-15 minutes)
           - Real-world scenario or case
           - Interactive discussion
           - Problem-based opener
        
        3. **Knowledge Activation** (10 minutes)
           - Prior knowledge assessment
           - Connection to previous modules
           - Mental preparation for new content
        
        #### Core Content Delivery (120-150 minutes)
        
        **Segment 1: Foundational Concepts** (40-50 minutes)
        - Detailed content delivery method
        - Interactive elements every 10-15 minutes
        - Visual aids and demonstrations
        - Check for understanding
        - Q&A opportunities
        
        **Break** (10-15 minutes)
        
        **Segment 2: Advanced Applications** (40-50 minutes)
        - Case study analysis
        - Hands-on exercises
        - Group work and discussions
        - Problem-solving activities
        
        **Break** (10-15 minutes)
        
        **Segment 3: Practical Implementation** (40-50 minutes)
        - Real-world applications
        - Tool demonstrations
        - Practice opportunities
        - Skill development activities
        
        #### Integration and Assessment (30-40 minutes)
        1. **Synthesis Activities** (15-20 minutes)
           - Concept mapping
           - Summary creation
           - Peer teaching
        
        2. **Formative Assessment** (10-15 minutes)
           - Quick comprehension checks
           - Application exercises
           - Self-assessment tools
        
        3. **Wrap-up and Preview** (5-10 minutes)
           - Key takeaways summary
           - Next session preview
           - Assignment of follow-up work
        
        ### Instructional Strategies for Each Phase
        
        #### Content Delivery Techniques
        - **Chunking**: Break complex content into digestible segments
        - **Scaffolding**: Build complexity gradually
        - **Multimodal**: Use visual, auditory, and kinesthetic approaches
        - **Interactive**: Engage every 10-15 minutes
        - **Contextual**: Provide real-world connections
        
        #### Engagement Strategies
        - Think-pair-share activities
        - Polling and voting
        - Breakout discussions
        - Hands-on demonstrations
        - Case study analysis
        - Role-playing scenarios
        
        ### Assessment Integration
        
        #### Continuous Assessment
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
        - Extension activities
        - Leadership roles
        - Additional challenges
        - Independent projects
        
        #### For Struggling Learners
        - Additional support materials
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
        - Homework assignments
        - Independent study guides
        - Peer collaboration projects
        - Real-world application tasks
        
        Create a lesson plan that can effectively deliver comprehensive, textbook-level content while maintaining high engagement.
        """
        
        lesson_plan_response = client.generate(prompt)
        
        return {
            "comprehensive_lesson_plan": lesson_plan_response,
            "metadata": {
                "module_number": module_idx,
                "module_title": module_title,
                "generated_date": datetime.now().strftime("%B %d, %Y at %H:%M"),
                "detail_level": detail_level,
                "session_duration": "3-4 hours or multiple shorter sessions",
                "preparation_time": "60-90 minutes"
            }
        }
    
    def generate_comprehensive_activities(self, module_idx: int, detail_level: str = "comprehensive") -> Dict[str, Any]:
        """
        Generate extensive learning activities for comprehensive content.
        """
        if module_idx < 1 or module_idx > len(self.modules):
            return {"error": "Invalid module index"}
            
        module = self.modules[module_idx - 1]
        module_title = module.get("title", f"Module {module_idx}")
        
        client = GroqClient()
        
        prompt = f"""
        Create a comprehensive collection of learning activities for Module {module_idx}: {module_title}.
        
        These activities should support the delivery and reinforcement of extensive, textbook-style content.
        
        Generate 8-12 diverse activities that include:
        
        ### Category 1: Content Engagement Activities (2-3 activities)
        
        #### Activity: Interactive Content Exploration
        - **Type**: Guided Discovery
        - **Duration**: 25-30 minutes
        - **Purpose**: Deep engagement with core concepts
        - **Materials**: Content chunks, exploration guides
        - **Process**: 
          1. Divide content into exploration stations
          2. Students rotate through stations
          3. Each station focuses on one key concept
          4. Interactive elements at each station
          5. Synthesis discussion at the end
        - **Assessment**: Concept mapping completion
        - **Technology**: QR codes for multimedia content
        
        ### Category 2: Application Activities (3-4 activities)
        
        #### Activity: Real-World Case Analysis
        - **Type**: Case Study Analysis
        - **Duration**: 45-60 minutes
        - **Purpose**: Apply concepts to authentic scenarios
        - **Materials**: Detailed case studies, analysis frameworks
        - **Process**:
          1. Present complex, multi-faceted case
          2. Teams analyze different aspects
          3. Apply module concepts to case
          4. Develop solutions or recommendations
          5. Present findings to class
        - **Assessment**: Solution quality and reasoning
        - **Extensions**: Additional cases, alternative solutions
        
        ### Category 3: Collaborative Learning Activities (2-3 activities)
        
        #### Activity: Expert Groups and Teaching
        - **Type**: Jigsaw Method
        - **Duration**: 50-70 minutes
        - **Purpose**: Deep learning through teaching others
        - **Materials**: Expert topic assignments, teaching resources
        - **Process**:
          1. Assign expert topics to groups
          2. Expert groups master their topic
          3. Prepare teaching materials
          4. Teach other groups their topic
          5. All groups learn about all topics
        - **Assessment**: Teaching effectiveness and peer learning
        - **Technology**: Collaborative digital tools
        
        ### Category 4: Skill Development Activities (2-3 activities)
        
        #### Activity: Progressive Skill Building
        - **Type**: Scaffolded Practice
        - **Duration**: 40-60 minutes
        - **Purpose**: Build competency in key skills
        - **Materials**: Practice scenarios, skill checklists
        - **Process**:
          1. Demonstrate skill components
          2. Guided practice with feedback
          3. Independent practice
          4. Peer review and feedback
          5. Skill demonstration
        - **Assessment**: Skill demonstration rubric
        - **Differentiation**: Multiple difficulty levels
        
        ### Category 5: Creative and Critical Thinking Activities (1-2 activities)
        
        #### Activity: Innovation Challenge
        - **Type**: Design Thinking
        - **Duration**: 60-90 minutes
        - **Purpose**: Creative application of concepts
        - **Materials**: Design thinking templates, prototyping materials
        - **Process**:
          1. Present innovation challenge
          2. Empathize and define problems
          3. Ideate solutions using module concepts
          4. Prototype and test ideas
          5. Present innovations
        - **Assessment**: Innovation quality and concept integration
        - **Extensions**: Implementation planning
        
        For each activity, provide:
        
        ### Detailed Implementation Guide
        - Pre-activity setup
        - Step-by-step facilitation
        - Timing for each phase
        - Materials checklist
        - Technology requirements
        - Assessment methods
        - Troubleshooting tips
        - Variations and extensions
        
        ### Differentiation Options
        - Advanced learner challenges
        - Support for struggling learners
        - Cultural adaptations
        - Technology alternatives
        
        ### Integration with Content
        - Specific concepts reinforced
        - Learning objectives addressed
        - Connection to other activities
        - Assessment alignment
        
        Create activities that are engaging, educationally sound, and appropriate for {self.audience_type} learners dealing with comprehensive content.
        """
        
        activities_response = client.generate(prompt)
        
        return {
            "comprehensive_activities": activities_response,
            "activity_overview": {
                "total_activities": "8-12 diverse activities",
                "categories": [
                    "Content Engagement",
                    "Application",
                    "Collaborative Learning", 
                    "Skill Development",
                    "Creative and Critical Thinking"
                ],
                "estimated_total_time": "4-6 hours",
                "recommended_usage": "Select 3-5 activities per session based on learning objectives"
            },
            "metadata": {
                "module_number": module_idx,
                "module_title": module_title,
                "generated_date": datetime.now().strftime("%B %d, %Y at %H:%M"),
                "detail_level": detail_level,
                "activity_complexity": "comprehensive"
            }
        }
    
    def generate_comprehensive_instructor_guide(self, module_idx: int, detail_level: str = "comprehensive") -> Dict[str, Any]:
        """
        Generate detailed instructor guide for comprehensive content delivery.
        """
        if module_idx < 1 or module_idx > len(self.modules):
            return {"error": "Invalid module index"}
            
        module = self.modules[module_idx - 1]
        module_title = module.get("title", f"Module {module_idx}")
        
        client = GroqClient()
        
        prompt = f"""
        Create a comprehensive instructor guide for delivering extensive, textbook-style content for Module {module_idx}: {module_title}.
        
        This guide should support instructors in effectively delivering rich, detailed educational content to {self.audience_type} level learners.
        
        ## Comprehensive Instructor Guide: {module_title}
        
        ### Module Overview for Instructors
        
        #### Content Scope and Depth
        - **Estimated Content Volume**: 8,000-12,000 words equivalent
        - **Reading Time**: 45-60 minutes for students
        - **Teaching Time**: 3-4 hours or multiple sessions
        - **Complexity Level**: {self.audience_type} with comprehensive depth
        - **Prerequisites**: [List essential prerequisite knowledge]
        
        #### Key Teaching Challenges
        - Managing extensive content without overwhelming students
        - Maintaining engagement throughout lengthy sessions
        - Ensuring deep understanding vs. surface coverage
        - Balancing theory with practical application
        - Accommodating different learning paces
        
        ### Pre-Instruction Preparation (2-3 Hours)
        
        #### Content Mastery Preparation
        1. **Deep Content Review** (60-90 minutes)
           - Read all content materials thoroughly
           - Identify key concepts and relationships
           - Note potential student difficulty areas
           - Prepare additional examples
           - Research current applications
        
        2. **Instructional Planning** (45-60 minutes)
           - Plan content chunking strategy
           - Design engagement checkpoints
           - Prepare multimedia elements
           - Set up interactive components
           - Plan assessment touchpoints
        
        3. **Material and Technology Setup** (30-45 minutes)
           - Test all technology components
           - Prepare handouts and resources
           - Set up learning environment
           - Organize materials for easy access
           - Prepare backup plans
        
        ### Content Delivery Strategies
        
        #### Chunking Strategy for Extensive Content
        **Chunk 1: Foundation Building** (45-60 minutes)
        - **Content Focus**: Core concepts and definitions
        - **Delivery Method**: Interactive lecture with frequent checks
        - **Engagement**: Every 10-15 minutes
        - **Assessment**: Quick comprehension checks
        - **Transition**: Clear bridge to next chunk
        
        **Chunk 2: Deep Dive Analysis** (45-60 minutes)
        - **Content Focus**: Detailed explanations and examples
        - **Delivery Method**: Guided exploration and discussion
        - **Engagement**: Case studies and scenarios
        - **Assessment**: Application exercises
        - **Transition**: Synthesis activity
        
        **Chunk 3: Practical Application** (45-60 minutes)
        - **Content Focus**: Real-world applications and skills
        - **Delivery Method**: Hands-on activities and practice
        - **Engagement**: Interactive exercises
        - **Assessment**: Performance demonstrations
        - **Transition**: Integration and summary
        
        #### Engagement Maintenance Strategies
        
        **Every 10-15 Minutes**:
        - Pose reflection questions
        - Quick pair-share activities
        - Polling or voting
        - Stand and stretch breaks
        - Concept check quizzes
        
        **Every 30-45 Minutes**:
        - Major activity or exercise
        - Group discussions
        - Case study analysis
        - Problem-solving scenarios
        - Application challenges
        
        **Every 60-90 Minutes**:
        - Formal break (10-15 minutes)
        - Energy re-engagement activity
        - Major transition activity
        - Progress assessment
        - Goal refocusing
        
        ### Assessment Integration and Management
        
        #### Real-Time Assessment Strategies
        - **Content-Based Questions**: Use actual module content for immediate checks
        - **Application Scenarios**: Test understanding through real examples
        - **Peer Teaching**: Students explain concepts to each other
        - **Quick Quizzes**: 3-5 questions based on just-covered material
        - **Exit Tickets**: Summary of key learnings and questions
        
        #### Assessment Data Management
        - Real-time tracking methods
        - Quick documentation strategies
        - Student progress monitoring
        - Intervention decision points
        - Feedback delivery systems
        
        ### Technology Integration Guide
        
        #### Essential Technology Tools
        - **Presentation Software**: Advanced features usage
        - **Polling Tools**: Real-time engagement
        - **Collaboration Platforms**: Group work management
        - **Assessment Tools**: Quick check systems
        - **Multimedia Tools**: Rich content delivery
        
        #### Technology Troubleshooting
        - Common issues and solutions
        - Backup delivery methods
        - Student technology support
        - Accessibility considerations
        - Emergency procedures
        
        ### Student Support Strategies
        
        #### For Overwhelmed Students
        - Content chunking reminders
        - Study strategy guidance
        - Additional support resources
        - One-on-one check-ins
        - Stress management techniques
        
        #### For Advanced Students
        - Extension challenges
        - Leadership opportunities
        - Independent exploration
        - Peer teaching roles
        - Advanced applications
        
        #### For Struggling Students
        - Prerequisite review
        - Simplified explanations
        - Additional examples
        - Extra practice time
        - Alternative assessments
        
        ### Quality Assurance Checklist
        
        #### Before Each Session
        - [ ] Content thoroughly reviewed
        - [ ] All materials prepared
        - [ ] Technology tested
        - [ ] Environment set up
        - [ ] Backup plans ready
        
        #### During Each Session
        - [ ] Engagement every 10-15 minutes
        - [ ] Regular comprehension checks
        - [ ] Time management monitoring
        - [ ] Student energy assessment
        - [ ] Adjustment implementation
        
        #### After Each Session
        - [ ] Student feedback collected
        - [ ] Assessment data reviewed
        - [ ] Session effectiveness evaluated
        - [ ] Improvements identified
        - [ ] Next session prepared
        
        ### Assessment Answer Keys and Guidance
        
        #### Using Real Assessment Questions
        - How to integrate content-based questions during instruction
        - Techniques for creating spontaneous questions from content
        - Methods for checking student understanding of specific concepts
        - Strategies for providing immediate feedback on content mastery
        
        #### Grading Comprehensive Assessments
        - Guidelines for evaluating content-based responses
        - Rubrics for application and analysis questions
        - Methods for providing meaningful feedback
        - Strategies for identifying and addressing knowledge gaps
        
        Create an instructor guide that empowers educators to deliver comprehensive, engaging, and effective instruction with extensive content while ensuring real learning occurs.
        """
        
        instructor_guide_response = client.generate(prompt)
        
        return {
            "comprehensive_instructor_guide": instructor_guide_response,
            "guide_overview": {
                "preparation_time": "2-3 hours",
                "delivery_time": "3-4 hours or multiple sessions",
                "key_features": [
                    "Content chunking strategies",
                    "Engagement maintenance",
                    "Real-time assessment integration",
                    "Technology support",
                    "Student support strategies",
                    "Assessment guidance"
                ],
                "support_level": "comprehensive"
            },
            "metadata": {
                "module_number": module_idx,
                "module_title": module_title,
                "generated_date": datetime.now().strftime("%B %d, %Y at %H:%M"),
                "detail_level": detail_level,
                "guide_type": "comprehensive_delivery"
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


# Updated helper function
def generate_course_materials(design_data: Dict[str, Any], 
                             selected_modules: List[int] = None,
                             components: List[str] = None,
                             detail_level: str = "comprehensive") -> Dict[str, Any]:
    """
    Generate comprehensive, textbook-style course materials with real assessment questions.
    
    Args:
        design_data: Course design data from Phase 2
        selected_modules: List of module indexes to generate materials for
        components: List of component types to generate
        detail_level: Level of detail for generation
        
    Returns:
        Dictionary containing comprehensive generated materials with real assessments
    """
    generator = TextbookStyleCourseMaterialsGenerator(design_data)
    return generator.generate_all_materials(selected_modules, components, detail_level)


# Backward compatibility - keep the original class name as an alias
class CourseMaterialsGenerator(TextbookStyleCourseMaterialsGenerator):
    """Alias for backward compatibility."""
    pass