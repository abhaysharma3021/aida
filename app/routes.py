from models.groq_client import GroqClient
import os
import sys
import json
from venv import logger
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, send_file, current_app
from datetime import datetime
import markdown
import io
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
from difflib import get_close_matches
import zipfile
from models.course_materials import CourseMaterialsGenerator, generate_course_materials
from collections import defaultdict
import html
from xml.etree import ElementTree as ET
from xml.dom import minidom
from functools import wraps
from app.analysis_log import AnalysisLog
import time





# Create the Blueprint
main = Blueprint('main', __name__)

# Define the form classes
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Optional, Length

class CourseInputForm(FlaskForm):
    course_topic = StringField('Course Topic', validators=[DataRequired()])
    audience_type = SelectField('Audience Type', 
                              choices=[('beginner', 'Beginner'), 
                                      ('intermediate', 'Intermediate'),
                                      ('advanced', 'Advanced')],
                              validators=[DataRequired()])
    job_titles = TextAreaField('Role of Targeted Audience', 
                             description="Enter one job title per line (e.g., Software Engineer, Project Manager)")
    submit = SubmitField('Continue to Audience Analysis')

class TerminalObjectivesForm(FlaskForm):
    terminal_objectives = TextAreaField('Terminal Objectives', 
                                       description="Enter the terminal objectives for this course",
                                       validators=[DataRequired()])
    submit = SubmitField('Generate Task Analysis')

class CourseDesignRequirementsForm(FlaskForm):
    """Form for collecting additional requirements for course design."""
    course_duration = StringField('Course Duration (e.g., 3 days, 8 weeks)', validators=[Optional()])
    delivery_format = SelectField('Delivery Format', 
                                 choices=[
                                     ('', 'Select Format'),
                                     ('in_person', 'In-Person'),
                                     ('online_synchronous', 'Online Synchronous'),
                                     ('online_asynchronous', 'Online Asynchronous'),
                                     ('blended', 'Blended/Hybrid')
                                 ],
                                 validators=[Optional()])
    module_count = IntegerField('Number of Modules (3-7 recommended)', validators=[Optional()])
    additional_requirements = TextAreaField('Additional Requirements or Notes', 
                                          validators=[Optional(), Length(max=2000)])
    submit = SubmitField('Generate Course Design')

# Import models with absolute path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.audience_analysis import generate_audience_analysis
from models.task_analysis import generate_task_analysis
from models.course_design import generate_course_structure, generate_instructional_strategies, generate_assessment_plan, generate_comprehensive_course_design

# Create a data directory if it doesn't exist
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped

def save_analysis(analysis_id, data):
    """Save analysis data to a JSON file"""
    filepath = os.path.join(DATA_DIR, f"{analysis_id}.json")
    with open(filepath, 'w') as f:
        json.dump(data, f)
    return analysis_id

def load_analysis(analysis_id):
    """Load analysis data from a JSON file"""
    filepath = os.path.join(DATA_DIR, f"{analysis_id}.json")
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return None

def markdown_to_docx(doc, markdown_text):
    """Convert markdown text to formatted docx document."""
    # Split the markdown into lines
    lines = markdown_text.split('\n')
    current_list = None
    list_item_pattern = re.compile(r'^\s*[-*]\s+(.+)$')
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
    task_heading_pattern = re.compile(r'^\*\*(Task\s+\d+:.+?)\*\*$')
    learning_activity_pattern = re.compile(r'^\*\*(Learning Activity:)\*\*\s*(.+)$')
    assessment_pattern = re.compile(r'^\*\*(Assessment:)\*\*\s*(.+)$')
    
    for line in lines:
        if not line.strip():
            # Empty line
            doc.add_paragraph()
            current_list = None
            continue
        
        # Check if line is a heading
        heading_match = heading_pattern.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            doc.add_heading(text, level)
            current_list = None
            continue
            
        # Check for task headings like "**Task 1: Understanding Basic Syntax**"
        task_match = task_heading_pattern.match(line)
        if task_match:
            title = task_match.group(1)
            heading = doc.add_heading(title, 2)
            current_list = None
            continue
            
        # Check for "**Learning Activity:**" or "**Assessment:**"
        learning_match = learning_activity_pattern.match(line)
        if learning_match:
            p = doc.add_paragraph()
            run = p.add_run(learning_match.group(1) + " ")
            run.bold = True
            if learning_match.group(2):
                p.add_run(learning_match.group(2))
            current_list = None
            continue
            
        assessment_match = assessment_pattern.match(line)
        if assessment_match:
            p = doc.add_paragraph()
            run = p.add_run(assessment_match.group(1) + " ")
            run.bold = True
            if assessment_match.group(2):
                p.add_run(assessment_match.group(2))
            current_list = None
            continue
        
        # Check if line is a list item
        list_match = list_item_pattern.match(line)
        if list_match:
            if current_list is None:
                current_list = doc.add_paragraph(style='List Bullet')
            else:
                current_list = doc.add_paragraph(style='List Bullet')
                
            # Process the list item text for any formatting
            item_text = list_match.group(1)
            remaining_text = item_text
            
            # Process bold and italic in list item
            while '**' in remaining_text or '*' in remaining_text:
                # Check for bold text
                bold_match = re.search(r'\*\*(.+?)\*\*', remaining_text)
                if bold_match:
                    start, end = bold_match.span()
                    # Add text before the bold part
                    if start > 0:
                        current_list.add_run(remaining_text[:start])
                    # Add the bold text
                    current_list.add_run(bold_match.group(1)).bold = True
                    # Update remaining text
                    remaining_text = remaining_text[end:]
                    continue
                
                # Check for italic text
                italic_match = re.search(r'\*(.+?)\*', remaining_text)
                if italic_match:
                    start, end = italic_match.span()
                    # Add text before the italic part
                    if start > 0:
                        current_list.add_run(remaining_text[:start])
                    # Add the italic text
                    current_list.add_run(italic_match.group(1)).italic = True
                    # Update remaining text
                    remaining_text = remaining_text[end:]
                    continue
                
                break
            
            # Add any remaining text
            if remaining_text:
                current_list.add_run(remaining_text)
            
            continue
        
        # Regular paragraph - check for special patterns
        if '**' in line:
            p = doc.add_paragraph()
            remaining_text = line
            
            # Process bold and italic formatting
            while '**' in remaining_text or '*' in remaining_text:
                # Check for bold text
                bold_match = re.search(r'\*\*(.+?)\*\*', remaining_text)
                if bold_match:
                    start, end = bold_match.span()
                    # Add text before the bold part
                    if start > 0:
                        p.add_run(remaining_text[:start])
                    # Add the bold text
                    p.add_run(bold_match.group(1)).bold = True
                    # Update remaining text
                    remaining_text = remaining_text[end:]
                    continue
                
                # Check for italic text
                italic_match = re.search(r'\*(.+?)\*', remaining_text)
                if italic_match:
                    start, end = italic_match.span()
                    # Add text before the italic part
                    if start > 0:
                        p.add_run(remaining_text[:start])
                    # Add the italic text
                    p.add_run(italic_match.group(1)).italic = True
                    # Update remaining text
                    remaining_text = remaining_text[end:]
                    continue
                
                break
            
            # Add any remaining text
            if remaining_text:
                p.add_run(remaining_text)
        else:
            # Regular paragraph with no special formatting
            p = doc.add_paragraph(line)
        
        current_list = None
def escape_control_characters(json_str):
    def replace_control_chars(match):
        # Get the matched string (content between quotes)
        content = match.group(0)
        # Replace \r\n with \\r\\n and \n with \\n
        content = content.replace('\r\n', '\\r\\n').replace('\n', '\\n')
        return content
    
    # Match string literals (text between double quotes)
    pattern = r'"[^"]*"'
    return re.sub(pattern, replace_control_chars, json_str)

# Function to unescape control characters in the extracted content
def unescape_content(content):
    # Convert literal \r\n and \n to actual control characters
    return content.encode().decode('unicode_escape')

@main.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = CourseInputForm()
    if form.validate_on_submit():
        try:
            # Process form data
            course_topic = form.course_topic.data
            audience_type = form.audience_type.data
            job_titles = form.job_titles.data
            
            # Create a timestamp-based ID
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            analysis_id = f"analysis_{timestamp}"
            
            # Generate audience analysis
            audience_analysis = generate_audience_analysis(course_topic, audience_type, '')
            
            # Save initial data to file
            analysis_data = {
                'audience_analysis': audience_analysis,
                'course_topic': course_topic,
                'audience_type': audience_type,
                'job_titles': job_titles,
                'generated_date': datetime.now().strftime("%B %d, %Y at %H:%M")
            }
            save_analysis(analysis_id, analysis_data)
            
            logged_user = session.get("user")
            if not logged_user:
                flash("User session not found.")
                return redirect(url_for("auth_bp.login"))  # or any fallback
             
            email = logged_user["email"]
            
            AnalysisLog.create(
                useremail= email,
                analysis_id=analysis_id,
                data= analysis_data
            )
            
            # Store the ID in session
            session['current_analysis_id'] = analysis_id
            
            return redirect(url_for('main.audience_analysis', analysis_id=analysis_id))
        
        except Exception as e:
            flash(f"Error generating analysis: {str(e)}")
            print(f"Error details: {str(e)}")
            return render_template('index.html', form=form)
    
    return render_template('index.html', form=form)

@main.route('/audience_analysis/<analysis_id>', methods=['GET', 'POST'])
def audience_analysis(analysis_id):
    # Load analysis data from file
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found. Please submit the form to generate a new analysis.')
        return redirect(url_for('main.index'))
    
    # Initialize the terminal objectives form
    form = TerminalObjectivesForm()
    
    # Pre-populate the form if terminal objectives exist
    if 'terminal_objectives' in analysis_data:
        form.terminal_objectives.data = analysis_data['terminal_objectives']
    
    if form.validate_on_submit():
        # Get terminal objectives from form
        terminal_objectives = form.terminal_objectives.data
        
        # Update the analysis data
        analysis_data['terminal_objectives'] = terminal_objectives
        
        # Generate task analysis
        task_analysis = generate_task_analysis(
            analysis_data['course_topic'], 
            analysis_data['audience_type'],
            terminal_objectives
        )
        
        # Add task analysis to the data
        analysis_data['task_analysis'] = task_analysis
        
        # Save updated analysis
        save_analysis(analysis_id, analysis_data)
        
        # AnalysisLog.update_by_analysis_id(
        #     analysis_id=analysis_id,
        #     data=analysis_data
        # )
        
        # Redirect to task analysis page
        return redirect(url_for('main.task_analysis', analysis_id=analysis_id))
    
    # Convert Markdown to HTML
    audience_analysis_html = markdown.markdown(analysis_data['audience_analysis'])
    
    # For GET request, display the audience analysis with terminal objectives form
    return render_template('audience_analysis.html', 
                          audience_analysis=audience_analysis_html,
                          course_topic=analysis_data['course_topic'],
                          current_date=analysis_data['generated_date'],
                          analysis_id=analysis_id,
                          form=form,
                          analysis_data=analysis_data)  # Pass the full analysis_data

@main.route('/task_analysis/<analysis_id>')
def task_analysis(analysis_id):
    # Load analysis data from file
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found. Please submit the form to generate a new analysis.')
        return redirect(url_for('main.index'))
    
    # Convert Markdown to HTML
    task_analysis_html = markdown.markdown(analysis_data['task_analysis'])
    
    return render_template('task_analysis.html', 
                          task_analysis=task_analysis_html,
                          course_topic=analysis_data['course_topic'],
                          current_date=analysis_data['generated_date'],
                          analysis_id=analysis_id)

@main.route('/prepare_course_design/<analysis_id>', methods=['GET', 'POST'])
def prepare_course_design(analysis_id):
    """
    Prepare for course design generation by collecting additional requirements.
    """
    # Load analysis data from file
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found. Please submit the form to generate a new analysis.')
        return redirect(url_for('main.index'))
    
    # Check if task analysis exists
    if 'task_analysis' not in analysis_data:
        flash('Task analysis not found. Please complete task analysis first.')
        return redirect(url_for('main.audience_analysis', analysis_id=analysis_id))
    
    # Initialize form for additional requirements
    form = CourseDesignRequirementsForm()
    
    if form.validate_on_submit():
        # Get form data
        course_duration = form.course_duration.data
        delivery_format = form.delivery_format.data
        module_count = form.module_count.data
        additional_requirements = form.additional_requirements.data
        
        # Get component options
        generate_structure = form.generate_structure.data
        generate_strategies = form.generate_strategies.data
        generate_assessment = form.generate_assessment.data
        
        # Build component list
        components = []
        if generate_structure:
            components.append('structure')
        if generate_strategies:
            components.append('strategies')
        if generate_assessment:
            components.append('assessment')
            
        # Make sure at least one component is selected
        if not components:
            flash('Please select at least one component to generate.')
            return render_template('prepare_course_design.html',
                                 form=form,
                                 analysis_id=analysis_id,
                                 course_topic=analysis_data['course_topic'],
                                 audience_type=analysis_data['audience_type'],
                                 audience_analysis_html=markdown.markdown(analysis_data['audience_analysis']),
                                 task_analysis_html=markdown.markdown(analysis_data['task_analysis']),
                                 terminal_objectives=analysis_data.get('terminal_objectives', ''),
                                 current_date=analysis_data['generated_date'])
        
        # Add to analysis data
        analysis_data['course_duration'] = course_duration
        analysis_data['delivery_format'] = delivery_format
        analysis_data['module_count'] = module_count
        analysis_data['additional_requirements'] = additional_requirements
        analysis_data['design_components'] = components
        
        # Save updated analysis
        save_analysis(analysis_id, analysis_data)
        
        # Redirect to generate course design
        return redirect(url_for('main.generate_course_design', analysis_id=analysis_id))
    
    # Convert Markdown to HTML for display
    audience_analysis_html = markdown.markdown(analysis_data['audience_analysis'])
    task_analysis_html = markdown.markdown(analysis_data['task_analysis'])
    
    return render_template('prepare_course_design.html',
                          form=form,
                          analysis_id=analysis_id,
                          course_topic=analysis_data['course_topic'],
                          audience_type=analysis_data['audience_type'],
                          audience_analysis_html=audience_analysis_html,
                          task_analysis_html=task_analysis_html,
                          terminal_objectives=analysis_data.get('terminal_objectives', ''),
                          current_date=analysis_data['generated_date'])

@main.route('/generate_course_design/<analysis_id>', methods=['GET'])
def generate_course_design(analysis_id):
    # Load analysis data from file
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found. Please submit the form to generate a new analysis.')
        return redirect(url_for('main.index'))
    
    # Check if we need to regenerate any components
    components_to_generate = analysis_data.get('design_components', ['structure', 'strategies', 'assessment'])
    
    # Check which components already exist
    if 'course_structure' in analysis_data and 'structure' in components_to_generate:
        components_to_generate.remove('structure')
    if 'instructional_strategies' in analysis_data and 'strategies' in components_to_generate:
        components_to_generate.remove('strategies')
    if 'assessment_plan' in analysis_data and 'assessment' in components_to_generate:
        components_to_generate.remove('assessment')
    
    # If all components exist and no new ones are requested, redirect to view
    if not components_to_generate:
        flash('Course design already exists. Redirecting to existing design.')
        return redirect(url_for('main.view_course_design', analysis_id=analysis_id))
    
    # Generate course design components
    try:
        # Extract module count if specified
        module_count = analysis_data.get('module_count')
        if module_count and isinstance(module_count, str):
            try:
                module_count = int(module_count)
            except ValueError:
                module_count = None
        
        # Generate only the requested components
        updated_analysis_data = generate_comprehensive_course_design(
            analysis_data, 
            components=components_to_generate,
            module_count=module_count
        )
        
        # Save the updated analysis
        save_analysis(analysis_id, updated_analysis_data)
        
        # Create success message based on generated components
        component_names = {
            'structure': 'Course Structure',
            'strategies': 'Instructional Strategies',
            'assessment': 'Assessment Plan'
        }
        generated_names = [component_names[comp] for comp in components_to_generate]
        
        if len(generated_names) == 1:
            message = f"{generated_names[0]} generated successfully!"
        elif len(generated_names) == 2:
            message = f"{generated_names[0]} and {generated_names[1]} generated successfully!"
        elif len(generated_names) > 2:
            message = f"{', '.join(generated_names[:-1])} and {generated_names[-1]} generated successfully!"
        else:
            message = "Course design components generated successfully!"
            
        flash(message)
        return redirect(url_for('main.view_course_design', analysis_id=analysis_id))
    
    except Exception as e:
        flash(f'Error generating course design: {str(e)}')
        return redirect(url_for('main.task_analysis', analysis_id=analysis_id))

@main.route('/view_course_design/<analysis_id>')
def view_course_design(analysis_id):
    # Load analysis data from file
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found. Please submit the form to generate a new analysis.')
        return redirect(url_for('main.index'))
    
    # Check if course design exists
    if 'course_structure' not in analysis_data:
        flash('Course design not found. Generating now...')
        return redirect(url_for('main.generate_course_design', analysis_id=analysis_id))
    
    # Convert Markdown to HTML
    course_structure_html = markdown.markdown(analysis_data['course_structure'])
    instructional_strategies_html = markdown.markdown(analysis_data['instructional_strategies'])
    assessment_plan_html = markdown.markdown(analysis_data['assessment_plan'])
    
    return render_template('course_design.html', 
                          course_structure=course_structure_html,
                          instructional_strategies=instructional_strategies_html,
                          assessment_plan=assessment_plan_html,
                          course_topic=analysis_data['course_topic'],
                          current_date=analysis_data.get('course_design_generated_date', 
                                                      analysis_data.get('generated_date')),
                          analysis_id=analysis_id)

@main.route('/edit_course_design/<analysis_id>', methods=['GET', 'POST'])
def edit_course_design(analysis_id):
    # Load analysis data from file
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found.')
        return redirect(url_for('main.index'))
    
    # Check if course design exists
    if 'course_structure' not in analysis_data:
        flash('Course design not found. Generating now...')
        return redirect(url_for('main.generate_course_design', analysis_id=analysis_id))
    
    if request.method == 'POST':
        # Update the analysis data with edited content
        analysis_data['course_structure'] = request.form.get('course_structure', '')
        analysis_data['instructional_strategies'] = request.form.get('instructional_strategies', '')
        analysis_data['assessment_plan'] = request.form.get('assessment_plan', '')
        analysis_data['last_edited'] = datetime.now().strftime("%B %d, %Y at %H:%M")
        
        # Save the updated analysis
        save_analysis(analysis_id, analysis_data)
        flash('Course design updated successfully!')
        
        return redirect(url_for('main.view_course_design', analysis_id=analysis_id))
    
    # For GET request, display the edit form
    return render_template('edit_course_design.html', 
                          analysis_id=analysis_id,
                          course_structure=analysis_data['course_structure'],
                          instructional_strategies=analysis_data['instructional_strategies'],
                          assessment_plan=analysis_data['assessment_plan'],
                          course_topic=analysis_data['course_topic'])

@main.route('/download_course_design/<analysis_id>')
def download_course_design(analysis_id):
    # Load analysis data from file
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found.')
        return redirect(url_for('main.index'))
    
    # Check if course design exists
    if 'course_structure' not in analysis_data:
        flash('Course design not found. Generating now...')
        return redirect(url_for('main.generate_course_design', analysis_id=analysis_id))
    
    # Create a new Word document
    doc = Document()
    
    # Add title
    title = doc.add_heading(f"Course Design: {analysis_data['course_topic']}", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Add generated date
    date_paragraph = doc.add_paragraph()
    date_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_paragraph.add_run(f"Generated on {analysis_data.get('course_design_generated_date', analysis_data['generated_date'])}").italic = True
    
    doc.add_paragraph()  # Add some space
    
    # Add Course Structure
    doc.add_heading("Course Structure", 1)
    markdown_to_docx(doc, analysis_data['course_structure'])
    
    doc.add_page_break()
    
    # Add Instructional Strategies
    doc.add_heading("Instructional Strategies", 1)
    markdown_to_docx(doc, analysis_data['instructional_strategies'])
    
    doc.add_page_break()
    
    # Add Assessment Plan
    doc.add_heading("Assessment Plan", 1)
    markdown_to_docx(doc, analysis_data['assessment_plan'])
    
    # Save to a BytesIO object
    f = io.BytesIO()
    doc.save(f)
    f.seek(0)
    
    # Send the file for download
    return send_file(
        f,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name=f"Course_Design_{analysis_data['course_topic'].replace(' ', '_')}.docx"
    )

@main.route('/results/<analysis_id>')
def results(analysis_id):
    # Load analysis data from file
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found. Please submit the form to generate a new analysis.')
        return redirect(url_for('main.index'))
    
    # Check what components exist
    has_audience = 'audience_analysis' in analysis_data
    has_task = 'task_analysis' in analysis_data
    has_course_design = 'course_structure' in analysis_data
    
    # Convert Markdown to HTML if components exist
    audience_analysis_html = markdown.markdown(analysis_data['audience_analysis']) if has_audience else None
    task_analysis_html = markdown.markdown(analysis_data['task_analysis']) if has_task else None
    
    if has_course_design:
        course_structure_html = markdown.markdown(analysis_data['course_structure'])
        instructional_strategies_html = markdown.markdown(analysis_data['instructional_strategies'])
        assessment_plan_html = markdown.markdown(analysis_data['assessment_plan'])
    else:
        course_structure_html = None
        instructional_strategies_html = None
        assessment_plan_html = None
    
    return render_template('results.html', 
                         course_topic=analysis_data['course_topic'],
                         audience_type=analysis_data['audience_type'],
                         current_date=analysis_data['generated_date'],
                         analysis_id=analysis_id,
                         audience_analysis_html=audience_analysis_html,
                         task_analysis_html=task_analysis_html,
                         course_structure_html=course_structure_html,
                         instructional_strategies_html=instructional_strategies_html,
                         assessment_plan_html=assessment_plan_html,
                         has_audience=has_audience,
                         has_task=has_task,
                         has_course_design=has_course_design)

# For backward compatibility
@main.route('/results')
def results_redirect():
    analysis_id = session.get('current_analysis_id')
    if analysis_id:
        return redirect(url_for('main.results', analysis_id=analysis_id))
    else:
        flash('No analysis results found. Please submit the form first.')
        return redirect(url_for('main.index'))

@main.route('/edit_audience/<analysis_id>', methods=['GET', 'POST'])
def edit_audience_analysis(analysis_id):
    try:
        # Load analysis data from file
        analysis_data = load_analysis(analysis_id)
        
        if not analysis_data:
            flash('Analysis not found.')
            return redirect(url_for('main.index'))
        
        if request.method == 'POST':
            # Update only the audience analysis
            analysis_data['audience_analysis'] = request.form.get('audience_analysis', '')
            
            # Save the updated analysis
            save_analysis(analysis_id, analysis_data)
            flash('Audience analysis updated successfully!')
            
            # Redirect back to audience analysis page
            return redirect(url_for('main.audience_analysis', analysis_id=analysis_id))
        
        # For GET request, display the edit form for audience analysis only
        return render_template('edit_audience.html', 
                            analysis_id=analysis_id,
                            audience_analysis=analysis_data['audience_analysis'],
                            course_topic=analysis_data['course_topic'])
        
    except Exception as e:
        flash(f"Error: {str(e)}")
        return redirect(url_for('main.index'))

@main.route('/edit_task/<analysis_id>', methods=['GET', 'POST'])
def edit_task_analysis(analysis_id):
    try:
        # Load analysis data from file
        analysis_data = load_analysis(analysis_id)
        
        if not analysis_data:
            flash('Analysis not found.')
            return redirect(url_for('main.index'))
        
        if request.method == 'POST':
            # Update only the task analysis
            analysis_data['task_analysis'] = request.form.get('task_analysis', '')
            
            # Save the updated analysis
            save_analysis(analysis_id, analysis_data)
            flash('Task analysis updated successfully!')
            
            # Redirect back to task analysis page
            return redirect(url_for('main.task_analysis', analysis_id=analysis_id))
        
        # For GET request, display the edit form for task analysis only
        return render_template('edit_task.html', 
                            analysis_id=analysis_id,
                            task_analysis=analysis_data['task_analysis'],
                            course_topic=analysis_data['course_topic'])
        
    except Exception as e:
        flash(f"Error: {str(e)}")
        return redirect(url_for('main.index'))

@main.route('/download_audience/<analysis_id>')
def download_audience_analysis(analysis_id):
    # Load analysis data from file
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found.')
        return redirect(url_for('main.index'))
    
    # Create a new Word document
    doc = Document()
    
    # Add title
    title = doc.add_heading(f"Audience Analysis: {analysis_data['course_topic']}", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Add generated date
    date_paragraph = doc.add_paragraph()
    date_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_paragraph.add_run(f"Generated on {analysis_data['generated_date']}").italic = True
    
    doc.add_paragraph()  # Add some space
    
    # Convert markdown to formatted Word document
    markdown_to_docx(doc, analysis_data['audience_analysis'])
    
    # Save to a BytesIO object
    f = io.BytesIO()
    doc.save(f)
    f.seek(0)
    
    # Send the file for download
    return send_file(
        f,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name=f"Audience_Analysis_{analysis_data['course_topic'].replace(' ', '_')}.docx"
    )

@main.route('/download_task/<analysis_id>')
def download_task_analysis(analysis_id):
    # Load analysis data from file
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found.')
        return redirect(url_for('main.index'))
    
    # Create a new Word document
    doc = Document()
    
    # Add title
    title = doc.add_heading(f"Task Analysis: {analysis_data['course_topic']}", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Add generated date
    date_paragraph = doc.add_paragraph()
    date_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_paragraph.add_run(f"Generated on {analysis_data['generated_date']}").italic = True
    
    doc.add_paragraph()  # Add some space
    
    # Convert markdown to formatted Word document
    markdown_to_docx(doc, analysis_data['task_analysis'])
    
    # Save to a BytesIO object
    f = io.BytesIO()
    doc.save(f)
    f.seek(0)
    
    # Send the file for download
    return send_file(
        f,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name=f"Task_Analysis_{analysis_data['course_topic'].replace(' ', '_')}.docx"
    )

@main.route('/generate_additional_components/<analysis_id>', methods=['POST'])
def generate_additional_components(analysis_id):
    # Load analysis data
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found.')
        return redirect(url_for('main.index'))
    
    # Get components to generate
    components = []
    if request.form.get('generate_structure') and 'course_structure' not in analysis_data:
        components.append('structure')
    if request.form.get('generate_strategies') and 'instructional_strategies' not in analysis_data:
        components.append('strategies')
    if request.form.get('generate_assessment') and 'assessment_plan' not in analysis_data:
        components.append('assessment')
    
    # Generate the requested components
    if components:
        try:
            # Extract module count if specified
            module_count = analysis_data.get('module_count')
            if module_count and isinstance(module_count, str):
                try:
                    module_count = int(module_count)
                except ValueError:
                    module_count = None
            
            # Generate components
            updated_analysis_data = generate_comprehensive_course_design(
                analysis_data, 
                components=components,
                module_count=module_count
            )
            
            # Save the updated analysis
            save_analysis(analysis_id, updated_analysis_data)
            
            # Create success message
            component_names = {
                'structure': 'Course Structure',
                'strategies': 'Instructional Strategies',
                'assessment': 'Assessment Plan'
            }
            generated_names = [component_names[comp] for comp in components]
            
            if len(generated_names) == 1:
                message = f"{generated_names[0]} generated successfully!"
            elif len(generated_names) == 2:
                message = f"{generated_names[0]} and {generated_names[1]} generated successfully!"
            else:
                message = f"{', '.join(generated_names[:-1])}, and {generated_names[-1]} generated successfully!"
                
            flash(message)
        except Exception as e:
            flash(f'Error generating additional components: {str(e)}')
    else:
        flash('No components selected for generation.')
    
    return redirect(url_for('main.view_course_design', analysis_id=analysis_id))
# Add these imports at the top of your routes.py if not already present
from models.course_materials import CourseMaterialsGenerator, generate_course_materials
import zipfile
import logging
import io
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

logger = logging.getLogger(__name__)

@main.route('/prepare_materials/<analysis_id>')
def prepare_materials(analysis_id):
    """Display the material generation preparation page."""
    # Load analysis data
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found.')
        return redirect(url_for('main.index'))
    
    # Check if course design exists
    if 'course_structure' not in analysis_data:
        flash('Course design not found. Please complete course design first.')
        return redirect(url_for('main.prepare_course_design', analysis_id=analysis_id))
    
    # Extract modules from course structure
    generator = CourseMaterialsGenerator(analysis_data)
    modules = generator.modules
    
    # Check if materials already exist
    existing_materials = analysis_data.get('course_materials', {})
    
    return render_template('prepare_materials.html',
                          analysis_id=analysis_id,
                          course_topic=analysis_data['course_topic'],
                          audience_type=analysis_data['audience_type'],
                          design_date=analysis_data.get('course_design_generated_date', 
                                                      analysis_data['generated_date']),
                          modules=modules,
                          existing_materials=existing_materials)

@main.route('/generate_materials/<analysis_id>', methods=['POST'])
def generate_materials(analysis_id):
    """Generate course materials based on user selections."""
    # Load analysis data
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found.')
        return redirect(url_for('main.index'))
    
    try:
        # Get form data
        selected_modules = request.form.getlist('selected_modules')
        selected_modules = [int(m) for m in selected_modules]
        
        components = request.form.getlist('components')
        detail_level = request.form.get('detail_level', 'comprehensive')
        format_preference = request.form.get('format_preference', 'structured')
        additional_notes = request.form.get('additional_notes', '')
        
        # Validate selections
        if not selected_modules:
            flash('Please select at least one module.')
            return redirect(url_for('main.prepare_materials', analysis_id=analysis_id))
        
        if not components:
            flash('Please select at least one component type.')
            return redirect(url_for('main.prepare_materials', analysis_id=analysis_id))
        
        # Generate materials
        logger.info(f"Generating materials for modules {selected_modules} with components {components}")
        
        materials = generate_course_materials(
            analysis_data,
            selected_modules=selected_modules,
            components=components
        )
        
        # Add metadata
        materials['metadata'] = {
            'generated_date': datetime.now().strftime("%B %d, %Y at %H:%M"),
            'total_modules': len(materials['modules']),
            'components_generated': components,
            'detail_level': detail_level,
            'format_preference': format_preference,
            'additional_notes': additional_notes
        }
        
        # Merge with existing materials if any
        if 'course_materials' in analysis_data:
            existing_modules = {m['number']: m for m in analysis_data['course_materials'].get('modules', [])}
            
            # Update with new materials
            for new_module in materials['modules']:
                module_num = new_module['number']
                if module_num in existing_modules:
                    # Merge components
                    existing_modules[module_num]['components'].update(new_module['components'])
                else:
                    existing_modules[module_num] = new_module
            
            # Convert back to list
            materials['modules'] = list(existing_modules.values())
            materials['modules'].sort(key=lambda x: x['number'])
        
        # Save materials (use consistent key name)
        analysis_data['course_materials'] = materials
        analysis_data['materials_generated_date'] = datetime.now().strftime("%B %d, %Y at %H:%M")
        save_analysis(analysis_id, analysis_data)
        
        flash(f'Successfully generated {len(components)} component(s) for {len(selected_modules)} module(s)!')
        return redirect(url_for('main.view_materials', analysis_id=analysis_id))
        
    except Exception as e:
        logger.error(f"Error generating materials: {str(e)}")
        error_message = str(e)
        flash(f'Error generating materials: {error_message}')
        return redirect(url_for('main.prepare_materials', analysis_id=analysis_id))

# UPDATE the existing view_materials route:
@main.route('/view_materials/<analysis_id>')
def view_materials(analysis_id):
    """Display the materials dashboard."""
    # Load analysis data
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found.')
        return redirect(url_for('main.index'))
    
    # Check if materials exist (use consistent key name)
    if 'course_materials' not in analysis_data:
        flash('No materials generated yet.')
        return redirect(url_for('main.prepare_materials', analysis_id=analysis_id))
    
    materials = analysis_data['course_materials']
    
    # Calculate statistics
    stats = calculate_materials_stats(materials)
    
    # Calculate individual stats for template
    total_lesson_plans = sum(1 for module in materials.get('modules', []) 
                           if 'lesson_plan' in module.get('components', {}))
    total_activities = sum(1 for module in materials.get('modules', []) 
                         if 'activities' in module.get('components', {}))
    total_assessments = sum(1 for module in materials.get('modules', []) 
                          if 'assessments' in module.get('components', {}))
    
    return render_template('materials_dashboard.html',
                          analysis_id=analysis_id,
                          course_topic=analysis_data['course_topic'],
                          audience_type=analysis_data['audience_type'],
                          generation_date=materials.get('metadata', {}).get('generated_date', 'Unknown'),
                          materials=materials,
                          total_lesson_plans=total_lesson_plans,
                          total_activities=total_activities,
                          total_assessments=total_assessments,
                          stats=stats)

# UPDATE the existing view_material route:
@main.route('/view_material/<analysis_id>/<int:module_id>/<material_type>')
def view_material(analysis_id, module_id, material_type):
    """View a specific material component."""
    # Load analysis data
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data or 'course_materials' not in analysis_data:
        flash('Materials not found.')
        return redirect(url_for('main.index'))
    
    # Find the module
    module = None
    for m in analysis_data['course_materials']['modules']:
        if m['number'] == module_id:
            module = m
            break
    
    if not module:
        flash('Module not found.')
        return redirect(url_for('main.view_materials', analysis_id=analysis_id))
    
    # Get the specific material
    material = module['components'].get(material_type)
    
    if not material:
        flash(f'{material_type.replace("_", " ").title()} not found for this module.')
        return redirect(url_for('main.view_materials', analysis_id=analysis_id))
    
    return render_template('view_material.html',
                          analysis_id=analysis_id,
                          course_topic=analysis_data['course_topic'],
                          module_number=module_id,
                          material_type=material_type,
                          material=material)

# UPDATE the existing edit_material route:
@main.route('/edit_material/<analysis_id>/<int:module_id>/<material_type>', methods=['GET', 'POST'])
def edit_material(analysis_id, module_id, material_type):
    """Edit a specific material component."""
    # Load analysis data
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data or 'course_materials' not in analysis_data:
        flash('Materials not found.')
        return redirect(url_for('main.index'))
    
    # Find the module
    module_idx = None
    module = None
    for idx, m in enumerate(analysis_data['course_materials']['modules']):
        if m['number'] == module_id:
            module_idx = idx
            module = m
            break
    
    if not module:
        flash('Module not found.')
        return redirect(url_for('main.view_materials', analysis_id=analysis_id))
    
    # Get the specific material
    material = module['components'].get(material_type)
    
    if not material:
        flash(f'{material_type.replace("_", " ").title()} not found for this module.')
        return redirect(url_for('main.view_materials', analysis_id=analysis_id))
    
    if request.method == 'POST':
        # Update the material with form data
        updated_content = request.form.get('material_content', '')
        
        try:
            # Save the updated material as raw content for now
            if isinstance(material, dict):
                material['raw_content'] = updated_content
            else:
                material = {'raw_content': updated_content}
            
            analysis_data['course_materials']['modules'][module_idx]['components'][material_type] = material
            save_analysis(analysis_id, analysis_data)
            
            flash(f'{material_type.replace("_", " ").title()} updated successfully!')
            return redirect(url_for('main.view_material', 
                                  analysis_id=analysis_id, 
                                  module_id=module_id, 
                                  material_type=material_type))
            
        except Exception as e:
            flash(f'Error updating material: {str(e)}')
            return render_template('edit_material.html',
                                 analysis_id=analysis_id,
                                 module_id=module_id,
                                 material_type=material_type,
                                 material_content=updated_content)
    
    # For GET request, show edit form
    if isinstance(material, dict):
        material_content = material.get('raw_content', json.dumps(material, indent=2))
        # material_content_format = escape_control_characters(material_content)
        # material_raw = json.loads(material_content_format)
        # raw_main_content = material_raw['main_content']
        # print(raw_main_content)
    else:
        material_content = str(material)
    
    return render_template('edit_material.html',
                          analysis_id=analysis_id,
                          module_id=module_id,
                          material_type=material_type,
                          material_content=material_content)

@main.route('/generate_single_material/<analysis_id>/<int:module_id>/<material_type>')
def generate_single_material(analysis_id, module_id, material_type):
    """Generate a single material component for a specific module."""
    # Load analysis data
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data:
        flash('Analysis not found.')
        return redirect(url_for('main.index'))
    
    try:
        # Generate the specific material
        generator = CourseMaterialsGenerator(analysis_data)
        
        # Map material type to component name
        component_map = {
            'lesson_plan': 'lesson_plans',
            'content': 'content',
            'activities': 'activities',
            'assessments': 'assessments',
            'instructor_guide': 'instructor_guides'
        }
        
        component = component_map.get(material_type)
        if not component:
            flash('Invalid material type.')
            return redirect(url_for('main.view_materials', analysis_id=analysis_id))
        
        # Generate material for single module and component
        new_materials = generator.generate_all_materials(
            selected_modules=[module_id],
            components=[component]
        )
        
        # Initialize course_materials if it doesn't exist
        if 'course_materials' not in analysis_data:
            analysis_data['course_materials'] = {'modules': []}
        
        # Find and update the specific module
        module_found = False
        for idx, module in enumerate(analysis_data['course_materials']['modules']):
            if module['number'] == module_id:
                # Update the specific component
                if len(new_materials['modules']) > 0:
                    new_component = new_materials['modules'][0]['components'].get(material_type)
                    if new_component:
                        if 'components' not in module:
                            module['components'] = {}
                        module['components'][material_type] = new_component
                module_found = True
                break
        
        if not module_found and len(new_materials['modules']) > 0:
            # Module not found in existing materials, add it
            analysis_data['course_materials']['modules'].append(new_materials['modules'][0])
            analysis_data['course_materials']['modules'].sort(key=lambda x: x['number'])
        
        # Save updated analysis
        save_analysis(analysis_id, analysis_data)
        
        flash(f'{material_type.replace("_", " ").title()} generated successfully!')
        return redirect(url_for('main.view_material', 
                              analysis_id=analysis_id, 
                              module_id=module_id, 
                              material_type=material_type))
        
    except Exception as e:
        logger.error(f"Error generating single material: {str(e)}")
        flash(f'Error generating material: {str(e)}')
        return redirect(url_for('main.view_materials', analysis_id=analysis_id))

@main.route('/regenerate_module/<analysis_id>/<int:module_id>')
def regenerate_module(analysis_id, module_id):
    """Regenerate all materials for a specific module."""
    try:
        # Load analysis data
        analysis_data = load_analysis(analysis_id)
        
        if not analysis_data:
            flash('Analysis not found.')
            return redirect(url_for('main.index'))
        
        # Generate all materials for the module
        generator = CourseMaterialsGenerator(analysis_data)
        materials = generator.generate_all_materials(
            selected_modules=[module_id],
            components=['lesson_plans', 'content', 'activities', 'assessments', 'instructor_guides']
        )
        
        # Initialize course_materials if it doesn't exist
        if 'course_materials' not in analysis_data:
            analysis_data['course_materials'] = {'modules': []}
        
        # Replace the module materials
        modules = analysis_data['course_materials']['modules']
        # Remove existing module
        modules[:] = [mod for mod in modules if mod['number'] != module_id]
        # Add regenerated module
        if len(materials['modules']) > 0:
            modules.extend(materials['modules'])
            modules.sort(key=lambda x: x['number'])
        
        # Save updated analysis
        save_analysis(analysis_id, analysis_data)
        
        flash(f'Module {module_id} regenerated successfully!')
        return redirect(url_for('main.view_materials', analysis_id=analysis_id))
        
    except Exception as e:
        flash(f'Error regenerating module {module_id}: {str(e)}')
        return redirect(url_for('main.view_materials', analysis_id=analysis_id))



def clean_markdown_text(text):
    if not isinstance(text, str):
        return text

    text = text.encode("utf-8").decode("unicode_escape")  # Convert \n, \", etc.
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)          # Remove bold (**bold**)
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)  # Remove bullet points
    text = re.sub(r'\\n', '\n', text)                     # Clean up double-escaped \n
    text = re.sub(r'\\', '', text)                        # Remove leftover backslashes
    return text.strip()

def clean_json_structure(obj):
    if isinstance(obj, dict):
        return {k: clean_json_structure(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_json_structure(item) for item in obj]
    elif isinstance(obj, str):
        return clean_markdown_text(obj)
    else:
        return obj
import json
import re

def clean_groq_response(raw_response):
    # Step 1: Remove outer single quotes
    if raw_response.startswith("'") and raw_response.endswith("'"):
        raw_response = raw_response[1:-1]

    # Step 2: Remove Markdown-style ```json and ``` wrappers
    if raw_response.startswith("```json") or raw_response.startswith("```"):
        raw_response = re.sub(r"^```json\s*|```$", "", raw_response).strip()

    # Step 3: Decode escaped characters
    try:
        raw_response = raw_response.encode().decode('unicode_escape')
    except Exception as e:
        logger.warning(f"Unicode decode issue: {e}")

    # Step 4: Try to parse JSON
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to decode JSON from Groq response: {e}")


@main.route('/download_all_materials/<analysis_id>')
def download_all_materials(analysis_id):
    """Download all materials as a ZIP file."""
    scorm_version = request.args.get('scorm', '').strip()
    include_scorm = scorm_version == '2004'

    # Load analysis data
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data or 'course_materials' not in analysis_data:
        flash('Materials not found.')
        return redirect(url_for('main.view_materials', analysis_id=analysis_id))
    
    try:
        # Create a ZIP file in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add overview document
            overview = create_materials_overview(analysis_data)
            zip_file.writestr('Course_Materials_Overview.txt', overview)
            
            navigation_data = create_combined_navigation(analysis_data['course_materials'])
            zip_file.writestr('navigation.json', json.dumps(navigation_data, indent=2))

            # Add SCORM runtime files if requested
            if include_scorm:
                scorm_files = {
                    'index_lms.html': os.path.join(current_app.root_path, 'static', 'index_lms.html'),
                    'course.js': os.path.join(current_app.root_path, 'static', 'js', 'course.js'),
                    'ADLwrapper.js': os.path.join(current_app.root_path, 'static', 'js', 'ADLwrapper.js')
                }
                
                for arcname, filepath in scorm_files.items():
                    if os.path.exists(filepath):
                        zip_file.write(filepath, arcname)
                    else:
                        current_app.logger.warning(f'SCORM file missing: {filepath}')
                
                # Generate and add manifest
                manifest_xml = create_scorm_manifest(
                    course_title=analysis_data['course_topic'],
                    modules=analysis_data['course_materials']['modules']
                )
                zip_file.writestr('imsmanifest.xml', manifest_xml)

            

            # Add each module's materials
            for module in analysis_data['course_materials']['modules']:
                module_folder = f"Module_{module['number']}_{sanitize_filename(module['title'])}"
                module_title = module['title']
                module_number = module['number']
                # Collect chapter/component names
                # chapters = []
                # for component_type, component_data in module['components'].items():
                #     if component_data:
                #         # Format component type as title (e.g., "lesson_plan" -> "Lesson Plan")
                #         chapter_name = component_type.replace('_', ' ').title()
                #         chapters.append(chapter_name)
                
                
                # Add each component
                for component_type, component_data in module['components'].items():
                    if component_data:
                        # Create filename
                        filename = f"{module_folder}/{component_type.replace('_', ' ').title()}.json"
                        
                        # Add to ZIP
                        content = json.dumps(component_data, indent=2)
                        zip_file.writestr(filename, content)
                        
                        # Also create a formatted text version
                        text_content = format_material_as_text(component_type, component_data)
                        text_filename = f"{module_folder}/{component_type.replace('_', ' ').title()}.txt"
                        zip_file.writestr(text_filename, text_content)

                       # 3. Clean JSON (structured � parsed from markdown if needed)
                        component_type = component_type.lower()

                        if component_type in ["assessments", "assessment"]:
                            # print('assessments')
                            # if 'raw_content' in component_data:
                            #     asses_json_output = parse_assessment_to_json(component_data['raw_content'])
                            # elif 'comprehensive_assessments' in component_data:
                            #     #asses_json_output = parse_assessment_to_json(component_data['comprehensive_assessments'])
                            #     combined_content = (
                            #         component_data.get('comprehensive_assessments', '') + '\n' +
                            #         component_data.get('Practice_questions', '')
                            #     )
                            #     asses_json_output = parse_assessment_to_json(combined_content)
 
                            # else:
                            #     asses_json_output = None  # or handle the missing key case appropriately
 
                           
                            # cleaned_data = asses_json_output
                            client = GroqClient()
                            print("Generating assessments from AI")
                            system_prompt = "You are an expert educational content formatter. Your task is to output only JSON and nothing else. Do not include explanations, Markdown formatting, or comments. Use the following structure exactly with only properties mentioned here: { \"comprehensive_assessments\": { \"knowledge_check_questions\": { \"multiple_choice_questions\": [ { \"question_number\": <Question Number>, \"question\": \"<Question Text>\", \"options\": [\"<Option 1>\", \"<Option 2>\", \"...\"], \"correct_answer\": \"<Correct Answer>\", \"content_reference\": \"<Content Reference>\", \"learning_objective_tested\": \"<Learning Objective>\" }, \"...\" ], \"true_false_questions\": [ { \"question_number\": <Question Number>, \"question\": \"<Question Text>\", \"correct_answer\": <Boolean>, \"content_reference\": \"<Content Reference>\", \"learning_objective_tested\": \"<Learning Objective>\" }, \"...\" ], \"short_answer_questions\": [ { \"question_number\": <Question Number>, \"question\": \"<Question Text>\", \"sample_correct_answer\": \"<Sample Answer>\", \"key_points_required\": [\"<Key Point 1>\", \"<Key Point 2>\", \"...\"], \"content_reference\": \"<Content Reference>\", \"learning_objective_tested\": \"<Learning Objective>\" }, \"...\" ] }, \"application_questions\": { \"scenario_based_questions\": [ { \"question_number\": <Question Number>, \"question\": \"<Question Text>\", \"sample_correct_answer\": \"<Sample Answer>\", \"assessment_rubric\": { \"excellent\": { \"score\": <Score>, \"description\": \"<Description>\" }, \"good\": { \"score\": <Score>, \"description\": \"<Description>\" }, \"satisfactory\": { \"score\": <Score>, \"description\": \"<Description>\" }, \"needs_improvement\": { \"score\": <Score>, \"description\": \"<Description>\" } }, \"content_connection\": \"<Content Connection>\" }, \"...\" ], \"problem_solving_questions\": [ { \"question_number\": <Question Number>, \"question\": \"<Question Text>\", \"step_by_step_solution\": [\"<Step 1>\", \"<Step 2>\", \"...\"], \"common_mistakes\": [\"<Mistake 1>\", \"<Mistake 2>\", \"...\"], \"full_credit_answer\": \"<Full Credit Answer>\" }, \"...\" ] }, \"analysis_and_synthesis_questions\": [ { \"question_number\": <Question Number>, \"question\": \"<Question Text>\", \"sample_answer\": \"<Sample Answer>\", \"grading_criteria\": [\"<Criterion 1>\", \"<Criterion 2>\", \"...\"], \"content_references\": [\"<Reference 1>\", \"<Reference 2>\", \"...\"] }, \"...\" ], \"practical_assessment_project\": { \"project_description\": \"<Project Description>\", \"project_requirements\": [\"<Requirement 1>\", \"<Requirement 2>\", \"...\"], \"deliverables\": [\"<Deliverable 1>\", \"<Deliverable 2>\", \"...\"], \"grading_rubric\": { \"concept_application\": { \"weight\": \"<Weight>\", \"description\": \"<Description>\" }, \"technical_accuracy\": { \"weight\": \"<Weight>\", \"description\": \"<Description>\" }, \"completeness\": { \"weight\": \"<Weight>\", \"description\": \"<Description>\" }, \"quality_of_explanation\": { \"weight\": \"<Weight>\", \"description\": \"<Description>\" }, \"innovation_creativity\": { \"weight\": \"<Weight>\", \"description\": \"<Description>\" } } }, \"self_assessment_tools\": { \"knowledge_self_check\": [ { \"question\": \"<Question Text>\", \"scale\": \"<Scale>\" }, \"...\" ], \"skills_self_assessment\": [ { \"question\": \"<Question Text>\", \"options\": [\"<Option 1>\", \"<Option 2>\", \"...\"] }, \"...\" ] }, \"answer_keys_and_explanations\": { \"note\": \"<Note>\" } }, \"practice_questions\": [ { \"question_number\": <Question Number>, \"question\": \"<Question Text>\", \"options\": [\"<Option 1>\", \"<Option 2>\", \"...\"], \"answer\": \"<Answer>\", \"content_reference\": \"<Content Reference>\", \"study_tip\": \"<Study Tip>\" }, \"...\" ], \"assessment_overview\": { \"total_questions\": \"<Total Questions>\", \"question_types\": [\"<Type 1>\", \"<Type 2>\", \"...\"], \"assessment_features\": [\"<Feature 1>\", \"<Feature 2>\", \"...\"], \"estimated_assessment_time\": \"<Estimated Time>\" } }"
                           
                            raw_response = client.generate(content, system_prompt)
                            # Step 1: Strip the outer single quotes (if present)
                            raw_response = raw_response.strip("'")
                          
                            parsed_json = json.loads(raw_response)
                           
                            cleaned_data = parsed_json
                            clean_json_filename = f"{filename}.clean.json"
                            clean_json_content = json.dumps(cleaned_data, indent=2)
                            zip_file.writestr(clean_json_filename, clean_json_content)
                        

                        elif component_type == "content":
                            # print('content')
                            # json_output = parse_content_to_json_contenttype(component_data['main_content'])
                            # cleaned_data = json_output
                            var_parsed_json = json.loads(content)
                            var_markdown_text = var_parsed_json.get("main_content", "")
                            client = GroqClient()
                            system_prompt = "You are an expert educational content formatter. Your task is to output only JSON and nothing else. Do not include explanations, Markdown formatting, or comments. Use the following structure exactly with only properties mentioned here: {\"chapter\": {\"title\": \"\", \"learningOutcomes\": [], \"overview\": \"\", \"introduction\": \"\", \"topics\": [{\"title\": \"\", \"overview\": \"\", \"coreConcepts\": {\"definition\": \"\", \"theoreticalFoundation\": \"\", \"keyComponents\": []}, \"examples\": [{\"level\": \"\", \"steps\": []}], \"practicalApplications\": \"\", \"challengesAndSolutions\": [{\"challenge\": \"\", \"solution\": \"\"}], \"bestPractices\": []}], \"synthesis\": \"\", \"implementationGuide\": [], \"toolsAndResources\": {\"essentialTools\": [], \"additionalResources\": {\"recommendedReadings\": [], \"onlineTutorials\": [], \"practicePlatforms\": [], \"professionalCommunities\": []}}, \"summary\": \"\", \"glossary\": [{\"term\": \"\", \"definition\": \"\"}]}}}"

                           

                            # Call Groq to get structured response
                            print("Sending chapter markdown to Groq for parsing...")
                            
                            raw_response = client.generate(var_markdown_text, system_prompt)
                          
                            parsed_raw = json.loads(raw_response)

                            # Step 2: Extract the relevant part directly (no Markdown conversion needed)
                            chapter_data = parsed_raw.get('chapter', {})                           

                            # Step 4: Clean the chapter data using your existing clean_json_structure function
                            #cleaned_data = clean_json_structure(chapter_data)
                            
                            output_json = {'chapter': chapter_data}

                            # Step 4: Clean the chapter data using your existing clean_json_structure function
                            cleaned_data = clean_json_structure(output_json)
                            clean_json_filename = f"{filename}.clean.json"
                            clean_json_content = json.dumps(cleaned_data, indent=2)
                            zip_file.writestr(clean_json_filename, clean_json_content)


                        # else:
                        #     cleaned_data = component_data  # fallback: use raw JSON if unknown type
                            

                        # clean_json_filename = f"{filename}.clean.json"
                        # clean_json_content = json.dumps(cleaned_data, indent=2)
                        # zip_file.writestr(clean_json_filename, clean_json_content)


        # Prepare for download
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"Course_Materials_{sanitize_filename(analysis_data['course_topic'])}.zip"
        )
        
    except Exception as e:
        logger.error(f"Error creating materials ZIP: {str(e)}")
        flash('Error creating download file.')
        return redirect(url_for('main.view_materials', analysis_id=analysis_id))


def parse_assessment_to_json(assessmentRaw_text):
    # Define section assessmentHeadings for the assessment
    assessmentHeadings = [
        "Comprehensive Assessment Suite", "Knowledge Check Questions",
        "Multiple Choice Questions", "True/False Questions",
        "Short Answer Questions", "Application Questions",
        "Scenario-Based Questions", "Analysis and Synthesis Questions",
        "Practical Assessment Project",
        "Self-Assessment Tools","Answer Keys and Explanations","Practice Questions for"
    ]

    def asmt_clean_line(line):
        cleaned = re.sub(r'^#+\s*', '', line)
        cleaned = re.sub(r'^[-*+]\s+', '', cleaned)
        cleaned = re.sub(r'^\d+\.\s+', '', cleaned)
        cleaned = re.sub(r'\*\*|__|\*|_', '', cleaned)
        cleaned = re.sub(r'`+', '', cleaned)
        cleaned = re.sub(r':\s*$', '', cleaned)
        cleaned = re.sub(r'\t', ' ', cleaned)
        return cleaned.strip()
    
    asmt_raw_lines = [line.strip() for line in assessmentRaw_text.split('\n') if line.strip()]
    asmt_cleaned_lines = [asmt_clean_line(line) for line in asmt_raw_lines]

    asmt_parsed_data = {}
    asmt_current_heading = None
    asmt_lowercase_headings = [h.lower() for h in assessmentHeadings]

    # for line in asmt_cleaned_lines:
    #     if line.lower() in asmt_lowercase_headings:
    #         asmt_matching_heading = next(h for h in assessmentHeadings
    #                                 if h.lower() == line.lower())
    #         asmt_current_heading = asmt_matching_heading
    #         if asmt_current_heading not in asmt_parsed_data:
    #             asmt_parsed_data[asmt_current_heading] = []
    #     elif asmt_current_heading:
    #         asmt_parsed_data[asmt_current_heading].append(line)

    # for line in asmt_cleaned_lines:
    #     if any(line.lower().startswith(h.lower()) for h in assessmentHeadings if h == "Practice Questions for") or line.lower() in asmt_lowercase_headings:
    #         matching_heading = next(h for h in assessmentHeadings if line.lower().startswith(h.lower())) if "Practice Questions for" in assessmentHeadings and line.lower().startswith("practice questions for") else next(h for h in assessmentHeadings if h.lower() == line.lower())
    #         asmt_current_heading = matching_heading
    #         if asmt_current_heading not in asmt_parsed_data:
    #             asmt_parsed_data[asmt_current_heading] = []
    #     elif asmt_current_heading:
    #         asmt_parsed_data[asmt_current_heading].append(line)
    for line in asmt_cleaned_lines:
        # Check if the line starts with or contains a heading (ignoring parenthetical content)
        matching_heading = None
        for h in assessmentHeadings:
            h_lower = h.lower()
            # Remove parenthetical content for comparison
            asmt_cleaned_lines = re.sub(r'\s*\([^)]*\)', '', line.lower()).strip()
            if asmt_cleaned_lines == h_lower or (h == "Practice Questions for" and line.lower().startswith(h_lower)):
                matching_heading = h
                break
        if matching_heading:
            asmt_current_heading = matching_heading
            if asmt_current_heading not in asmt_parsed_data:
                asmt_parsed_data[asmt_current_heading] = []
        elif asmt_current_heading:
            asmt_parsed_data[asmt_current_heading].append(line)
           

    asmt_standard_json = {
        "comprehensive_assessments": {
            "knowledge_check_questions": {
                "multiple_choice_questions": [],
                "true_false_questions": [],
                "short_answer_questions": []
            },
            "application_questions": {
                "scenario_based_questions": []
            },
            "analysis_and_synthesis_questions": [],
            "practical_assessment_project": {
                "project_description": "",
                "project_requirements": [],
                "deliverables": [],
                "grading_rubric": {}
            },
            "self_assessment_tools": {
                "knowledge_self_check": [],
                "skills_self_assessment": []
            },
            #"answer_keys_and_explanations": [],
            "practice_questions": []
        },
        "assessment_overview": {
            "total_questions": "",
            "question_types": [],
            "assessment_features": [],
            "estimated_assessment_time": ""
        }
    }

    def process_multiple_choice(lines):
        questions = []
        current_question = {}
        current_options = []
        expect_question_text = False
        for line in lines:
            line = asmt_clean_line(line)
            if line.startswith("Question"):
                if current_question:
                    current_question["options"] = current_options
                    questions.append(current_question)
                    current_options = []
                    current_question = {}
                expect_question_text = True
                current_question = {
                    "question_number": len(questions) + 1,
                    "question": "",
                    "options": [],
                    "correct_answer": "",
                    "content_reference": "",
                    "learning_objective_tested": ""
                }
            elif expect_question_text and line and not line.startswith(("a)", "b)", "c)", "d)", "Correct Answer:", "Content Reference:", "Learning Objective Tested:")):
                current_question["question"] = line.strip()
                expect_question_text = False
            elif line.startswith(("a)", "b)", "c)", "d)")):
                current_options.append(line)
            elif line.startswith("Correct Answer:"):
                current_question["correct_answer"] = line.split(":", 1)[1].strip()
            elif line.startswith("Content Reference:"):
                current_question["content_reference"] = line.split(":", 1)[1].strip()
            elif line.startswith("Learning Objective Tested:"):
                current_question["learning_objective_tested"] = line.split(":", 1)[1].strip()
        if current_question:
            current_question["options"] = current_options
            questions.append(current_question)
        return questions

    def process_true_false(lines):
        questions = []
        current_question = {}
        for line in lines:
            line = asmt_clean_line(line)
            if line.startswith("Question"):
                if current_question:
                    questions.append(current_question)
                    current_question = {}
                expect_question_text = True
                current_question = {
                    "question_number": len(questions) + 1,
                    "question": "",
                    "correct_answer": False,
                    "content_reference": "",
                    "learning_objective_tested": ""
                }
            elif expect_question_text and line and not line.startswith(("Correct Answer:","Content Reference:", "Learning Objective Tested:")):
                if line.startswith("True or") or line.startswith("true or"):
                    currentquestion = line.split(":", 1)[1].strip()
                    current_question["question"] = currentquestion
                    expect_question_text = False
            elif line.startswith("Correct Answer:"):
                answer = line.split(":", 1)[1].strip()
                current_question["correct_answer"] = answer.lower().startswith(
                    "true")
            elif line.startswith("Content Reference:"):
                current_question["content_reference"] = line.split(
                    ":", 1)[1].strip()
            elif line.startswith("Learning Objective Tested:"):
                current_question["learning_objective_tested"] = line.split(
                    ":", 1)[1].strip()
        if current_question:
            questions.append(current_question)
        return questions

    def process_short_answer(lines):
        questions = []
        current_question = {}
        key_points = []
        for line in lines:
            line = asmt_clean_line(line)
            if line.startswith("Question"):
                if current_question:
                    current_question["key_points_required"] = key_points
                    questions.append(current_question)
                    key_points = []
                    current_question = {}
                expect_question_text = True
                current_question = {
                    "question_number": len(questions) + 1,
                    "question": "",
                    "sample_correct_answer": "",
                    "key_points_required": [],
                    "content_reference": "",
                    "learning_objective_tested": ""
                }

            elif expect_question_text and line and not line.startswith(("Sample Correct Answer:", "Key Points Required:","Content Reference:","Learning Objective Tested:")):
                current_question["question"] = line.strip()
                expect_question_text = False    
            elif line.startswith("Sample Correct Answer:"):
                current_question["sample_correct_answer"] = line.split(
                    ":", 1)[1].strip()
            elif line.startswith("Key Points Required:"):
                key_points = line.split(":", 1)[1].strip().split(", ")
            elif line.startswith("Content Reference:"):
                current_question["content_reference"] = line.split(
                    ":", 1)[1].strip()
            elif line.startswith("Learning Objective Tested:"):
                current_question["learning_objective_tested"] = line.split(
                    ":", 1)[1].strip()
        if current_question:
            current_question["key_points_required"] = key_points
            questions.append(current_question)
        return questions

    def process_scenario_based(lines):
        questions = []
        current_question = {}
        rubric = {}
        for line in lines:
            line = asmt_clean_line(line)
            if line.startswith("Question"):
                if current_question:
                    current_question["assessment_rubric"] = rubric
                    questions.append(current_question)
                    rubric = {}
                    current_question = {}
                expect_question_text = True
                current_question = {
                    "question_number": len(questions) + 1,
                    "question": "",
                    "sample_correct_answer": "",
                    "assessment_rubric": {},
                    "content_connection": ""
                }
            elif expect_question_text and line and not line.startswith(("Question","Sample Correct Answer",
                                 "Assessment Rubric",
                                 "Excellent", "Good", "Satisfactory", "Needs Improvement","Content Connection")):
                current_question["question"] = line.strip()
                expect_question_text = False 

            elif line.startswith("Sample Correct Answer:"):
                current_question["sample_correct_answer"] = line.split(
                    ":", 1)[1].strip()
            elif line.startswith("Assessment Rubric:"):
                continue
            elif line.startswith(
                ("Excellent", "Good", "Satisfactory", "Needs Improvement")):
                score = 4 if line.startswith(
                    "Excellent") else 3 if line.startswith(
                        "Good") else 2 if line.startswith(
                            "Satisfactory") else 1
                description = line.split("(", 1)[0].strip()
                rubric[description.lower()] = {
                    "score": score,
                    "description": line.split(":", 1)[1].strip()
                }
            elif line.startswith("Content Connection:"):
                current_question["content_connection"] = line.split(
                    ":", 1)[1].strip()
        if current_question:
            current_question["assessment_rubric"] = rubric
            questions.append(current_question)
        return questions

    def process_analysis_synthesis(lines):
        questions = []
        current_question = {}
        grading_criteria = []
        for line in lines:
            line = asmt_clean_line(line)
            if line.startswith("Question"):
                if current_question:
                    current_question["grading_criteria"] = grading_criteria
                    questions.append(current_question)
                    grading_criteria = []
                    current_question = {}
                expect_question_text = True
                current_question = {
                    "question_number": len(questions) + 1,
                    "question": "",
                    "sample_answer": "",
                    "grading_criteria": [],
                    "content_references": ""
                }

            elif expect_question_text and line and not line.startswith(("Question","Sample Answer",
                                 "Grading Criteria",
                                 "Content References")):
                current_question["question"] = line.strip()
                expect_question_text = False 

            elif line.startswith("Sample Answer:"):
                current_question["sample_answer"] = line.split(":",
                                                               1)[1].strip()
            elif line.startswith("Grading Criteria:"):
                grading_criteria = line.split(":", 1)[1].strip().split(", ")
            elif line.startswith("Content References:"):
                current_question["content_references"] = line.split(
                    ":", 1)[1].strip()
        if current_question:
            current_question["grading_criteria"] = grading_criteria
            questions.append(current_question)
        return questions

    def process_practical_project(lines):
        project = {
            "project_description": "",
            "project_requirements": [],
            "deliverables": [],
            "grading_rubric": {}
        }
        current_section = None
        requirements = []
        deliverables = []
        rubric = {}
        subheadings = ["Project Description", "Project Requirements", "Deliverables", "Grading Rubric"]
        lowercase_subheadings = [h.lower() for h in subheadings]

        for line in lines:
            line = asmt_clean_line(line)
            if line.lower() in lowercase_subheadings:
                current_section = next(h for h in subheadings if h.lower() == line.lower()).lower().replace(" ", "_")
            elif current_section and line:
                if current_section == "project_description":
                    project["project_description"] = line
                elif current_section == "project_requirements":
                    requirements.append(line)
                elif current_section == "deliverables":
                    deliverables.append(line)
                elif current_section == "grading_rubric":
                    try:
                        key = line.split("(", 1)[0].strip().lower().replace(" ", "_")
                        weight = int(line.split("(", 1)[1].split("%")[0])
                        description = line.split(":", 1)[1].strip()
                        rubric[key] = {"weight": weight, "description": description}
                    except (IndexError, ValueError) as e:
                        print(f"Error processing grading rubric line '{line}': {str(e)}")

        project["project_requirements"] = requirements
        project["deliverables"] = deliverables
        project["grading_rubric"] = rubric
        return project

    def process_self_assessment(lines):
        self_assessment = {
            "knowledge_self_check": [],
            "skills_self_assessment": []
        }
        current_section = None
        subheadings = ["Knowledge Self-Check", "Skills Self-Assessment"]
        lowercase_subheadings = [h.lower() for h in subheadings]

        for line in lines:
            line = asmt_clean_line(line)
            if line.lower() in lowercase_subheadings:
                current_section = next(h for h in subheadings if h.lower() == line.lower()).lower().replace(" ", "_")
            elif current_section and line:
                if current_section == "knowledge_self-check":
                 scale = "1-5" if "(1-5)" in line else ""
                 question_text = line.split("(1-5)")[0].strip() if "(1-5)" in line else line
                 self_assessment["knowledge_self_check"].append({"question": question_text, "scale": scale})
                elif current_section == "skills_self-assessment":
                 options = ["Yes", "No", "Partially"] if "Yes/No/Partially" in line else []
                 question_text = line.split("(Yes/No/Partially)")[0].strip() if "(Yes/No/Partially)" in line else line
                 self_assessment["skills_self_assessment"].append({"question": question_text, "options": options})

        return self_assessment

    # def process_answer_keys(lines):
    #     answer_keys = []
    #     current_question = {}
    #     common_wrong_answers = []
    #     for line in lines:
    #         line = asmt_clean_line(line)
    #         if line.startswith("Question"):
    #             if current_question:
    #                 current_question[
    #                     "common_wrong_answers"] = common_wrong_answers
    #                 answer_keys.append(current_question)
    #                 common_wrong_answers = []
    #                 current_question = {}
    #             question_text = line.split(
    #                 ":", 1)[1].strip() if ":" in line else line.replace(
    #                     "Question", "").strip()
    #             current_question = {
    #                 "question": question_text,
    #                 "correct_answer": "",
    #                 "explanation": "",
    #                 "common_wrong_answers": [],
    #                 "content_reference": "",
    #                 "tips": ""
    #             }
    #         elif line.startswith("Correct Answer:"):
    #             current_question["correct_answer"] = line.split(":",
    #                                                             1)[1].strip()
    #         elif line.startswith("Explanation:"):
    #             current_question["explanation"] = line.split(":", 1)[1].strip()
    #         elif line.startswith("Content Reference:"):
    #             current_question["content_reference"] = line.split(
    #                 ":", 1)[1].strip()
    #         elif line.startswith("Common Wrong Answers:"):
    #             common_wrong_answers = [
    #                 ans.strip() for ans in line.split(":", 1)[1].split(", ")
    #             ] if ":" in line else []
    #         elif line.startswith("Tips:"):
    #             current_question["tips"] = line.split(":", 1)[1].strip()
    #     if current_question:
    #         current_question["common_wrong_answers"] = common_wrong_answers
    #         answer_keys.append(current_question)
    #     return answer_keys
    
    def process_practice_questions(lines):
        questions = []
        current_question = {}
        current_options = []
        expect_question_text = False
        for line in lines:
            line = asmt_clean_line(line)
            if line.startswith("Practice Question"):
                if current_question:
                    current_question["options"] = current_options
                    questions.append(current_question)
                    current_options = []
                    current_question = {}
                expect_question_text = True
                current_question = {
                    "question_number": len(questions) + 1,
                    "question": "",
                    "options": [],
                    "answer": "",
                    "content_reference": "",
                    "study_tip": ""
                }
            elif expect_question_text and line and not line.startswith(("A)", "B)", "C)", "D)", "Answer:", "Content Reference:", "Study Tip:")):
                current_question["question"] = line.strip()
                expect_question_text = False
            elif line.startswith(("A)", "B)", "C)", "D)")):
                current_options.append(line[2:].strip())
            elif line.startswith("Answer:"):
                current_question["answer"] = line.split(":", 1)[1].strip()
            elif line.startswith("Content Reference:"):
                current_question["content_reference"] = line.split(":", 1)[1].strip()
            elif line.startswith("Study Tip:"):
                current_question["study_tip"] = line.split(":", 1)[1].strip()
        if current_question:
            current_question["options"] = current_options
            questions.append(current_question)
        return questions

    for key, value in asmt_parsed_data.items():
        if key == "Multiple Choice Questions":
         asmt_standard_json["comprehensive_assessments"][
             "knowledge_check_questions"][
                 "multiple_choice_questions"] = process_multiple_choice(value)

        elif key == "True/False Questions":
            asmt_standard_json["comprehensive_assessments"][
                "knowledge_check_questions"][
                    "true_false_questions"] = process_true_false(value)
        elif key == "Short Answer Questions":
            asmt_standard_json["comprehensive_assessments"][
                "knowledge_check_questions"][
                    "short_answer_questions"] = process_short_answer(value)
        elif key == "Scenario-Based Questions":
            asmt_standard_json["comprehensive_assessments"][
                "application_questions"][
                    "scenario_based_questions"] = process_scenario_based(value)
        elif key == "Analysis and Synthesis Questions":
            asmt_standard_json["comprehensive_assessments"][
                "analysis_and_synthesis_questions"] = process_analysis_synthesis(
                    value)
        elif key == "Practical Assessment Project":
            asmt_standard_json["comprehensive_assessments"][
                "practical_assessment_project"] = process_practical_project(
                    value)
        elif key == "Self-Assessment Tools":
            asmt_standard_json["comprehensive_assessments"][
                "self_assessment_tools"] = process_self_assessment(value)
            
        elif key.startswith("Practice Questions for"):
            asmt_standard_json["comprehensive_assessments"]["practice_questions"] = process_practice_questions(value)
        
        # elif key == "Answer Keys and Explanations":
        #     asmt_standard_json["comprehensive_assessments"][
        #         "answer_keys_and_explanations"] = process_answer_keys(value)

    return asmt_standard_json



def create_combined_navigation(course_materials):
    navigation_data = []

    for module in course_materials["modules"]:
        module_number = module["number"]
        module_title = module["title"]
        module_folder = f"Module_{module_number}_{sanitize_filename(module_title)}"

        navigation_data.append({
            "module": module_title,
            "path": module_folder,
            "hasAssessment": True
        })

    return navigation_data

def remove_trailing_commas(json_str):
    # Remove trailing commas inside objects and arrays
    # 1. Trailing commas in objects: { "a": 1, }
    json_str = re.sub(r',(\s*})', r'\1', json_str)
    # 2. Trailing commas in arrays: [1, 2, ]
    json_str = re.sub(r',(\s*])', r'\1', json_str)
    return json_str

def parse_markdown_to_scorm_object(md: str):
    import re

    def extract_section(name, content):
        # Match a bold label and extract until the next bold label
        pattern = rf"\*\*{re.escape(name)}\*\*[:]?\s*\n?(.*?)(?=\n\s*\*\*[^*\n]+\*\*|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else ""

    def extract_core_concepts(section):
        def get_text(label):
            return extract_section(label, section)

        def get_list(label):
            pattern = rf"\*\*{re.escape(label)}\*\*[:]?\s*\n((?:\s*[-+*]\s+.*\n?)+)"
            match = re.search(pattern, section)
            return [item.strip() for item in re.findall(r"[-+*] (.+)", match.group(1))] if match else []

        return {
            "definition": get_text("Definition"),
            "theoreticalFoundation": get_text("Theoretical Foundation"),
            "keyComponents": get_list("Key Components")
        }

    def extract_best_practices(section):
        pattern = r"\*\*Best Practices\*\*\n((?:\s*[-+*]\s+.*\n?)+)"
        match = re.search(pattern, section)
        return re.findall(r"[-+*] (.*)", match.group(1)) if match else []

    def clean_title(header):
        return re.sub(r'[#:*\n]', '', header).strip()

    # Step 1: Locate the Detailed Topic Coverage section
    topic_coverage_match = re.search(r"### Detailed Topic Coverage\n+(.*?)(?=\n### |\n## |\Z)", md, re.DOTALL)
    if not topic_coverage_match:
        return {"chapter": {"topics": []}}

    topic_content = topic_coverage_match.group(1).strip()

    # Step 2: Split by all #### Subtopics inside Detailed Topic Coverage
    topic_sections = re.split(r"\n(?=#### )", topic_content)

    topics = []
    for section in topic_sections:
        title_match = re.match(r"#### (.+)", section)
        if not title_match:
            continue

        title = clean_title(title_match.group(1))
        overview = extract_section("Comprehensive Overview", section) or extract_section("Overview", section)
        core_concepts = extract_core_concepts(section)
        practical_applications = extract_section("Practical Applications", section)
        best_practices = extract_best_practices(section)

        topics.append({
            "title": title,
            "overview": overview,
            "coreConcepts": core_concepts,
            "practicalApplications": practical_applications,
            "bestPractices": best_practices
        })

    return {
        "chapter": {
            "topics": topics
        }
    }


# def parse_markdown_to_scorm_object(md: str):
#     import re

#     def extract_section(heading, content):
#         pattern = rf"###* {re.escape(heading)}\n+(.*?)(?=\n### |\n## |\Z)"
#         match = re.search(pattern, content, re.DOTALL)
#         return match.group(1).strip() if match else ""

#     def extract_core_concepts(section):
#         def get_text(label):
#             pattern = rf"\*\*{label}\*\*: (.*)"
#             match = re.search(pattern, section)
#             return match.group(1).strip() if match else ""

#         def get_list(label):
#             pattern = rf"\*\*{label}\*\*:\n((?:\s*-\s+.*\n?)+)"
#             match = re.search(pattern, section)
#             if not match:
#                 return []
#             items = re.findall(r"- (.+)", match.group(1))
#             return [item.strip() for item in items]

#         return {
#             "definition": get_text("Definition"),
#             "theoreticalFoundation": get_text("Theoretical Foundation"),
#             "keyComponents": get_list("Key Components")
#         }

#     def extract_best_practices(section):
#         pattern = r"\*\*Best Practices\*\*\n((?:\s*\d+\.\s+.*\n?)+)"
#         match = re.search(pattern, section)
#         return re.findall(r"\d+\.\s+(.*)", match.group(1)) if match else []

#     def extract_title(section):
#         match = re.search(r"#### (.*)", section)
#         return match.group(1).strip() if match else "Untitled"

#     topic_sections = re.split(r"\n(?=#### )", md)
#     topics = []

#     for section in topic_sections[1:]:  # skip the chapter-level intro
#         title = extract_title(section)
#         overview = extract_section("Comprehensive Overview", section)
#         core_concepts = extract_core_concepts(section)
#         practical_applications = extract_section("Practical Applications", section)
#         best_practices = extract_best_practices(section)

#         topics.append({
#             "title": title,
#             "overview": overview,
#             "coreConcepts": core_concepts,
#             "practicalApplications": practical_applications,
#             "bestPractices": best_practices
#         })

#     return {
#         "chapter": {
#             "topics": topics
#         }
#     }


# ADD these helper functions at the bottom of your routes.py file:
def calculate_materials_stats(materials):
    """Calculate statistics for materials dashboard."""
    modules = materials.get('modules', [])
    stats = {
        'total_modules': len(modules),
        'total_components': 0,
        'completion_rate': 0,
        'total_pages': 0
    }
    
    if not modules:
        return stats
    
    total_possible = len(modules) * 5  # 5 components per module
    completed = 0
    
    for module in modules:
        for component_type, component_data in module.get('components', {}).items():
            if component_data:
                stats['total_components'] += 1
                completed += 1
                
                # Estimate pages (rough calculation)
                if isinstance(component_data, dict):
                    content_str = json.dumps(component_data)
                    words = len(content_str.split())
                    stats['total_pages'] += max(1, words // 300)  # ~300 words per page
    
    stats['completion_rate'] = int((completed / total_possible) * 100) if total_possible > 0 else 0
    
    return stats

def sanitize_filename(filename):
    """Sanitize filename for safe file system usage."""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    
    # Limit length
    filename = filename[:50]
    
    return filename.strip()

def create_materials_overview(analysis_data):
    """Create a text overview of all materials."""
    overview = f"""COURSE MATERIALS OVERVIEW
========================

Course: {analysis_data['course_topic']}
Audience Level: {analysis_data['audience_type'].title()}
Generated: {analysis_data.get('materials_generated_date', 'Unknown')}
Total Modules: {len(analysis_data['course_materials']['modules'])}

MODULE SUMMARY
==============

"""
    
    for module in analysis_data['course_materials']['modules']:
        overview += f"\nModule {module['number']}: {module['title']}\n"
        overview += "-" * 50 + "\n"
        
        for component_type, component_data in module['components'].items():
            if component_data:
                overview += f"? {component_type.replace('_', ' ').title()}\n"
            else:
                overview += f"? {component_type.replace('_', ' ').title()} (not generated)\n"
    
    return overview

def format_material_as_text(material_type, material_data):
    """Format material data as readable text."""
    # This is a simplified version - you can expand this based on material structure
    text = f"{material_type.replace('_', ' ').upper()}\n"
    text += "=" * 50 + "\n\n"
    
    # Remove metadata for cleaner text
    if isinstance(material_data, dict):
        data = {k: v for k, v in material_data.items() if k != 'metadata'}
    else:
        data = material_data
    
    # Convert to formatted text
    text += json.dumps(data, indent=2)
    
    return text

def parse_content_to_json_contenttype(md_text):
    rawtext = md_text

    headings = [
        "Chapter", "Learning Outcomes", "Chapter Overview", "Introduction",
        "Detailed Topic Coverage", "Synthesis and Integration",
        "Practical Implementation Guide", "Tools and Resources", "Essential Tools",
        "Additional Resources", "Recommended Readings", "Online tutorials",
        "Practice platforms", "Professional communities", "Chapter Summary",
        "Key Terms Glossary"
    ]

    topic_headings = [
        "Comprehensive Overview", "Core Concepts", "Definition", "Theoretical Foundation",
        "Key Components", "How It Works", "Detailed Examples", "Practical Applications",
        "Common Challenges and Solutions", "Best Practices", "Integration with Other Concepts"
    ]

    def clean_line(line):
        cleaned = re.sub(r'^#+\s*', '', line)
        cleaned = re.sub(r'^[-*+]\s+', '', cleaned)
        cleaned = re.sub(r'^\d+\.\s+', '', cleaned)
        cleaned = re.sub(r'\*\*|__|\*|_', '', cleaned)
        cleaned = re.sub(r'`+', '', cleaned)
        cleaned = re.sub(r':\s*$', '', cleaned)
        cleaned = re.sub(r'\t', ' ', cleaned)
        cleaned = re.sub(r'JAVAHOME', 'JAVA_HOME', cleaned)
        return cleaned.strip()

    def process_examples_lines(example_key, lines, current_topic):
        detailed_examples = []
        current_level = None
        current_steps = []
        for line in lines:
            line = line.strip()
            if line.startswith("Example"):
                if current_level:
                    detailed_examples.append({
                        "level": current_level,
                        "steps": [step for step in current_steps if step]
                    })
                    current_steps = []
                current_level = line.split(":", 1)[1].strip() if ":" in line else line.strip()
            elif current_level and line:
                current_steps.append(line)
        if current_level:
            detailed_examples.append({
                "level": current_level,
                "steps": [step for step in current_steps if step]
            })
        current_topic["Detailed Examples"] = detailed_examples
        return current_topic

    def process_challenge_lines(challenge_key, lines, current_topic):
        challenges_solutions = []
        current_challenge = None
        current_steps = []
        is_pattern_2 = False
        for i, line in enumerate(lines):
            line = line.strip()
            if "Challenge" in line:
                if current_challenge:
                    if is_pattern_2:
                        if current_steps and "Solution" in current_steps[0]:
                            solution = current_steps[0].split(":", 1)[1].strip() if ":" in current_steps[0] else current_steps[0].strip()
                            challenges_solutions.append({
                                "challenge": current_challenge,
                                "solution": solution
                            })
                    else:
                        challenges_solutions.append({
                            "challenge": current_challenge,
                            "solution": [step for step in current_steps if step]
                        })
                    current_steps = []
                challenge_part = line.split(":", 1)[1].strip() if ":" in line else line.strip()
                current_challenge = challenge_part.rstrip("-").strip()
                if i + 1 < len(lines) and "Solution" in lines[i + 1].strip():
                    is_pattern_2 = True
                else:
                    is_pattern_2 = False
            elif current_challenge and line:
                current_steps.append(line)
        if current_challenge:
            if is_pattern_2:
                if current_steps and "Solution" in current_steps[0]:
                    solution = current_steps[0].split(":", 1)[1].strip() if ":" in current_steps[0] else current_steps[0].strip()
                    challenges_solutions.append({
                        "challenge": current_challenge,
                        "solution": solution
                    })
            else:
                challenges_solutions.append({
                    "challenge": current_challenge,
                    "solution": [step for step in current_steps if step]
                })
        current_topic["Common Challenges and Solutions"] = challenges_solutions
        return current_topic

    def restructure_challenges(current_topic):
        challenges_solutions = current_topic["Common Challenges and Solutions"]
        restructured = []
        for challenge in challenges_solutions:
            if any("Description:" in item for item in challenge["solution"]):
                description = ""
                solution = ""
                for item in challenge["solution"]:
                    if "Description:" in item:
                        description = item.split(":", 1)[1].strip()
                    elif "Solution:" in item:
                        solution = item.split(":", 1)[1].strip()
                restructured.append({
                    "challenge": description or challenge["challenge"],
                    "solution": solution
                })
            else:
                restructured.append({
                    "challenge": challenge["challenge"],
                    "solution": challenge["solution"]
                })
        current_topic["Common Challenges and Solutions"] = restructured
        return current_topic

    def process_topic_coverage(topic_key, lines, standard_json):
        topics = []
        current_topic = {
            "Topic Title": "",
            "Comprehensive Overview": "",
            "Core Concepts": {
                "Definition": "",
                "Theoretical Foundation": "",
                "Key Components": [],
                "How It Works": []
            },
            "Detailed Examples": [],
            "Practical Applications": "",
            "Common Challenges and Solutions": [],
            "Best Practices": [],
            "Integration with Other Concepts": ""
        }
        current_subsection = None
        current_lines = []
        topic_title = None
        lowercase_topic_headings = [h.lower() for h in topic_headings]
        for line in lines:
            line = line.strip()
            if re.match(r'^[A-Z]\.\s*+.+$', line):
                if topic_title:
                    if current_subsection:
                        if current_subsection == "Comprehensive Overview":
                            joined = '\n'.join([l for l in current_lines if l])
                            current_topic["Comprehensive Overview"] = joined.split('\n') if '\n' in joined else joined
                        elif current_subsection == "Definition":
                            joined = '\n'.join([l for l in current_lines if l])
                            current_topic["Core Concepts"]["Definition"] = joined.split('\n') if '\n' in joined else joined
                        elif current_subsection == "Theoretical Foundation":
                            joined = '\n'.join([l for l in current_lines if l])
                            current_topic["Core Concepts"]["Theoretical Foundation"] = joined.split('\n') if '\n' in joined else joined
                        elif current_subsection == "Key Components":
                            current_topic["Core Concepts"]["Key Components"] = [l for l in current_lines if l]
                        elif current_subsection == "How It Works":
                            current_topic["Core Concepts"]["How It Works"] = [l for l in current_lines if l]
                        elif current_subsection == "Detailed Examples":
                            current_topic = process_examples_lines(current_subsection, current_lines, current_topic)
                        elif current_subsection == "Practical Applications":
                            joined = '\n'.join([l for l in current_lines if l])
                            current_topic["Practical Applications"] = joined.split('\n') if '\n' in joined else joined
                        elif current_subsection == "Common Challenges and Solutions":
                            current_topic = process_challenge_lines(current_subsection, current_lines, current_topic)
                            current_topic = restructure_challenges(current_topic)
                        elif current_subsection == "Best Practices":
                            current_topic["Best Practices"] = [l for l in current_lines if l]
                        elif current_subsection == "Integration with Other Concepts":
                            joined = '\n'.join([l for l in current_lines if l])
                            current_topic["Integration with Other Concepts"] = joined.split('\n') if '\n' in joined else joined
                    current_topic["Topic Title"] = topic_title
                    topics.append(current_topic)
                    current_topic = {
                        "Topic Title": "",
                        "Comprehensive Overview": "",
                        "Core Concepts": {
                            "Definition": "",
                            "Theoretical Foundation": "",
                            "Key Components": [],
                            "How It Works": []
                        },
                        "Detailed Examples": [],
                        "Practical Applications": "",
                        "Common Challenges and Solutions": [],
                        "Best Practices": [],
                        "Integration with Other Concepts": ""
                    }
                    current_subsection = None
                    current_lines = []
                topic_title = line
            elif line.lower() in lowercase_topic_headings:
                matching_heading = next(h for h in topic_headings if h.lower() == line.lower())
                if current_subsection:
                    if current_subsection == "Comprehensive Overview":
                        joined = '\n'.join([l for l in current_lines if l])
                        current_topic["Comprehensive Overview"] = joined.split('\n') if '\n' in joined else joined
                    elif current_subsection == "Definition":
                        joined = '\n'.join([l for l in current_lines if l])
                        current_topic["Core Concepts"]["Definition"] = joined.split('\n') if '\n' in joined else joined
                    elif current_subsection == "Theoretical Foundation":
                        joined = '\n'.join([l for l in current_lines if l])
                        current_topic["Core Concepts"]["Theoretical Foundation"] = joined.split('\n') if '\n' in joined else joined
                    elif current_subsection == "Key Components":
                        current_topic["Core Concepts"]["Key Components"] = [l for l in current_lines if l]
                    elif current_subsection == "How It Works":
                        current_topic["Core Concepts"]["How It Works"] = [l for l in current_lines if l]
                    elif current_subsection == "Detailed Examples":
                        current_topic = process_examples_lines(current_subsection, current_lines, current_topic)
                    elif current_subsection == "Practical Applications":
                        joined = '\n'.join([l for l in current_lines if l])
                        current_topic["Practical Applications"] = joined.split('\n') if '\n' in joined else joined
                    elif current_subsection == "Common Challenges and Solutions":
                        current_topic = process_challenge_lines(current_subsection, current_lines, current_topic)
                        current_topic = restructure_challenges(current_topic)
                    elif current_subsection == "Best Practices":
                        current_topic["Best Practices"] = [l for l in current_lines if l]
                    elif current_subsection == "Integration with Other Concepts":
                        joined = '\n'.join([l for l in current_lines if l])
                        current_topic["Integration with Other Concepts"] = joined.split('\n') if '\n' in joined else joined
                current_subsection = matching_heading
                current_lines = []
            elif current_subsection and line:
                current_lines.append(line)
        if topic_title:
            if current_subsection:
                if current_subsection == "Comprehensive Overview":
                    joined = '\n'.join([l for l in current_lines if l])
                    current_topic["Comprehensive Overview"] = joined.split('\n') if '\n' in joined else joined
                elif current_subsection == "Definition":
                    joined = '\n'.join([l for l in current_lines if l])
                    current_topic["Core Concepts"]["Definition"] = joined.split('\n') if '\n' in joined else joined
                elif current_subsection == "Theoretical Foundation":
                    joined = '\n'.join([l for l in current_lines if l])
                    current_topic["Core Concepts"]["Theoretical Foundation"] = joined.split('\n') if '\n' in joined else joined
                elif current_subsection == "Key Components":
                    current_topic["Core Concepts"]["Key Components"] = [l for l in current_lines if l]
                elif current_subsection == "How It Works":
                    current_topic["Core Concepts"]["How It Works"] = [l for l in current_lines if l]
                elif current_subsection == "Detailed Examples":
                    current_topic = process_examples_lines(current_subsection, current_lines, current_topic)
                elif current_subsection == "Practical Applications":
                    joined = '\n'.join([l for l in current_lines if l])
                    current_topic["Practical Applications"] = joined.split('\n') if '\n' in joined else joined
                elif current_subsection == "Common Challenges and Solutions":
                    current_topic = process_challenge_lines(current_subsection, current_lines, current_topic)
                    current_topic = restructure_challenges(current_topic)
                elif current_subsection == "Best Practices":
                    current_topic["Best Practices"] = [l for l in current_lines if l]
                elif current_subsection == "Integration with Other Concepts":
                    joined = '\n'.join([l for l in current_lines if l])
                    current_topic["Integration with Other Concepts"] = joined.split('\n') if '\n' in joined else joined
            current_topic["Topic Title"] = topic_title
            topics.append(current_topic)
        standard_json["chapter"]["Detailed Topic Coverage"] = topics
        return standard_json

    def process_glossary_lines(lines):
        glossary = []
        for line in lines:
            line = clean_line(line)
            if ":" in line:
                term, definition = line.split(":", 1)
                glossary.append({
                    "term": term.strip(),
                    "definition": definition.strip()
                })
        return glossary

    raw_lines = [line.strip() for line in rawtext.split('\n') if line.strip()]
    cleaned_lines = [clean_line(line) for line in raw_lines]

    parsed_data = {}
    current_heading = None
    lowercase_headings = [h.lower() for h in headings]

    for line in cleaned_lines:
        cleaned = clean_line(line)
        if cleaned.lower() in lowercase_headings:
            matching_heading = next(h for h in headings if h.lower() == cleaned.lower())
            current_heading = matching_heading
            if current_heading not in parsed_data:
                parsed_data[current_heading] = []
        elif current_heading:
            parsed_data[current_heading].append(cleaned)

    standard_json = {
        "chapter": {
            "Chapter": "{}",
            "Learning Outcomes": "",
            "Chapter Overview": "",
            "Introduction": "",
            "Detailed Topic Coverage": [],
            "Synthesis and Integration": "",
            "Practical Implementation Guide": "",
            "Tools and Resources": {
                "Essential Tools": "",
                "Additional Resources": {
                    "Recommended Readings": "",
                    "Online tutorials": "",
                    "Practice platforms": "",
                    "Professional communities": ""
                }
            },
            "Chapter Summary": "",
            "Key Terms Glossary": []
        }
    }

    if cleaned_lines:
        standard_json["chapter"]['Chapter'] = cleaned_lines[0].split(':', 1)[1].strip() if ':' in cleaned_lines[0] else cleaned_lines[0]

    for key, value in parsed_data.items():
        joined_value = '\n'.join(value)
        final_value = joined_value.split('\n') if '\n' in joined_value else joined_value
        matching_key = next(h for h in headings if h.lower() == key.lower())
        if matching_key == "Learning Outcomes":
            standard_json["chapter"][matching_key] = final_value
        elif matching_key == "Practical Implementation Guide":
            standard_json["chapter"][matching_key] = final_value
        elif matching_key == "Chapter":
            standard_json["chapter"][matching_key] = final_value
        elif matching_key == "Essential Tools":
            standard_json["chapter"]["Tools and Resources"][matching_key] = final_value
        elif matching_key in ["Recommended Readings", "Online tutorials", "Practice platforms", "Professional communities"]:
            standard_json["chapter"]["Tools and Resources"]["Additional Resources"][matching_key] = final_value
        elif matching_key == "Detailed Topic Coverage":
            standard_json = process_topic_coverage(matching_key, value, standard_json)
        elif matching_key == "Key Terms Glossary":
            standard_json["chapter"][matching_key] = process_glossary_lines(value)
        elif matching_key in standard_json["chapter"] and not isinstance(standard_json["chapter"][matching_key], (dict, list)):
            standard_json["chapter"][matching_key] = final_value

    
    # return standard_json
    updated_json = update_standard_json(standard_json)
    return updated_json


def update_standard_json(standard_json):
    key_mapping = {
        "Chapter": "title",
        "Learning Outcomes": "learningOutcomes",
        "Chapter Overview": "overview",
        "Introduction": "introduction",
        "Detailed Topic Coverage": "topics",
        "Topic Title": "title",
        "Comprehensive Overview": "overview",
        "Core Concepts": "coreConcepts",
        "Definition": "definition",
        "Theoretical Foundation": "theoreticalFoundation",
        "Key Components": "keyComponents",
        "How It Works": "howitWorks",
        "Detailed Examples": "examples",
        "Practical Applications": "practicalApplications",
        "Common Challenges and Solutions": "challengesAndSolutions",
        "Best Practices": "bestPractices",
        "Synthesis and Integration": "synthesis",
        "Practical Implementation Guide": "implementationGuide",
        "Tools and Resources": "toolsAndResources",
        "Essential Tools": "essentialTools",
        "Additional Resources": "additionalResources",
        "Recommended Readings": "recommendedReadings",
        "Online tutorials": "onlineTutorials",
        "Practice platforms": "practicePlatforms",
        "Professional communities": "professionalCommunities",
        "Chapter Summary": "summary",
        "Key Terms Glossary": "glossary"
    }

    return rename_keys(standard_json, key_mapping)

def rename_keys(obj, key_mapping):
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            new_key = key_mapping.get(k, k)
            new_obj[new_key] = rename_keys(v, key_mapping)
        return new_obj
    elif isinstance(obj, list):
        return [rename_keys(item, key_mapping) for item in obj]
    else:
        return obj

@main.route('/download_module_materials/<analysis_id>/<int:module_id>')
def download_module_materials(analysis_id, module_id):
    """Download materials for a specific module."""
    # Load analysis data
    analysis_data = load_analysis(analysis_id)
    
    if not analysis_data or 'course_materials' not in analysis_data:
        flash('Materials not found.')
        return redirect(url_for('main.index'))
    
    # Find the module
    module = None
    for m in analysis_data['course_materials']['modules']:
        if m['number'] == module_id:
            module = m
            break
    
    if not module:
        flash('Module not found.')
        return redirect(url_for('main.view_materials', analysis_id=analysis_id))
    
    try:
        # Create a zip file with module materials
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add each component as a JSON file
            for component_type, component_data in module.get('components', {}).items():
                if component_data:
                    filename = f"Module_{module_id}_{component_type}.json"
                    zip_file.writestr(filename, json.dumps(component_data, indent=2))
            
            # Add a summary file
            summary = {
                'module_number': module['number'],
                'module_title': module['title'],
                'generated_components': list(module.get('components', {}).keys()),
                'course_topic': analysis_data['course_topic'],
                'generation_date': analysis_data.get('materials_generated_date', 'Unknown')
            }
            zip_file.writestr(f"Module_{module_id}_Summary.json", json.dumps(summary, indent=2))
        
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"Module_{module_id}_Materials.zip"
        )
        
    except Exception as e:
        logger.error(f"Error creating module materials ZIP: {str(e)}")
        flash('Error creating download file.')
        return redirect(url_for('main.view_materials', analysis_id=analysis_id))

@main.route('/export_materials/<analysis_id>/<format>')
def export_materials(analysis_id, format):
    """Export materials in different formats (PDF, DOCX)."""
    # For now, redirect to download all materials
    # You can implement specific format exports later
    flash(f'{format.upper()} export not yet implemented. Downloading as ZIP instead.')
    return redirect(url_for('main.download_all_materials', analysis_id=analysis_id))

# Helper functions for Phase 3

def calculate_materials_stats(materials):
    """Calculate statistics for materials dashboard."""
    modules = materials.get('modules', [])
    stats = {
        'total_modules': len(modules),
        'total_components': 0,
        'completion_rate': 0,
        'total_pages': 0
    }
    
    if not modules:
        return stats
    
    total_possible = len(modules) * 5  # 5 components per module
    completed = 0
    
    for module in modules:
        for component_type, component_data in module.get('components', {}).items():
            if component_data:
                stats['total_components'] += 1
                completed += 1
                
                # Estimate pages (rough calculation)
                if isinstance(component_data, dict):
                    content_str = json.dumps(component_data)
                    words = len(content_str.split())
                    stats['total_pages'] += max(1, words // 300)  # ~300 words per page
    
    stats['completion_rate'] = int((completed / total_possible) * 100) if total_possible > 0 else 0
    
    return stats

def sanitize_filename(filename):
    """Sanitize filename for safe file system usage."""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    
    # Limit length
    filename = filename[:50]
    
    return filename.strip()

def create_materials_overview(analysis_data):
    """Create a text overview of all materials."""
    overview = f"""COURSE MATERIALS OVERVIEW
========================

Course: {analysis_data['course_topic']}
Audience Level: {analysis_data['audience_type'].title()}
Generated: {analysis_data.get('materials_generated_date', 'Unknown')}
Total Modules: {len(analysis_data['course_materials']['modules'])}

MODULE SUMMARY
==============

"""
    
    for module in analysis_data['course_materials']['modules']:
        overview += f"\nModule {module['number']}: {module['title']}\n"
        overview += "-" * 50 + "\n"
        
        for component_type, component_data in module['components'].items():
            if component_data:
                overview += f"? {component_type.replace('_', ' ').title()}\n"
            else:
                overview += f"? {component_type.replace('_', ' ').title()} (not generated)\n"
    
    return overview

def format_material_as_text(material_type, material_data):
    """Format material data as readable text."""
    # This is a simplified version - you can expand this based on material structure
    text = f"{material_type.replace('_', ' ').upper()}\n"
    text += "=" * 50 + "\n\n"
    
    # Remove metadata for cleaner text
    if isinstance(material_data, dict):
        data = {k: v for k, v in material_data.items() if k != 'metadata'}
    else:
        data = material_data
    
    # Convert to formatted text
    text += json.dumps(data, indent=2)
    
    return text

def create_scorm_manifest(course_title, modules):
    print(course_title)
    import xml.etree.ElementTree as ET
    from xml.dom import minidom

    def sanitize_filename(name):
        return ''.join(c if c.isalnum() else '_' for c in name)

    manifest = ET.Element('manifest', {
        'identifier': 'AIDA_COURSE_MANIFEST',
        'version': '1.0',
        'xmlns': 'http://www.imsglobal.org/xsd/imscp_v1p1',
        'xmlns:adlcp': 'http://www.adlnet.org/xsd/adlcp_v1p3',
        'xmlns:adlseq': 'http://www.adlnet.org/xsd/adlseq_v1p3',
        'xmlns:adlnav': 'http://www.adlnet.org/xsd/adlnav_v1p3',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xsi:schemaLocation': 'http://www.imsglobal.org/xsd/imscp_v1p1 imscp_v1p1.xsd '
                              'http://www.adlnet.org/xsd/adlcp_v1p3 adlcp_v1p3.xsd '
                              'http://www.adlnet.org/xsd/adlseq_v1p3 adlseq_v1p3.xsd '
                              'http://www.adlnet.org/xsd/adlnav_v1p3 adlnav_v1p3.xsd'
    })

    metadata = ET.SubElement(manifest, 'metadata')
    ET.SubElement(metadata, 'schema').text = 'ADL SCORM'
    ET.SubElement(metadata, 'schemaversion').text = '2004 4th Edition'

    organizations = ET.SubElement(manifest, 'organizations', {'default': 'AIDA_ORG'})
    organization = ET.SubElement(organizations, 'organization', {'identifier': 'AIDA_ORG'})
    ET.SubElement(organization, 'title').text = course_title

    root_item = ET.SubElement(organization, 'item', {
        'identifier': 'ROOT',
        'identifierref': 'RES_MAIN',
        'isvisible': 'true'
    })
    ET.SubElement(root_item, 'title').text = course_title

    # Add each module
    for mod_idx, module in enumerate(modules):
        sanitized_title = sanitize_filename(module['title'])
        folder_name = f"Module_{module['number']}_{sanitized_title}"

        mod_item = ET.SubElement(root_item, 'item', {
            'identifier': f'MODULE_{mod_idx}',
            'identifierref': f'RES_MODULE_{mod_idx}',
            'isvisible': 'true'
        })
        ET.SubElement(mod_item, 'title').text = module['title']

    # Resources section
    resources = ET.SubElement(manifest, 'resources')

    # Main resource entry
    main_resource = ET.SubElement(resources, 'resource', {
        'identifier': 'RES_MAIN',
        'type': 'webcontent',
        'adlcp:scormType': 'sco',
        'href': 'index_lms.html'
    })
    for file in ['index_lms.html', 'ADLwrapper.js', 'course.js', 'navigation.json']:
        ET.SubElement(main_resource, 'file', {'href': file})

    # Add each module resource
    for mod_idx, module in enumerate(modules):
        sanitized_title = sanitize_filename(module['title'])
        folder_name = f"Module_{module['number']}_{module['title']}"

        mod_resource = ET.SubElement(resources, 'resource', {
            'identifier': f'RES_MODULE_{mod_idx}',
            'type': 'webcontent',
            'adlcp:scormType': 'sco',
            'href': f'index_lms.html?module={mod_idx}'
        })
        ET.SubElement(mod_resource, 'file', {'href': f"{folder_name}/Content.json.clean.json"})

    # Return pretty XML string
    rough_xml = ET.tostring(manifest, 'utf-8')
    parsed_xml = minidom.parseString(rough_xml)
    return parsed_xml.toprettyxml(indent="  ")
