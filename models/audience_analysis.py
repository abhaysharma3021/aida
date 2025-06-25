from models.groq_client import GroqClient

def generate_audience_analysis(course_topic, audience_type, terminal_objectives, job_titles="", 
                              industry_context="", audience_challenges="", prior_knowledge=""):
    """Generate a concise, targeted audience analysis in the specified format"""

    system_prompt = """You are an expert instructional designer. You create concise, structured audience analyses 
    that follow a VERY SPECIFIC format with EXACT heading structure and bullet points. 
    Keep all responses extremely brief and consistent with the example format. Provide me output in html format and well formated with heading, subheading and paragraphs"""

    prompt = f"""
Create a brief audience analysis for a {audience_type} level course on {course_topic}.

Follow this EXACT format, with this EXACT structure and length:

# Audience Analysis
## Profile:
* Course Topic: [Course Topic]
* Audience Type: [Audience Type]
* Common Job Titles/Background: [1-2 sentences describing audience background]

## Key Characteristics:
* Knowledge Base: [1 sentence about what they know or don't know]
* Learning Style: [1 sentence about how they learn best]
* Motivation: [1 sentence about why they want to learn this]
* Needs: [1 sentence about what they need from the course]

## Implications for Instructional Design:
* [1 brief instructional design recommendation]
* [1 brief instructional design recommendation]
* [1 brief instructional design recommendation]

Use this EXAMPLE as a guide for length and style:

# Audience Analysis
Profile:
* Course Topic: Python Programming
* Audience Type: Beginner
* Common Job Titles/Background: 12th standard students, typically with basic computer literacy and little to no programming experience.

Key Characteristics:
* Knowledge Base: Limited exposure to programming and project management concepts.
* Learning Style: Likely to benefit from interactive, hands-on activities, visual aids, and real-life examples.
* Motivation: Interested in acquiring new technical skills that may help in academic and future career opportunities.
* Needs: Clear, step-by-step guidance; simplified explanations; and ample practice opportunities to build both programming and project management fundamentals.

Implications for Instructional Design:
* Use relatable examples and simple language.
* Incorporate multimedia elements (videos, interactive demos) to illustrate both Python programming and basic project management concepts.
* Provide opportunities for immediate application through projects or case studies that integrate planning, scheduling, and tool usage.

Additional details to consider:
- Job titles/background: {job_titles}
- Industry context: {industry_context}
- Audience challenges: {audience_challenges}
- Prior knowledge: {prior_knowledge}
- Course objectives: {terminal_objectives}

IMPORTANT RULES:
1. Keep each bullet point to ONE SENTENCE ONLY
2. Use the EXACT heading structure shown in the example
3. Maintain EXACTLY the number of bullets shown in the example
4. Be specific to the course topic and audience type
5. Do NOT include any additional text, explanations, or notes
6. Use the EXACT markdown heading structure shown (with ## and ### for headings)
7. Use proper markdown list items with - (dash) not * (asterisk)
8. Use proper markdown bold formatting with ** for labels
9. Follow markdown format precisely to ensure proper HTML rendering
"""

    # Generate the analysis
    client = GroqClient()
    response = client.generate(prompt, system_prompt)

    # Clean up any potential issues with the response
    response = response.replace('# ', '## ')  # Ensure proper heading level
    response = response.replace('* ', '- ')   # Standardize on dash for list items
    
    return response