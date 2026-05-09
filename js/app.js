const API_BASE_URL = 'http://127.0.0.1:8000';

document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const jobForm = document.getElementById('jobForm');
    const jobsContainer = document.getElementById('jobsContainer');
    const refreshJobsBtn = document.getElementById('refreshJobsBtn');
    const successMsg = document.getElementById('successMsg');
    const errorMsg = document.getElementById('errorMsg');
    const loadingText = document.getElementById('loadingText');
    const noJobsMsg = document.getElementById('noJobsMsg');
    
    // Filters
    const statusFilter = document.getElementById('statusFilter');
    const priorityFilter = document.getElementById('priorityFilter');

    // Modals
    const editModal = document.getElementById('editModal');
    const editJobForm = document.getElementById('editJobForm');
    const closeEditModal = document.getElementById('closeEditModal');
    const editMessage = document.getElementById('editMessage');

    // Initial load
    fetchJobs();

    // Event Listeners
    jobForm.addEventListener('submit', handleJobSubmit);
    refreshJobsBtn.addEventListener('click', fetchJobs);
    statusFilter.addEventListener('change', fetchJobs);
    priorityFilter.addEventListener('change', fetchJobs);
    
    closeEditModal.addEventListener('click', () => {
        editModal.style.display = 'none';
    });

    editJobForm.addEventListener('submit', handleEditSubmit);

    // --- Fetch and Render Jobs ---
    async function fetchJobs() {
        showLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/jobs/sorted`);
            const data = await response.json();
            
            if (response.ok) {
                let jobs = data.jobs || [];
                
                const sValue = statusFilter.value.toLowerCase();
                const pValue = priorityFilter.value.toUpperCase();

                if (sValue) {
                    jobs = jobs.filter(j => j.status.toLowerCase() === sValue);
                }
                if (pValue) {
                    jobs = jobs.filter(j => j.priority.toUpperCase() === pValue);
                }

                renderJobs(jobs);
            } else {
                throw new Error(data.detail || 'Failed to fetch jobs');
            }
        } catch (err) {
            console.error(err);
            jobsContainer.innerHTML = `<p class="error-text">Error loading jobs: ${err.message}</p>`;
        } finally {
            showLoading(false);
        }
    }

    function renderJobs(jobs) {
        jobsContainer.innerHTML = '';
        
        if (jobs.length === 0) {
            noJobsMsg.style.display = 'block';
            return;
        }
        
        noJobsMsg.style.display = 'none';

        jobs.forEach(job => {
            const card = document.createElement('div');
            card.className = `job-card`;
            card.innerHTML = `
                <div class="job-card-header">
                    <div>
                        <div class="job-title">${job.customer_name}</div>
                        <div class="job-id">#${job.id}</div>
                    </div>
                    <span class="badge badge-${job.priority.toLowerCase()}">${job.priority}</span>
                </div>
                <div class="job-info">
                    <p><strong>📍 Location:</strong> ${job.location}</p>
                    <p><strong>⚙️ Status:</strong> <span class="status-badge status-${job.status}">${job.status}</span></p>
                    <p class="job-issue"><strong>📝 Issue:</strong> ${job.issue}</p>
                </div>
                <div class="job-actions">
                    <div class="action-btns">
                        <button class="edit-btn" onclick="openEditModal(${JSON.stringify(job).replace(/"/g, '&quot;')})">Edit</button>
                        ${job.status !== 'cancelled' ? 
                            `<button class="btn-cancel" onclick="cancelJob(${job.id})">Cancel</button>` : ''
                        }
                        <button class="btn-delete" onclick="deleteJob(${job.id})">Delete</button>
                    </div>
                </div>
            `;
            jobsContainer.appendChild(card);
        });
    }

    // --- Create Job ---
    async function handleJobSubmit(e) {
        e.preventDefault();
        const formData = new FormData(jobForm);
        const jobData = {
            customer_name: formData.get('customer_name'),
            location: formData.get('location'),
            issue: formData.get('issue'),
            priority: formData.get('priority').toUpperCase()
        };

        successMsg.style.display = 'none';
        errorMsg.style.display = 'none';

        try {
            const response = await fetch(`${API_BASE_URL}/jobs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(jobData)
            });
            
            const data = await response.json();

            if (response.ok) {
                successMsg.textContent = data.message;
                successMsg.style.display = 'block';
                jobForm.reset();
                fetchJobs();
            } else {
                throw new Error(data.error || data.detail || 'Failed to create job');
            }
        } catch (err) {
            errorMsg.textContent = err.message;
            errorMsg.style.display = 'block';
        }
    }

    // --- Edit Job ---
    async function handleEditSubmit(e) {
        e.preventDefault();
        const jobId = document.getElementById('edit_job_id').value;
        const jobData = {
            customer_name: document.getElementById('edit_customer_name').value,
            location: document.getElementById('edit_location').value,
            issue: document.getElementById('edit_issue').value,
            priority: document.getElementById('edit_priority').value.toUpperCase(),
            status: document.getElementById('edit_status').value.toLowerCase()
        };

        try {
            const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(jobData)
            });
            
            const data = await response.json();

            if (response.ok) {
                alert('Job updated successfully!');
                editModal.style.display = 'none';
                fetchJobs();
            } else {
                alert('Error: ' + (data.detail || 'Failed to update job'));
            }
        } catch (err) {
            alert('Network error: ' + err.message);
        }
    }

    // --- Visual Helpers ---
    function showLoading(isLoading) {
        if (loadingText) loadingText.style.display = isLoading ? 'block' : 'none';
    }

    // --- Global Attachment for onclick ---
    window.openEditModal = (job) => {
        document.getElementById('edit_job_id').value = job.id;
        document.getElementById('edit_customer_name').value = job.customer_name;
        document.getElementById('edit_location').value = job.location;
        document.getElementById('edit_issue').value = job.issue;
        document.getElementById('edit_priority').value = job.priority.charAt(0).toUpperCase() + job.priority.slice(1).toLowerCase();
        document.getElementById('edit_status').value = job.status;
        
        editModal.style.display = 'flex';
    };

    window.cancelJob = async (jobId) => {
        if (!confirm('Are you sure you want to cancel this job?')) return;

        try {
            const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/cancel`, {
                method: 'PATCH'
            });
            const data = await response.json();

            if (response.ok) {
                alert(data.message);
                fetchJobs();
            } else {
                alert('Error: ' + (data.detail || 'Failed to cancel job'));
            }
        } catch (err) {
            alert('Error: ' + err.message);
        }
    };

    window.deleteJob = async (jobId) => {
        if (!confirm('Are you sure you want to PERMANENTLY DELETE this job?')) return;

        try {
            const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`, {
                method: 'DELETE'
            });
            const data = await response.json();

            if (response.ok) {
                alert(data.message);
                fetchJobs();
            } else {
                alert('Error: ' + (data.detail || 'Failed to delete job'));
            }
        } catch (err) {
            alert('Error: ' + err.message);
        }
    };
});
