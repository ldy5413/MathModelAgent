import request from "@/utils/request";

export function getHelloWorld() {
	return request.get<{ message: string }>("/");
}

// 获取论文顺序
export function getWriterSeque() {
	return request.get<{ writer_seque: string[] }>("/writer_seque");
}


export function openFolderAPI(task_id: string) {
	return request.get<{ message: string }>("/open_folder", {
		params: {
			task_id,
		},
	});
}


export function exampleAPI(example_id: string, source: string) {
	return request.post<{
		task_id: string;
		status: string;
	}>("/example", {
		example_id,
		source,
	});
}

// 获取服务状态
export function getServiceStatus() {
	return request.get<{
		backend: { status: string; message: string };
		redis: { status: string; message: string };
	}>("/status");
}
// 历史任务列表
export function getTasks() {
  return request.get<{
    task_id: string
    created_at: string
    status: 'running' | 'completed' | 'pending'
    has_md: boolean
    has_docx: boolean
  }[]>("/tasks")
}

// 历史任务的消息
export function getTaskMessages(task_id: string) {
  return request.get<any[]>("/task_messages", {
    params: { task_id },
  })
}

export function getTaskStatus(task_id: string) {
  return request.get<{ task_id: string; paused: boolean; running: boolean }>("/task/status", {
    params: { task_id },
  })
}

export function pauseTask(task_id: string) {
  return request.post<{ success: boolean; message: string }>("/task/pause", null, {
    params: { task_id },
  })
}

export function resumeTask(task_id: string) {
  return request.post<{ success: boolean; message: string }>("/task/resume", null, {
    params: { task_id },
  })
}

export function startTask(task_id: string) {
  return request.post<{ success: boolean; message: string }>("/task/start", null, {
    params: { task_id },
  })
}

export function stopTask(task_id: string) {
  return request.post<{ success: boolean; message: string }>("/task/stop", null, {
    params: { task_id },
  })
}

export function resetTask(task_id: string, auto_start: boolean = true) {
  return request.post<{ success: boolean; message: string }>("/task/reset", null, {
    params: { task_id, auto_start },
  })
}

// 删除任务
export function deleteTask(task_id: string) {
  // 后端实现了 DELETE /tasks/{task_id}
  return request.delete<{ success: boolean; message: string }>(`/tasks/${task_id}`)
}

// 检查点响应（继续/反馈）
export function respondCheckpoint(task_id: string, payload: { checkpoint_id: string; action: 'continue' | 'feedback'; content?: string }) {
  return request.post<{ success: boolean }>("/task/checkpoint/respond", payload, {
    params: { task_id },
  })
}
