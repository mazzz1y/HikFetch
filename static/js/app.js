const form = document.getElementById('downloadForm');
const taskList = document.getElementById('taskList');

const today = new Date().toISOString().split('T')[0];
document.getElementById('start_date').value = today;
document.getElementById('end_date').value = today;

async function createTask(formData) {
    const response = await fetch('/download', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(formData)
    });
    return await response.json();
}

async function loadTasks() {
    try {
        const response = await fetch('/tasks');
        const tasks = await response.json();
        renderTasks(tasks);
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

async function cancelTask(taskId) {
    try {
        await fetch(`/tasks/${taskId}/cancel`, {method: 'POST'});
        loadTasks();
    } catch (error) {
        console.error('Error canceling task:', error);
    }
}

function renderTasks(tasks) {
    if (tasks.length === 0) {
        taskList.innerHTML = '<div class="empty-state">No download tasks yet</div>';
        return;
    }

    tasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    taskList.innerHTML = tasks.map(task => {
        const progress = task.total > 0 ? Math.round((task.progress / task.total) * 100) : 0;
        const isActive = task.status === 'running' || task.status === 'pending';
        const showProgress = task.total > 0;

        return `
                <div class="task-item">
                    <div class="task-header">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span class="task-status ${task.status}">${task.status}</span>
                            <span style="font-family: monospace; color: #666; font-size: 12px; background: #f0f0f0; padding: 2px 8px; border-radius: 4px;">${task.display_id}</span>
                        </div>
                        <div class="task-actions">
                            ${isActive ? `<button class="btn btn-danger btn-small" onclick="cancelTask('${task.task_id}')">Cancel</button>` : ''}
                        </div>
                    </div>

                    <div class="task-info">
                        <div><strong>Channel:</strong> ${task.params.camera_channel}</div>
                        <div><strong>Time Range:</strong> ${task.params.start_datetime_str} - ${task.params.end_datetime_str}</div>
                        ${task.current_file ? `<div><strong>Current:</strong> ${task.current_file.split('/').pop()}</div>` : ''}
                        ${task.error ? `<div style="color: #d63031;"><strong>Error:</strong> ${task.error}</div>` : ''}
                        ${showProgress ? `<div><strong>Progress:</strong> ${task.progress}/${task.total} files (${progress}%)</div>` : ''}
                    </div>

                    ${showProgress ? `
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${Math.max(progress, 3)}%;"></div>
                        </div>
                    ` : task.status === 'running' ? `<div style="color: #666; font-size: 13px;">Finding files...</div>` : ''}

                    ${task.status === 'running' ? '<div><span class="spinner"></span> Downloading...</div>' : ''}
                </div>
            `;
    }).join('');
}

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        camera_channel: document.getElementById('camera_channel').value,
        start_date: document.getElementById('start_date').value,
        start_time: document.getElementById('start_time').value + ':00',
        end_date: document.getElementById('end_date').value,
        end_time: document.getElementById('end_time').value + ':59'
    };

    try {
        await createTask(formData);
        loadTasks();
    } catch (error) {
        alert('Error creating task: ' + error.message);
    }
});

async function loadUserInfo() {
    try {
        const response = await fetch('/auth/userinfo');
        if (response.ok) {
            const userInfoDiv = document.getElementById('userInfo');
            userInfoDiv.innerHTML = `
                <a href="/auth/logout" style="color: white; text-decoration: none; background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 5px; font-size: 14px;">Logout</a>
            `;
        }
    } catch (error) {
    }
}

loadTasks();
loadUserInfo();
setInterval(loadTasks, 2000);
