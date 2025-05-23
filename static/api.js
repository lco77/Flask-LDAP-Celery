// Resolve a DNS name
function resolve(resolveUrl,hostname,statusDiv) {
    fetch(resolveUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            hostname: hostname
        })
    })
    .then(res => res.json())
    .catch(err => {
        statusDiv.innerText = "Error resolving: " + err;
    });
}

// Start a background task
function startTask(createTaskUrl,taskType,data,statusDiv) {
    statusDiv.innerText = "🚀 Starting task...";

    fetch(createTaskUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            type: taskType,
            data: data
        })
    })
    .then(res => res.json())
    .then(data => {
        const taskId = data.task_id;
        if (!taskId) {
            statusDiv.innerText = "❌ No task ID returned";
            return;
        }

        pollTask(getTaskUrl,taskId,pollInterval,statusDiv);

    })
    .catch(err => {
        statusDiv.innerText = "Error starting task: " + err;
    });
}

// Poll a background task
function pollTask(getTaskUrl,taskId,pollInterval,statusDiv) {
    // Poll every 2 seconds
    const poll = setInterval(() => {

        fetch(getTaskUrl.replace("__TASK_ID__", taskId))
            .then(res => res.json())
            .then(task => {
                if (task.status === "SUCCESS") {
                    clearInterval(poll);
                    if (task.success) {
                        statusDiv.innerText = "✅ Result: " + JSON.stringify(task.result);
                    } else {
                        statusDiv.innerText = "❌ Task failed";
                    }
                } else if (task.status === "FAILURE") {
                    statusDiv.innerText = "❌ Task failed";
                } else {
                    statusDiv.innerText = `🔍 Task status: ${task.status}`;
                }
            })
            .catch(err => {
                clearInterval(poll);
                statusDiv.innerText = "❌ Error checking status: " + err;
            });
    }, pollInterval);
}