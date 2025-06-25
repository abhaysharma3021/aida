document.addEventListener('DOMContentLoaded', function() {
    // Form submission handling with loading indicator
    const form = document.querySelector('form');
    const submitButton = document.querySelector('input[type="submit"]');
    
    if (form) {
        form.addEventListener('submit', function(e) {
            // Prevent multiple submissions
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.value = 'Generating Analysis...';
                
                // Add loading spinner next to button
                const spinner = document.createElement('span');
                spinner.className = 'spinner';
                submitButton.parentNode.appendChild(spinner);
            }
            
            // Form continues normal submission
        });
    }
    
    // Form field character counter for terminal objectives
    const objectivesField = document.getElementById('terminal_objectives');
    if (objectivesField) {
        // Create character counter element
        const counterDiv = document.createElement('div');
        counterDiv.className = 'char-counter';
        counterDiv.innerHTML = '0 characters';
        objectivesField.parentNode.appendChild(counterDiv);
        
        // Update counter on input
        objectivesField.addEventListener('input', function() {
            const count = this.value.length;
            counterDiv.innerHTML = count + ' characters';
            
            // Add warning class if too long (optional limit)
            if (count > 1000) {
                counterDiv.classList.add('warning');
            } else {
                counterDiv.classList.remove('warning');
            }
        });
    }
    
    // Handle Hide/Show button
    const hideButtons = document.querySelectorAll('.btn-hide, .toggle-section');
    if (hideButtons.length > 0) {
        hideButtons.forEach(button => {
            button.addEventListener('click', function() {
                const targetId = this.getAttribute('data-target') || 'audience-content';
                const targetSection = document.getElementById(targetId);
                
                if (targetSection) {
                    if (targetSection.style.display === 'none') {
                        targetSection.style.display = 'block';
                        this.innerHTML = '<i class="fas fa-eye-slash"></i> Hide';
                    } else {
                        targetSection.style.display = 'none';
                        this.innerHTML = '<i class="fas fa-eye"></i> Show';
                    }
                }
            });
        });
    }
    
    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('.btn-copy, .copy-content');
    if (copyButtons.length > 0) {
        copyButtons.forEach(button => {
            button.addEventListener('click', function() {
                const contentId = this.getAttribute('data-content') || 'audience-content';
                const contentElement = document.getElementById(contentId);
                
                if (contentElement) {
                    // Use modern clipboard API if available
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(contentElement.innerText)
                            .then(() => {
                                // Show success message
                                const originalText = this.innerHTML;
                                this.innerHTML = '<i class="fas fa-check"></i> Copied!';
                                
                                setTimeout(() => {
                                    this.innerHTML = originalText;
                                }, 2000);
                            })
                            .catch(err => {
                                console.error('Failed to copy text: ', err);
                                // Fallback to old method
                                copyUsingExecCommand(contentElement, this);
                            });
                    } else {
                        // Fallback for browsers that don't support clipboard API
                        copyUsingExecCommand(contentElement, this);
                    }
                }
            });
        });
    }
    
    function copyUsingExecCommand(contentElement, button) {
        // Create a temporary textarea to copy the text
        const textarea = document.createElement('textarea');
        textarea.value = contentElement.innerText;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        
        // Store original button content
        const originalContent = button.innerHTML;
        
        // Show copied confirmation
        button.innerHTML = '<i class="fas fa-check"></i> Copied!';
        
        // Reset button after delay
        setTimeout(() => {
            button.innerHTML = originalContent;
        }, 2000);
    }
    
    // Add validation for course topic field
    const courseTopic = document.getElementById('course_topic');
    if (courseTopic) {
        courseTopic.addEventListener('blur', function() {
            if (this.value.trim() === '') {
                this.classList.add('error-field');
                
                // Add error message if it doesn't exist
                let errorMsg = this.parentNode.querySelector('.field-error');
                if (!errorMsg) {
                    errorMsg = document.createElement('div');
                    errorMsg.className = 'field-error';
                    errorMsg.textContent = 'Course topic is required';
                    this.parentNode.appendChild(errorMsg);
                }
            } else {
                this.classList.remove('error-field');
                
                // Remove error message if it exists
                const errorMsg = this.parentNode.querySelector('.field-error');
                if (errorMsg) {
                    errorMsg.remove();
                }
            }
        });
    }
    
    // Apply special formatting to audience analysis sections
    const audienceContent = document.getElementById('audience-content');
    if (audienceContent) {
        applyFormattingToAudienceAnalysis(audienceContent);
    }
});

// Function to apply formatting to audience analysis
function applyFormattingToAudienceAnalysis(audienceContent) {
    // Find all strong tags (bold text) that mark sections
    const sectionTitles = audienceContent.querySelectorAll('strong');
    
    sectionTitles.forEach(title => {
        if (title.textContent.includes('Profile:')) {
            title.closest('p').classList.add('profile-heading');
            const list = title.closest('p').nextElementSibling;
            if (list && list.tagName === 'UL') {
                list.classList.add('profile-section');
            }
        }
        
        if (title.textContent.includes('Key Characteristics:')) {
            title.closest('p').classList.add('characteristics-heading');
            const list = title.closest('p').nextElementSibling;
            if (list && list.tagName === 'UL') {
                list.classList.add('characteristics-section');
            }
        }
        
        if (title.textContent.includes('Implications for Instructional Design:')) {
            title.closest('p').classList.add('implications-heading');
            const list = title.closest('p').nextElementSibling;
            if (list && list.tagName === 'UL') {
                list.classList.add('implications-section');
            }
        }
    });
}