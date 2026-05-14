const API_BASE_URL = "http://127.0.0.1:8080";

// DOM Elements
const jobForm = document.getElementById("jobForm");
const jobsContainer = document.getElementById("jobsContainer");
const loadingText = document.getElementById("loadingText");
const noJobsMsg = document.getElementById("noJobsMsg");
const refreshJobsBtn = document.getElementById("refreshJobsBtn");

const statusFilter = document.getElementById("statusFilter");
const priorityFilter = document.getElementById("priorityFilter");

const editModal = document.getElementById("editModal");
const editJobForm = document.getElementById("editJobForm");
const closeEditModal = document.getElementById("closeEditModal");

// Global state for jobs
let allJobs = [];

// Initialize
document.addEventListener("DOMContentLoaded", () => {
    fetchJobs();

    // Event Listeners
    jobForm.addEventListener("submit", createJob);
    editJobForm.addEventListener("submit", updateJob);
    refreshJobsBtn.addEventListener("click", fetchJobs);
    closeEditModal.addEventListener("click", () => {
        editModal.style.display = "none";
    });

    // Filtering
    statusFilter.addEventListener("change", renderJobs);
    priorityFilter.addEventListener("change", renderJobs);

    // Close modal on outside click
    window.addEventListener("click", (event) => {
        if (event.target === editModal) {
            editModal.style.display = "none";
        }
    });
});

/**
 * Fetch all jobs from the backend
 */
async function fetchJobs() {
    try {
        showLoading(true);
        const response = await fetch(`${API_BASE_URL}/jobs`);
        const data = await response.json();

        if (response.ok) {
            allJobs = data.jobs || [];
            renderJobs();
        } else {
            showError("Failed to fetch jobs: " + (data.detail || "Unknown error"));
        }
    } catch (error) {
        showError("Network error while fetching jobs");
        console.error(error);
    } finally {
        showLoading(false);
    }
}

/**
 * Create a new job
 */
async function createJob(event) {
    event.preventDefault();
    const formData = new FormData(jobForm);
    const jobData = {
        customer_name: formData.get("customer_name"),
        location: formData.get("location"),
        issue: formData.get("issue"),
        priority: formData.get("priority"),
        status: "active" // Default status
    };

    try {
        const response = await fetch(`${API_BASE_URL}/jobs`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(jobData)
        });

        const data = await response.json();

        if (response.ok) {
            showSuccess("Job created successfully!");
            jobForm.reset();
            fetchJobs();
        } else {
            showError("Failed to create job: " + (data.error || data.detail || "Check fields"));
        }
    } catch (error) {
        showError("Network error while creating job");
        console.error(error);
    }
}

/**
 * Update an existing job
 */
async function updateJob(event) {
    event.preventDefault();
    const jobId = document.getElementById("edit_job_id").value;

    const jobData = {
        customer_name: document.getElementById("edit_customer_name").value,
        location: document.getElementById("edit_location").value,
        issue: document.getElementById("edit_issue").value,
        priority: document.getElementById("edit_priority").value,
        status: document.getElementById("edit_status").value
    };

    try {
        const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(jobData)
        });

        const data = await response.json();

        if (response.ok) {
            editModal.style.display = "none";
            fetchJobs();
        } else {
            alert("Update failed: " + (data.detail || "Check fields"));
        }
    } catch (error) {
        alert("Network error while updating job");
        console.error(error);
    }
}

/**
 * Cancel a job
 */
async function cancelJob(id) {
    if (!confirm("Are you sure you want to cancel this job?")) return;

    try {
        const response = await fetch(`${API_BASE_URL}/jobs/${id}/cancel`, {
            method: "PATCH"
        });

        if (response.ok) {
            fetchJobs();
        } else {
            const data = await response.json();
            alert("Failed to cancel job: " + (data.detail || "Unknown error"));
        }
    } catch (error) {
        alert("Network error while cancelling job");
        console.error(error);
    }
}

/**
 * Delete a job
 */
async function deleteJob(id) {
    if (!confirm("Are you sure you want to delete this job?")) return;

    try {
        const response = await fetch(`${API_BASE_URL}/jobs/${id}`, {
            method: "DELETE"
        });

        if (response.ok) {
            fetchJobs();
        } else {
            alert("Failed to delete job");
        }
    } catch (error) {
        alert("Network error while deleting job");
        console.error(error);
    }
}

/**
 * Open edit modal and populate data
 */
function openEditModal(job) {
    document.getElementById("edit_job_id").value = job.id;
    document.getElementById("edit_customer_name").value = job.customer_name;
    document.getElementById("edit_location").value = job.location;
    document.getElementById("edit_issue").value = job.issue;
    document.getElementById("edit_priority").value = job.priority;
    document.getElementById("edit_status").value = job.status;

    editModal.style.display = "flex";
}

/**
 * Render jobs list with filtering
 */
function renderJobs() {
    const selectedStatus = statusFilter.value;
    const selectedPriority = priorityFilter.value;

    const filteredJobs = allJobs.filter(job => {
        const matchStatus = selectedStatus === "" || job.status === selectedStatus;
        const matchPriority = selectedPriority === "" || job.priority === selectedPriority;
        return matchStatus && matchPriority;
    });

    jobsContainer.innerHTML = "";

    if (filteredJobs.length === 0) {
        noJobsMsg.style.display = "block";
        return;
    }

    noJobsMsg.style.display = "none";

    filteredJobs.forEach(job => {
        const card = document.createElement("div");
        card.className = `job-card priority-${job.priority.toLowerCase()}`;

        card.innerHTML = `
            <div class="job-card-header">
                <h3>${job.customer_name}</h3>
                <span class="badge badge-${job.status.replace(" ", "-")}">${job.status}</span>
            </div>
            <p class="job-location">📍 ${job.location}</p>
            <p class="job-issue">${job.issue}</p>
            <div class="job-card-footer">
                <span class="priority-label">Priority: ${job.priority}</span>
                <div class="job-actions">
                    <button class="btn-edit" onclick='openEditModalByData(${JSON.stringify(job).replace(/'/g, "&apos;")})'>Edit</button>
                    ${job.status !== 'cancelled' ? `<button class="btn-cancel" onclick="cancelJob(${job.id})" style="margin-left:8px; background:#fef3c7; color:#92400e; border:none; padding:8px 14px; border-radius:10px; font-weight:700; cursor:pointer;">Cancel</button>` : ''}
                    <button class="btn-delete" onclick="deleteJob(${job.id})">Delete</button>
                </div>
            </div>
        `;
        jobsContainer.appendChild(card);
    });
}

// Helper to handle the onclick with JSON
window.openEditModalByData = (job) => {
    openEditModal(job);
};

/**
 * UI Helpers
 */
function showLoading(isLoading) {
    loadingText.style.display = isLoading ? "block" : "none";
}

function showSuccess(msg) {
    const successMsg = document.getElementById("successMsg");
    successMsg.textContent = msg;
    successMsg.style.display = "block";
    setTimeout(() => successMsg.style.display = "none", 3000);
}

function showError(msg) {
    const errorMsg = document.getElementById("errorMsg");
    errorMsg.textContent = msg;
    errorMsg.style.display = "block";
    setTimeout(() => errorMsg.style.display = "none", 5000);
}
