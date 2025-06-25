import os
import sys
import json
import logging
import re
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Groq client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.groq_client import GroqClient

def extract_task_structure(task_analysis):
    """
    Extract the precise task structure from task analysis text.
    
    Args:
        task_analysis (str): The task analysis text
        
    Returns:
        list: List of dictionaries containing module info and subtasks
    """
    # Check if this is a standard task analysis template
    if "Task Analysis Template:" in task_analysis or "II. Task Breakdown:" in task_analysis:
        logger.info("Standard task analysis template detected")
        
        # First, try to find the Task Breakdown section
        task_breakdown_match = re.search(r'II\.\s+Task\s+Breakdown:(.*?)(?=III\.|$)', task_analysis, re.DOTALL | re.IGNORECASE)
        if task_breakdown_match:
            task_breakdown = task_breakdown_match.group(1)
        else:
            # If no Task Breakdown section, use the whole text
            task_breakdown = task_analysis
        
        # Look for sections like "A. Setting Up Python Development Environment"
        section_pattern = r'([A-Z])\.\s+([\w\s\-\/]+)[\r\n]+((?:(?:(?!^[A-Z]\.\s+[\w\s\-\/]+).)*?))(?=[A-Z]\.\s+|\Z)'
        section_matches = re.findall(section_pattern, task_breakdown, re.MULTILINE | re.DOTALL)
        
        if section_matches:
            logger.info(f"Found {len(section_matches)} main sections (A, B, C, etc.)")
            
            # Process each section
            modules = []
            for match in section_matches:
                if len(match) >= 3:  # Make sure we have enough values
                    section_id, section_title, section_content = match
                elif len(match) == 2:  # Handle the case where we only have id and title
                    section_id, section_title = match
                    section_content = ""
                else:  # Skip if we don't have enough information
                    continue
                
                # Look for subtasks
                subtask_pattern = r'Subtask\s+(\d+):\s+([\w\s\-\/]+)[\r\n]+((?:(?!Subtask\s+\d+:).)*?(?=Subtask\s+\d+:|\Z))'
                subtask_matches = re.findall(subtask_pattern, section_content, re.DOTALL)
                
                subtasks = []
                if subtask_matches:
                    for subtask_match in subtask_matches:
                        if len(subtask_match) >= 3:  # Make sure we have enough values
                            subtask_id, subtask_title, subtask_content = subtask_match
                        elif len(subtask_match) == 2:  # Handle the case where we only have id and title
                            subtask_id, subtask_title = subtask_match
                            subtask_content = ""
                        else:  # Skip if we don't have enough information
                            continue
                            
                        subtasks.append({
                            "id": subtask_id,
                            "title": subtask_title.strip(),
                            "content": subtask_content.strip()
                        })
                
                # If no subtasks found using pattern, try splitting the content
                if not subtasks:
                    lines = section_content.split('\n')
                    current_subtask = None
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                            
                        # Check for "Subtask X:" pattern
                        subtask_header = re.match(r'^Subtask\s+(\d+):\s+(.*)', line)
                        if subtask_header:
                            if current_subtask:
                                subtasks.append(current_subtask)
                                
                            current_subtask = {
                                "id": subtask_header.group(1),
                                "title": subtask_header.group(2).strip(),
                                "content": ""
                            }
                        elif current_subtask:
                            # Add to existing subtask content
                            current_subtask["content"] += line + "\n"
                        else:
                            # Create new subtask for first lines
                            current_subtask = {
                                "id": "1",
                                "title": "General Information",
                                "content": line + "\n"
                            }
                    
                    # Add the last subtask
                    if current_subtask:
                        subtasks.append(current_subtask)
                
                # If we still don't have subtasks, create a placeholder
                if not subtasks:
                    subtasks = [{
                        "id": "1",
                        "title": "General Content",
                        "content": section_content.strip()
                    }]
                
                modules.append({
                    "id": section_id,
                    "title": section_title.strip(),
                    "subtasks": subtasks
                })
            
            if modules:
                return modules
    
    # Try a simpler approach if the detailed parsing doesn't work
    logger.warning("Using simplified parsing approach")
    
    # Look for patterns like "A. Title" or "II. Title"
    main_headers = re.findall(r'([A-Z])\.\s+([\w\s\-\/]+)', task_analysis)
    
    if main_headers:
        logger.info(f"Found {len(main_headers)} main headers with simplified parsing")
        modules = []
        
        for i, (section_id, section_title) in enumerate(main_headers):
            # Get content between this header and the next (or end)
            start_pattern = f"{section_id}\\. {re.escape(section_title)}"
            
            if i < len(main_headers) - 1:
                end_pattern = f"{main_headers[i+1][0]}\\. {re.escape(main_headers[i+1][1])}"
                section_match = re.search(f"{start_pattern}(.*?){end_pattern}", task_analysis, re.DOTALL)
            else:
                section_match = re.search(f"{start_pattern}(.*?)$", task_analysis, re.DOTALL)
            
            if section_match:
                section_content = section_match.group(1).strip()
            else:
                section_content = ""
            
            # Look for "Subtask X:" in content
            subtask_headers = re.findall(r'Subtask\s+(\d+):\s+([\w\s\-\/]+)', section_content)
            
            if subtask_headers:
                subtasks = []
                for j, (subtask_id, subtask_title) in enumerate(subtask_headers):
                    # Get content between this subtask and the next (or end of section)
                    start_subtask = f"Subtask {subtask_id}: {subtask_title}"
                    
                    if j < len(subtask_headers) - 1:
                        end_subtask = f"Subtask {subtask_headers[j+1][0]}: {subtask_headers[j+1][1]}"
                        subtask_match = re.search(f"{re.escape(start_subtask)}(.*?){re.escape(end_subtask)}", 
                                                 section_content, re.DOTALL)
                    else:
                        subtask_match = re.search(f"{re.escape(start_subtask)}(.*?)$", section_content, re.DOTALL)
                    
                    if subtask_match:
                        subtask_content = subtask_match.group(1).strip()
                    else:
                        subtask_content = ""
                    
                    subtasks.append({
                        "id": subtask_id,
                        "title": subtask_title.strip(),
                        "content": subtask_content
                    })
            else:
                # No subtasks found, create a generic one
                subtasks = [{
                    "id": "1",
                    "title": "General Content",
                    "content": section_content
                }]
            
            modules.append({
                "id": section_id,
                "title": section_title.strip(),
                "subtasks": subtasks
            })
        
        if modules:
            return modules
    
    # If we still couldn't find modules, create a basic structure
    logger.warning("Could not detect modules in task analysis. Creating basic structure.")
    modules = [
        {
            "id": "A",
            "title": "Setting Up and Introduction",
            "subtasks": [{"id": "1", "title": "Getting Started", "content": "Basic introduction and setup."}]
        },
        {
            "id": "B",
            "title": "Core Concepts",
            "subtasks": [{"id": "1", "title": "Essential Skills", "content": "Fundamental skills and knowledge."}]
        },
        {
            "id": "C",
            "title": "Practical Applications",
            "subtasks": [{"id": "1", "title": "Real-world Usage", "content": "Applying knowledge to practical scenarios."}]
        },
        {
            "id": "D",
            "title": "Advanced Topics",
            "subtasks": [{"id": "1", "title": "Advanced Techniques", "content": "More complex topics and techniques."}]
        }
    ]
    
    return modules

def generate_course_structure(course_topic, audience_type, terminal_objectives, audience_analysis, task_analysis, module_count=None):
    """
    Generate a course structure based on task analysis sections.
    
    Args:
        course_topic (str): The main topic of the course
        audience_type (str): The audience level (beginner, intermediate, advanced)
        terminal_objectives (str): The terminal learning objectives
        audience_analysis (str): The generated audience analysis content
        task_analysis (str): The generated task analysis content
        module_count (int, optional): Number of modules to generate (default: auto-detect from task analysis)
        
    Returns:
        str: A markdown-formatted course structure
    """
    try:
        client = GroqClient()
        
        # Extract task structure from task analysis
        modules = extract_task_structure(task_analysis)
        
        # If no modules were found, log an error
        if not modules:
            raise Exception("No modules could be extracted from the task analysis")
        
        # If module_count is specified and different from extracted count, adjust
        if module_count and module_count != len(modules):
            if module_count < len(modules):
                # Combine modules
                logger.info(f"Combining {len(modules)} modules into {module_count} modules")
                new_modules = []
                modules_per_group = len(modules) // module_count
                remaining = len(modules) % module_count
                
                start_idx = 0
                for i in range(module_count):
                    # Calculate how many modules to include in this group
                    count = modules_per_group + (1 if i < remaining else 0)
                    end_idx = start_idx + count
                    
                    # Combine module titles
                    module_titles = [modules[j]["title"] for j in range(start_idx, end_idx)]
                    combined_title = " & ".join(module_titles)
                    
                    # Combine subtasks
                    combined_subtasks = []
                    for j in range(start_idx, end_idx):
                        for subtask in modules[j]["subtasks"]:
                            combined_subtasks.append({
                                "id": f"{modules[j]['id']}{subtask['id']}",
                                "title": f"{modules[j]['title']}: {subtask['title']}",
                                "content": subtask['content']
                            })
                    
                    new_modules.append({
                        "id": f"Group {i+1}",
                        "title": combined_title,
                        "subtasks": combined_subtasks
                    })
                    
                    start_idx = end_idx
                
                modules = new_modules
            
            elif module_count > len(modules):
                # Add additional modules
                logger.info(f"Adding {module_count - len(modules)} additional modules")
                additional_modules = [
                    {
                        "id": "Extra1",
                        "title": "Review and Practice",
                        "subtasks": [{"id": "1", "title": "Review Exercises", "content": "Comprehensive review and practice."}]
                    },
                    {
                        "id": "Extra2",
                        "title": "Advanced Applications",
                        "subtasks": [{"id": "1", "title": "Advanced Projects", "content": "Complex projects and applications."}]
                    },
                    {
                        "id": "Extra3",
                        "title": "Specialized Topics",
                        "subtasks": [{"id": "1", "title": "Special Interest Areas", "content": "Deeper dive into specialized areas."}]
                    },
                    {
                        "id": "Extra4",
                        "title": "Future Directions",
                        "subtasks": [{"id": "1", "title": "Emerging Trends", "content": "Future developments and trends."}]
                    }
                ]
                
                modules.extend(additional_modules[:module_count - len(modules)])
        
        # Prepare the module information for the prompt
        modules_text = ""
        for i, module in enumerate(modules):
            modules_text += f"MODULE {i+1}: {module['title']}\n"
            modules_text += "Subtasks:\n"
            
            for subtask in module["subtasks"]:
                modules_text += f"- {subtask['title']}\n"
            
            modules_text += "\n"
        
        # Create a bullet list of module titles for the critical requirements
        module_list = "\n".join([f"- Module {i+1}: {module['title']}" for i, module in enumerate(modules)])
        
        # Prepare the prompt for generating course structure
        prompt = f"""
        As an instructional design expert, create a detailed course structure for:
        
        COURSE TOPIC: {course_topic}
        AUDIENCE LEVEL: {audience_type}
        
        TERMINAL OBJECTIVES:
        {terminal_objectives}
        
        I have analyzed the task analysis and identified these exact modules and subtasks:
        
        {modules_text}
        
        Please create a detailed course structure with these EXACT SAME MODULES that includes:
        
        1. Course title (be specific and creative)
        2. Course description (1-2 paragraphs)
        3. Learning objectives (5-7 objectives using Bloom's taxonomy, organized by cognitive levels)
        4. Module structure (using EXACTLY the {len(modules)} modules I identified):
           For each module, include:
           - Module title (use EXACTLY the module titles I provided)
           - Module learning objectives (2-3 per module, using Bloom's taxonomy)
           - Topics covered (include ALL the subtasks I listed for each module)
           - Key activities (practical exercises based on the subtasks)
           
        Format the output in markdown with proper headings and bullet points.
        
        CRITICAL REQUIREMENTS:
        1. You MUST use EXACTLY the modules I provided:
        {module_list}
        2. Maintain the EXACT SAME ORDER of modules as I listed them
        3. Include ALL the subtasks I listed under each module
        4. Do not add any modules that I didn't list
        5. Do not remove any modules that I listed
        6. Do not reorder or rename the modules
        """
        
        # Generate content
        response = client.generate(prompt)
        logger.info("Course structure generated successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error generating course structure: {str(e)}")
        raise Exception(f"Failed to generate course structure: {str(e)}")

def generate_instructional_strategies(course_topic, audience_type, course_structure):
    """
    Generate instructional strategies based on course structure.
    
    Args:
        course_topic (str): The main topic of the course
        audience_type (str): The audience level (beginner, intermediate, advanced)
        course_structure (str): The generated course structure
        
    Returns:
        str: A markdown-formatted instructional strategies document
    """
    try:
        client = GroqClient()
        
        # Extract module titles from course structure for reference
        module_titles = re.findall(r'#+\s+Module \d+:[\s]+([^\n]+)', course_structure)
        if not module_titles:
            # Try alternative pattern
            module_titles = re.findall(r'Module \d+:[\s]+([^\n]+)', course_structure)
        
        # Create module list text
        if module_titles:
            modules_list = "\n".join([f"- Module {i+1}: {title}" for i, title in enumerate(module_titles)])
        else:
            modules_list = "(Please refer to the modules in the course structure)"
        
        # Prepare prompt for generating instructional strategies
        prompt = f"""
        As an instructional design expert, develop effective instructional strategies for:
        
        COURSE TOPIC: {course_topic}
        AUDIENCE LEVEL: {audience_type}
        
        For these specific modules:
        {modules_list}
        
        Please create a detailed instructional strategies document that includes:
        
        1. Overall instructional approach (based on audience level and subject matter)
        2. Engagement strategies (how to maintain learner interest and motivation)
        3. Specific strategies for EACH module:
           - Recommended instructional methods for content delivery
           - Interactive elements (discussions, activities, case studies)
           - Technology tools and resources to support learning
           - Strategies for addressing different learning styles
        4. Implementation recommendations
        
        Format the output in markdown with proper headings and bullet points.
        
        IMPORTANT: Create specific strategies for EACH module listed above, maintaining the same module titles and order.
        Do not combine, rename, or reorder the modules.
        """
        
        # Generate content
        response = client.generate(prompt)
        logger.info("Instructional strategies generated successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error generating instructional strategies: {str(e)}")
        raise Exception(f"Failed to generate instructional strategies: {str(e)}")

def generate_assessment_plan(course_topic, audience_type, course_structure, instructional_strategies=None):
    """
    Generate an assessment plan based on course structure.
    
    Args:
        course_topic (str): The main topic of the course
        audience_type (str): The audience level (beginner, intermediate, advanced)
        course_structure (str): The generated course structure
        instructional_strategies (str, optional): The generated instructional strategies
        
    Returns:
        str: A markdown-formatted assessment plan
    """
    try:
        client = GroqClient()
        
        # Extract module titles from course structure for reference
        module_titles = re.findall(r'#+\s+Module \d+:[\s]+([^\n]+)', course_structure)
        if not module_titles:
            # Try alternative pattern
            module_titles = re.findall(r'Module \d+:[\s]+([^\n]+)', course_structure)
        
        # Create module list text
        if module_titles:
            modules_list = "\n".join([f"- Module {i+1}: {title}" for i, title in enumerate(module_titles)])
        else:
            modules_list = "(Please refer to the modules in the course structure)"
        
        # Prepare prompt for generating assessment plan
        prompt = f"""
        As an instructional design expert, create a comprehensive assessment plan for:
        
        COURSE TOPIC: {course_topic}
        AUDIENCE LEVEL: {audience_type}
        
        For these specific modules:
        {modules_list}
        
        Please create a detailed assessment plan that includes:
        
        1. Assessment philosophy and approach (aligned with audience level)
        2. Pre-assessment strategies (to gauge prior knowledge)
        3. Formative assessment methods for EACH module:
           - Specific activities or questions to check understanding
           - Feedback mechanisms
        4. Summative assessment methods:
           - Final projects or assessments
           - Evaluation criteria and rubrics
        5. Self-assessment opportunities for learners
        
        Format the output in markdown with proper headings and bullet points.
        
        IMPORTANT: Create specific formative assessments for EACH module listed above, maintaining the same module titles and order.
        Do not combine, rename, or reorder the modules.
        """
        
        # Generate content
        response = client.generate(prompt)
        logger.info("Assessment plan generated successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error generating assessment plan: {str(e)}")
        raise Exception(f"Failed to generate assessment plan: {str(e)}")

def generate_comprehensive_course_design(analysis_data, components=None, module_count=None):
    """
    Generate a comprehensive course design including structure, strategies, and assessment.
    
    Args:
        analysis_data (dict): The complete analysis data including audience and task analyses
        components (list, optional): List of components to generate: 'structure', 'strategies', 'assessment'
        module_count (int, optional): Number of modules to generate
        
    Returns:
        dict: Updated analysis data with course design components
    """
    try:
        # If components is not specified, generate all
        if not components:
            components = ['structure', 'strategies', 'assessment']
        
        # Check which components already exist in analysis_data
        existing = {
            'structure': 'course_structure' in analysis_data,
            'strategies': 'instructional_strategies' in analysis_data,
            'assessment': 'assessment_plan' in analysis_data
        }
        
        # Step 1: Generate course structure (if requested)
        if 'structure' in components and not existing['structure']:
            course_structure = generate_course_structure(
                analysis_data['course_topic'],
                analysis_data['audience_type'],
                analysis_data.get('terminal_objectives', 'No terminal objectives provided.'),
                analysis_data['audience_analysis'],
                analysis_data.get('task_analysis', 'No task analysis provided.'),
                module_count
            )
            analysis_data['course_structure'] = course_structure
        
        # Step 2: Generate instructional strategies (if requested and course structure exists)
        if 'strategies' in components and not existing['strategies'] and 'course_structure' in analysis_data:
            instructional_strategies = generate_instructional_strategies(
                analysis_data['course_topic'],
                analysis_data['audience_type'],
                analysis_data['course_structure']
            )
            analysis_data['instructional_strategies'] = instructional_strategies
        
        # Step 3: Generate assessment plan (if requested and course structure exists)
        if 'assessment' in components and not existing['assessment'] and 'course_structure' in analysis_data:
            assessment_plan = generate_assessment_plan(
                analysis_data['course_topic'],
                analysis_data['audience_type'],
                analysis_data['course_structure'],
                analysis_data.get('instructional_strategies', None)
            )
            analysis_data['assessment_plan'] = assessment_plan
        
        # Update the generation date
        analysis_data['course_design_generated_date'] = datetime.now().strftime("%B %d, %Y at %H:%M")
        
        return analysis_data
        
    except Exception as e:
        logger.error(f"Error generating comprehensive course design: {str(e)}")
        raise Exception(f"Failed to generate comprehensive course design: {str(e)}")