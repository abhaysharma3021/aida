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
    
    # Component generation options
    generate_structure = BooleanField('Generate Course Structure', default=True)
    generate_strategies = BooleanField('Generate Instructional Strategies', default=True)
    generate_assessment = BooleanField('Generate Assessment Plan', default=True)
    
    additional_requirements = TextAreaField('Additional Requirements or Notes', 
                                          validators=[Optional(), Length(max=2000)])
    submit = SubmitField('Generate Course Design')