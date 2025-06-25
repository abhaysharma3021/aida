// === CONFIG ===
const secretKey = "privateKey";
let courseData = []; // [{ name, content }]
let currentModuleIndex = 0;
let currentTopicIndex = 0;
let sessionStartTime = new Date();

// === Assessment State ===
let assessmentState = {
  moduleIndex: null,
  currentQuestion: 0,
  answers: [],
  submitted: false,
};

// === Encode/Decode (UTF-8 Safe) ===
function encodeData(obj) {
  const jsonStr = JSON.stringify(obj);
  const bytes = new TextEncoder().encode(jsonStr);
  return btoa(String.fromCharCode(...bytes));
}

function decodeData(base64Str) {
  const binaryStr = atob(base64Str);
  const bytes = Uint8Array.from(binaryStr, (char) => char.charCodeAt(0));
  return JSON.parse(new TextDecoder().decode(bytes));
}

// === ISO 8601 SCORM session_time ===
function getSessionTime(startTime) {
  const diffMs = new Date() - startTime;
  const totalSeconds = diffMs / 1000;
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = (totalSeconds % 60).toFixed(2);
  return `P${days}DT${hours}H${minutes}M${seconds}S`;
}

// === Suspend Data ===
let suspendData = {
  lastModule: 0,
  lastTopic: 0,
  completed: {}, // e.g. { "0": [0, 1], "1": [0] }
};

async function loadCourseTitleFromManifest() {
  try {
    const response = await fetch("imsmanifest.xml");
    if (!response.ok) throw new Error("Manifest not found");

    const xmlText = await response.text();
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlText, "text/xml");

    // Extract title - this XPath may need adjustment based on your manifest structure
    const titleElement = xmlDoc.querySelector(
      "organizations organization title"
    );
    if (titleElement) {
      const title = titleElement.textContent;
      document.getElementById("course-title").textContent = title;
      document.title = title; // Also update browser tab title
    }
  } catch (error) {
    console.error("Error loading course title from manifest:", error);
    // Fallback to default title
    document.getElementById("course-title").textContent =
      "Financial Integrity (2025)";
  }
}

// === Load course and SCORM init ===
window.onload = async function () {
  // Load course title first
  await loadCourseTitleFromManifest();

  if (!doInitialize()) return;

  await loadAllModules();

  const raw = doGetValue("cmi.suspend_data");
  if (raw) {
    try {
      suspendData = decodeData(raw);
      currentModuleIndex = suspendData.lastModule || 0;

      // Check if last topic was an assessment
      if (suspendData.lastTopic === "assessment") {
        loadAssessment(currentModuleIndex);
      } else {
        currentTopicIndex = suspendData.lastTopic || 0;
        loadTopic(currentModuleIndex, currentTopicIndex);
      }
    } catch (e) {
      console.warn("Failed to decode suspend_data", e);
      currentTopicIndex = 0;
      loadTopic(currentModuleIndex, currentTopicIndex);
    }
  } else {
    loadTopic(currentModuleIndex, currentTopicIndex);
  }

  setTimeout(function () {
    document.getElementById("loader").style.display = "none";
  }, 1000);
};

// === Load all modules ===
async function loadAllModules() {
  const navRes = await fetch("navigation.json");
  const navigation = await navRes.json();

  courseData = await Promise.all(
    navigation.map(async (mod) => {
      // Load content
      const contentRes = await fetch(`${mod.path}/content.json.clean.json`);
      const contentJson = await contentRes.json();

      // Load assessment if exists
      let assessment = null;
      if (mod.hasAssessment) {
        try {
          const assessmentRes = await fetch(
            `${mod.path}/assessments.json.clean.json`
          );
          assessment = await assessmentRes.json();
        } catch (e) {
          console.error(`Failed to load assessment for ${mod.module}`, e);
        }
      }

      return {
        name: mod.module,
        path: mod.Path,
        content: contentJson,
        assessment: assessment,
      };
    })
  );
}

// === Load topic ===
function loadTopic(modIndex, topicIndex) {
  const module = courseData[modIndex];
  if (!module) return;

  const topics = module.content.chapter.topics;
  const topic = topics[topicIndex];
  if (!topic) return;

  currentModuleIndex = modIndex;
  currentTopicIndex = topicIndex;

  resetNavigationButtons();

  document.getElementById("course-content").innerHTML = `
    <h2>${topic.title}</h2>
    <p><strong>Overview:</strong> ${topic.overview}</p>
    <p><strong>Definition:</strong> ${topic.coreConcepts.definition}</p>
    <p><strong>Theory:</strong> ${topic.coreConcepts.theoreticalFoundation}</p>
    <p><strong>Key Components:</strong> ${topic.coreConcepts.keyComponents.join(
      ", "
    )}</p>
    <p><strong>Practical Use:</strong> ${topic.practicalApplications}</p>
    <p><strong>Best Practices:</strong><ul>${topic.bestPractices
      .map((bp) => `<li>${bp}</li>`)
      .join("")}</ul></p>
  `;

  if (typeof topicIndex === "number") {
    suspendData.lastModule = modIndex;
    suspendData.lastTopic = topicIndex;

    if (!suspendData.completed[modIndex]) {
      suspendData.completed[modIndex] = [];
    }

    if (!suspendData.completed[modIndex].includes(topicIndex)) {
      suspendData.completed[modIndex].push(topicIndex);
    }
  }

  highlightActiveTopic(currentModuleIndex, currentTopicIndex);

  suspendData.lastModule = modIndex;
  suspendData.lastTopic = topicIndex;

  if (!suspendData.completed[modIndex]) {
    suspendData.completed[modIndex] = [];
  }

  if (!suspendData.completed[modIndex].includes(topicIndex)) {
    suspendData.completed[modIndex].push(topicIndex);
  }

  const totalTopics = courseData.reduce(
    (sum, m) => sum + m.content.chapter.topics.length,
    0
  );
  const totalCompleted = Object.values(suspendData.completed).reduce(
    (sum, arr) => sum + arr.length,
    0
  );

  const progress = calculateProgress();
  doSetValue("cmi.progress_measure", progress.toFixed(4));

  if (progress >= 1) {
    doSetValue("cmi.completion_status", "completed");
    // doSetValue("cmi.success_status", "passed");
  }

  saveSuspendData();
  updateProgressBar();
}

function loadAssessment(modIndex) {
  const module = courseData[modIndex];
  if (!module || !module.assessment) return;

  assessmentState = {
    moduleIndex: modIndex,
    currentQuestion: 0,
    answers: [],
    submitted: false,
    feedback: {},
  };

  currentModuleIndex = modIndex;
  currentTopicIndex = "assessment";

  suspendData.lastModule = modIndex;
  suspendData.lastTopic = "assessment";

  highlightActiveTopic(modIndex, "assessment");

  renderQuestion(0);

  updateProgressBar();
}

function escapeSingleQuotes(str) {
  return str.replace(/'/g, "\\'");
}

function renderQuestion(questionIndex) {
  const module = courseData[assessmentState.moduleIndex];
  const assessment = module.assessment;
  const questions = [
    ...(assessment.comprehensive_assessments?.knowledge_check_questions
      ?.multiple_choice_questions || []),
    ...(assessment.comprehensive_assessments?.knowledge_check_questions
      ?.true_false_questions || []),
  ];

  if (!questions[questionIndex]) return;

  const question = questions[questionIndex];
  const isMCQ = question.hasOwnProperty("options");
  const hasFeedback = assessmentState.feedback[questionIndex] !== undefined;

  let html = `<div class="assessment-question">
    <h3>Question ${questionIndex + 1} of ${questions.length}</h3>
    <div class="card mb-4">
      <div class="card-body">
        <h5 class="card-title">${question.question}</h5>`;

  if (isMCQ) {
    html += `<div class="options mt-3">`;
    question.options.forEach((opt, optIndex) => {
      const isChecked =
        assessmentState.answers[questionIndex] === opt ? "checked" : "";
      const isDisabled = hasFeedback ? "disabled" : "";
      const escapedOpt = escapeSingleQuotes(opt);
      html += `
        <div class="form-check">
          <input class="form-check-input" type="radio" 
                 name="q-${questionIndex}" 
                 id="q-${questionIndex}-${optIndex}"
                 value="${opt}" 
                 ${isChecked}
                 ${isDisabled}
                 onchange="recordAnswer(${questionIndex}, '${escapedOpt}')">
          <label class="form-check-label" for="q-${questionIndex}-${optIndex}">
            ${opt}
          </label>
        </div>`;
    });
    html += `</div>`;
  } else {
    const trueChecked =
      assessmentState.answers[questionIndex] === "true" ? "checked" : "";
    const falseChecked =
      assessmentState.answers[questionIndex] === "false" ? "checked" : "";
    const isDisabled = hasFeedback ? "disabled" : "";

    html += `
      <div class="options mt-3">
        <div class="form-check">
          <input class="form-check-input" type="radio" 
                 name="q-${questionIndex}" 
                 id="q-${questionIndex}-true" 
                 value="true"
                 ${trueChecked}
                 ${isDisabled}
                 onchange="recordAnswer(${questionIndex}, 'true')">
          <label class="form-check-label" for="q-${questionIndex}-true">
            True
          </label>
        </div>
        <div class="form-check">
          <input class="form-check-input" type="radio" 
                 name="q-${questionIndex}" 
                 id="q-${questionIndex}-false" 
                 value="false"
                 ${falseChecked}
                 ${isDisabled}
                 onchange="recordAnswer(${questionIndex}, 'false')">
          <label class="form-check-label" for="q-${questionIndex}-false">
            False
          </label>
        </div>
      </div>`;
  }

  // Add submit button if not submitted yet
  if (!hasFeedback) {
    html += `
      <div class="mt-4">
        <button id="submit-btn" onclick="submitAnswer(${questionIndex})" 
                class="btn btn-primary"
                ${!assessmentState.answers[questionIndex] ? "disabled" : ""}>
          Submit Answer
        </button>
      </div>
    `;
  } else {
    // Show feedback
    const feedback = assessmentState.feedback[questionIndex];
    html += `
      <div class="feedback mt-4 p-3 rounded ${
        feedback.isCorrect ? "alert-success" : "alert-danger"
      }">
        <strong>${feedback.isCorrect ? "Correct!" : "Incorrect"}</strong>
        <p>${feedback.message}</p>
        <p><small>${feedback.reference}</small></p>
      </div>
      <div class="mt-3">
        <button onclick="${
          questionIndex < questions.length - 1
            ? "nextQuestion()"
            : "submitAssessment()"
        }" 
                class="btn btn-primary">
          ${
            questionIndex < questions.length - 1
              ? "Next Question"
              : "Finish Assessment"
          }
        </button>
      </div>
    `;
  }

  html += `</div></div></div>`;

  document.getElementById("course-content").innerHTML = html;
  const radioButtons = document.querySelectorAll('input[type="radio"]');
  radioButtons.forEach((radio) => {
    radio.addEventListener("change", () => {
      document.getElementById("submit-btn").disabled = false;
    });
  });

  // Update navigation buttons
  // const navButtons = document.querySelector(".navigation-buttons");
  // if (navButtons) {
  //   navButtons.innerHTML = `
  //     <button onclick="prevQuestion()" class="btn btn-light btn-sm ${
  //       questionIndex === 0 ? "disabled" : ""
  //     }">
  //       Previous
  //     </button>
  //     ${
  //       questionIndex === questions.length - 1
  //         ? `<button onclick="submitAssessment()" class="btn btn-primary btn-sm">Submit Answers</button>`
  //         : `<button onclick="nextQuestion()" class="btn btn-primary btn-sm">Next</button>`
  //     }
  //   `;
  // }
}

function submitAnswer(questionIndex) {
  const modIndex = assessmentState.moduleIndex;
  const module = courseData[modIndex];
  const assessment = module.assessment;
  const questions = [
    ...(assessment.comprehensive_assessments?.knowledge_check_questions
      ?.multiple_choice_questions || []),
    ...(assessment.comprehensive_assessments?.knowledge_check_questions
      ?.true_false_questions || []),
  ];

  const question = questions[questionIndex];
  const userAnswer = assessmentState.answers[questionIndex];
  let isCorrect = false;
  let correctAnswer = "";
  let reference = "";

  // Check MCQ
  if (question.options) {
    isCorrect = userAnswer === question.correct_answer;
    correctAnswer = question.correct_answer;
    reference = question.content_reference || "";
  }
  // Check True/False
  else if (typeof question.correct_answer === "boolean") {
    correctAnswer = question.correct_answer ? "true" : "false";
    isCorrect = userAnswer === correctAnswer;
    reference = question.content_reference || "";
  }

  // Record interaction
  recordInteraction(
    questionIndex,
    `${modIndex}-${questionIndex}`,
    question.options ? "choice" : "true-false",
    userAnswer,
    correctAnswer,
    isCorrect,
	question.question
  );

  // Store feedback
  assessmentState.feedback[questionIndex] = {
    isCorrect,
    message: isCorrect
      ? "Your answer is correct!"
      : `Correct answer: ${correctAnswer}`,
    reference,
  };

  // Re-render question to show feedback
  renderQuestion(questionIndex);
  updateProgressBar();
}

function recordAnswer(questionIndex, answer) {
  assessmentState.answers[questionIndex] = answer;
}

function nextQuestion() {
  if (assessmentState.currentQuestion < getTotalQuestions() - 1) {
    assessmentState.currentQuestion++;
    renderQuestion(assessmentState.currentQuestion);
  }
}

function prevQuestion() {
  if (assessmentState.currentQuestion > 0) {
    assessmentState.currentQuestion--;
    renderQuestion(assessmentState.currentQuestion);
  }
}

function getTotalQuestions() {
  const module = courseData[assessmentState.moduleIndex];
  const assessment = module.assessment;
  return (
    (assessment.comprehensive_assessments?.knowledge_check_questions
      ?.multiple_choice_questions?.length || 0) +
    (assessment.comprehensive_assessments?.knowledge_check_questions
      ?.true_false_questions?.length || 0)
  );
}

function submitAssessment() {
  const modIndex = assessmentState.moduleIndex;
  const module = courseData[modIndex];
  const assessment = module.assessment;
  assessmentState.submitted = true;

  let totalCorrect = 0;
  let totalQuestions = 0;

  // Count correct answers from feedback
  for (const [index, feedback] of Object.entries(assessmentState.feedback)) {
    if (feedback.isCorrect) totalCorrect++;
    totalQuestions++;
  }

  const score = totalCorrect / totalQuestions;

  // Update SCORM
  doSetValue("cmi.score.scaled", score.toFixed(4));
  doSetValue("cmi.score.raw", totalCorrect);
  doSetValue("cmi.score.min", 0);
  doSetValue("cmi.score.max", totalQuestions);

  if (score >= 0.7) {
    doSetValue("cmi.success_status", "passed");
  } else {
    doSetValue("cmi.success_status", "failed");
  }

  // Mark assessment as completed
  if (!suspendData.completed[modIndex]) suspendData.completed[modIndex] = [];
  if (!suspendData.completed[modIndex].includes("assessment")) {
    suspendData.completed[modIndex].push("assessment");
  }

  saveSuspendData();
  doCommit("");

  // Show results
  showAssessmentResults(totalCorrect, totalQuestions);
  updateProgressBar();
}

function showAssessmentResults(correct, total) {
  document.getElementById("course-content").innerHTML = `
    <div class="assessment-results">
      <h2>Assessment Results</h2>
      <div class="card mb-4">
        <div class="card-body text-center">
          <h3>${correct} / ${total} Correct</h3>
          <p>Score: ${Math.round((correct / total) * 100)}%</p>
          ${
            correct / total >= 0.7
              ? '<div class="text-success"><strong>Passed</strong></div>'
              : '<div class="text-danger"><strong>Not Passed</strong></div>'
          }
        </div>
      </div>
      
      <div class="text-center">
        <button onclick="continueAfterAssessment()" class="btn btn-primary">
          Continue
        </button>
      </div>
    </div>
  `;

  // Update navigation buttons
  const navButtons = document.querySelector(".navigation-buttons");
  if (navButtons) {
    navButtons.innerHTML = `
      <button onclick="prevQuestion()" class="btn btn-light btn-sm">
        Back to Questions
      </button>
      <button onclick="continueAfterAssessment()" class="btn btn-primary btn-sm">
        Continue
      </button>
    `;
  }
}

function continueAfterAssessment() {
  // Reset assessment state
  const modIndex = assessmentState.moduleIndex;
  assessmentState = {
    moduleIndex: null,
    currentQuestion: 0,
    answers: [],
    submitted: false,
  };

  // Go to next module
  if (modIndex < courseData.length - 1) {
    currentModuleIndex = modIndex + 1;
    currentTopicIndex = 0;
    loadTopic(currentModuleIndex, currentTopicIndex);
  } else {
    // Last module - go to first topic of first module
    currentModuleIndex = 0;
    currentTopicIndex = 0;
    loadTopic(currentModuleIndex, currentTopicIndex);
  }
  updateProgressBar();
}

function resetNavigationButtons() {
  const navButtons = document.querySelector(".navigation-buttons");
  if (navButtons) {
    navButtons.innerHTML = `
      <button onclick="prev()" class="btn back btn-light btn-sm">Back</button>
      <button onclick="next()" class="btn btn-primary btn-sm">Next</button>
    `;
  }
}

// Helper function to record interactions
function recordInteraction(
  index,
  id,
  type,
  response,
  correctResponse,
  isCorrect,
  description
) {
  const prefix = `cmi.interactions.Scene${
    currentModuleIndex + 1
  }.${currentTopicIndex}.Question${index + 1}`;

  doSetValue(`${prefix}.id`, id);
  doSetValue(`${prefix}.type`, type);
  doSetValue(`${prefix}.learner_response`, response);
  doSetValue(`${prefix}.result`, isCorrect ? "correct" : "incorrect");
  doSetValue(`${prefix}.timestamp`, new Date().toISOString());
  doSetValue(`${prefix}.description`, description);

  // Correct response pattern
  doSetValue(`${prefix}.correct_responses._count`, 1);
  doSetValue(`${prefix}.correct_responses.0.pattern`, correctResponse);

  // Optional: Set weighting (1 point per question)
  doSetValue(`${prefix}.weighting`, 1);
}

function calculateProgress() {
  let totalItems = 0;
  let completedItems = 0;

  courseData.forEach((module, modIndex) => {
    // Count topics
    totalItems += module.content.chapter.topics.length;

    // Count assessments
    if (module.assessment) totalItems++;

    // Count completed items
    if (suspendData.completed[modIndex]) {
      // Count completed topics
      const completedTopics = suspendData.completed[modIndex].filter(
        (item) => typeof item === "number"
      ).length;

      // Check if assessment is completed
      const assessmentCompleted =
        suspendData.completed[modIndex].includes("assessment");

      completedItems += completedTopics;
      if (assessmentCompleted) completedItems++;
    }
  });

  // Avoid division by zero
  return totalItems > 0 ? completedItems / totalItems : 0;
}

// function calculateProgress() {
//   let totalItems = 0;
//   let completedItems = 0;

//   courseData.forEach((module, modIndex) => {
//     // Count topics
//     totalItems += module.content.chapter.topics.length;

//     // Count assessments
//     if (module.assessment) totalItems++;

//     // Count completed items
//     if (suspendData.completed[modIndex]) {
//       completedItems += suspendData.completed[modIndex].length;
//     }
//   });

//   return completedItems / totalItems;
// }

// === Save suspend data ===
function saveSuspendData() {
  const encrypted = encodeData(suspendData);
  doSetValue("cmi.suspend_data", encrypted);

  const location =
    typeof currentTopicIndex === "number"
      ? `${currentModuleIndex}-${currentTopicIndex}`
      : `${currentModuleIndex}-assessment`;

  doSetValue("cmi.location", location);
  doCommit("");
}

// === Navigation ===
function next() {
  const module = courseData[currentModuleIndex];
  const topics = module.content.chapter.topics;

  // If we're in an assessment, do nothing (assessment has its own navigation)
  if (currentTopicIndex === "assessment") {
    continueAfterAssessment();
    return;
  }

  // Regular topic navigation
  if (currentTopicIndex < topics.length - 1) {
    currentTopicIndex++;
    loadTopic(currentModuleIndex, currentTopicIndex);
  } else if (module.assessment) {
    // After last topic, go to assessment
    loadAssessment(currentModuleIndex);
  } else if (currentModuleIndex < courseData.length - 1) {
    // Go to next module
    currentModuleIndex++;
    currentTopicIndex = 0;
    loadTopic(currentModuleIndex, currentTopicIndex);
  }
}

function prev() {
  // If we're in an assessment, do nothing (assessment has its own navigation)
  if (currentTopicIndex === "assessment") {
    currentTopicIndex = module.content.chapter.topics.length - 1;
    loadTopic(currentModuleIndex, currentTopicIndex);
    return;
  }

  // Regular topic navigation
  if (currentTopicIndex > 0) {
    currentTopicIndex--;
    loadTopic(currentModuleIndex, currentTopicIndex);
  } else if (currentModuleIndex > 0) {
    // Go to previous module
    currentModuleIndex--;
    const topics = courseData[currentModuleIndex].content.chapter.topics;
    const hasAssessment = courseData[currentModuleIndex].assessment;

    // Go to assessment if exists, otherwise last topic
    if (hasAssessment) {
      loadAssessment(currentModuleIndex);
    } else {
      currentTopicIndex = topics.length - 1;
      loadTopic(currentModuleIndex, currentTopicIndex);
    }
  }
}

function updateProgressBar() {
  const progress = calculateProgress();
  const progressBar = document.getElementById("progress-bar");
  const progressText = document.getElementById("progress-text");

  if (progressBar && progressText) {
    const percentage = Math.round(progress * 100);
    progressBar.style.width = `${percentage}%`;
    progressText.textContent = `${percentage}% Complete`;

    // Change color based on completion
    if (percentage >= 100) {
      progressBar.style.backgroundColor = "#2e7d32"; // Dark green
    } else if (percentage >= 70) {
      progressBar.style.backgroundColor = "#4caf50"; // Green
    } else if (percentage >= 40) {
      progressBar.style.backgroundColor = "#ff9800"; // Orange
    } else {
      progressBar.style.backgroundColor = "#f44336"; // Red
    }
  }
}

// === Unload handler ===
window.onbeforeunload = function () {
  const sessionTime = getSessionTime(sessionStartTime);
  doSetValue("cmi.session_time", sessionTime);
  doSetValue("cmi.exit", "suspend");
  saveSuspendData();
  doTerminate();
};
