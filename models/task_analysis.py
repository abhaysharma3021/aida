from models.groq_client import GroqClient

def generate_task_analysis(course_topic, audience_type, job_titles="", audience_analysis=""):
    """Generate a detailed task analysis based on the course topic and audience characteristics"""

    # Determine number of major task categories based on audience type
    if audience_type.lower() == "beginner":
        category_count = 5
    elif audience_type.lower() == "intermediate":
        category_count = 7
    elif audience_type.lower() == "advanced":
        category_count = 10
    else:
        # Default to 5 if audience type is unspecified or doesn't match known types
        category_count = 5

    system_prompt = """You are an expert instructional designer specializing in task analysis. 
    Create detailed, structured task analyses that accurately reflect the course topic and are calibrated 
    to the audience's needs, background, and level. Your analyses should be practical, thorough, and 
    directly applicable to the learning context."""

    prompt = f"""
Create a comprehensive task analysis for a {audience_type} level course on {course_topic}.

Audience information:
- Audience type: {audience_type}
- Job titles/roles: {job_titles}
- Additional audience context: {audience_analysis}

Important instruction: For a {audience_type} level audience, you must create EXACTLY {category_count} major task categories.

Please follow this EXACT format for the task analysis:

**Task Analysis Template: {course_topic}**

**I. Task/Goal:** [Overall purpose of the course in one sentence that captures the main skill/knowledge to be developed]

**II. Task Breakdown:**

**A. [Major Task Category 1]** [Choose categories that logically break down the subject matter]
* **Subtask 1:** [Description of specific subtask]

      1. [Detailed step with specific action]
      2. [Detailed step with specific action]
      3. [Additional steps as needed - be thorough but appropriate for audience level]
  
* **Subtask 2:** [Another relevant subtask]
  
      1. [Detailed step]
      2. [Detailed step]
      3. [Additional steps as needed]

**B. [Major Task Category 2]**
* **Subtask 1:** [Description of subtask]
  
      1. [Detailed step]
      2. [Detailed step]
  
* **Subtask 2:** [Description of subtask]
   
      1. [Detailed steps that break down the concept/practice]
  
**C. [Major Task Category 3]** [Add more categories if needed based on complexity and audience needs]
* **Subtask 1:** [Description of subtask]
   
      1. [Detailed step]
      2. [Detailed step]
      3. [Additional steps as needed]

[CONTINUE WITH EXACTLY {category_count} MAJOR TASK CATEGORIES, LABELED A THROUGH {chr(64 + category_count)}]

IMPORTANT GUIDELINES:
1. Create EXACTLY {category_count} major task categories (A through {chr(64 + category_count)})
2. The task analysis should be primarily driven by the COURSE TOPIC and AUDIENCE TYPE
3. For beginners: provide more foundational steps, simpler language, and more detailed breakdowns
4. For intermediate/advanced: focus on sophisticated techniques, complex applications, and higher-level skills
5. Adjust the depth of content based on audience needs - technical audiences need more technical detail
6. Include 3-10 major categories that represent logical divisions of the subject matter
7. Make sure each step is concrete, specific, and actionable
8. Steps should be detailed enough to guide instruction but not excessively granular
9. DO NOT include a 'Supporting Information' section
10. Be professionally thorough but calibrate complexity to the {audience_type} level
11. For each major task category, include AS MANY SUBTASKS AS NECESSARY - use your judgment based on the topic complexity and audience needs
12. Include practical applications and real-world context appropriate to the audience's field
"""

    # Generate the analysis
    client = GroqClient()
    response = client.generate(prompt, system_prompt)
    
    # Simple post-processing to ensure proper spacing
    response = response.replace("**I. Task/Goal:**", "\n**I. Task/Goal:**")
    response = response.replace("**II. Task Breakdown:**", "\n**II. Task Breakdown:**\n")
    
    return response