from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField, IntegerField, BooleanField
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
                                       validators=[DataRequired()],
                                       description="List the main learning outcomes that students should achieve by the end of the course.")
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
    module_count = IntegerField('Number of Modules (leave blank to auto-detect from task analysis)', validators=[Optional()])
    
class MaterialsGenerationForm(FlaskForm):
    """Form for materials generation with tone selection."""
    
    # Tone selection - NEW FIELD
    content_tone = SelectField(
        'Content Generation Tone',
        choices=[
            ('default', 'Professional & Academic (Default)'),
            ('optimistic', 'Optimistic & Encouraging'),
            ('entertaining', 'Engaging & Entertaining'),
            ('humanized', 'Conversational & Personal')
        ],
        default='default',
        validators=[Optional()],
        description="Choose the tone and style for generated course materials"
    )
    
    # Detail level
    detail_level = SelectField(
        'Detail Level',
        choices=[
            ('comprehensive', 'Comprehensive (Recommended)'),
            ('detailed', 'Detailed'),
            ('standard', 'Standard')
        ],
        default='comprehensive',
        validators=[Optional()]
    )
    
    # Additional instructions
    additional_notes = TextAreaField(
        'Additional Instructions (Optional)',
        validators=[Optional(), Length(max=2000)],
        description="Any specific requirements, industry focus, or customizations"
    )
    
    submit = SubmitField('Generate Comprehensive Course Materials')
    # Component generation options
    generate_structure = BooleanField('Generate Course Structure', default=True)
    generate_strategies = BooleanField('Generate Instructional Strategies', default=True)
    generate_assessment = BooleanField('Generate Assessment Plan', default=True)
    
    additional_requirements = TextAreaField('Additional Requirements or Notes', 
                                          validators=[Optional(), Length(max=2000)])
    submit = SubmitField('Generate Course Design')