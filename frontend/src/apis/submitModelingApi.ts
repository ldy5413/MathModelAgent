// ... existing code ...
import request from "@/utils/request";

export function submitModelingTask(
	problem: {
		task_id: string;
		ques_all: string;
		comp_template?: string;
		format_output?: string;
	},
	files?: File[],
) {
	const formData = new FormData();

	// 添加问题数据
	formData.append(
		"problem",
		JSON.stringify({
			task_id: problem.task_id,
			ques_all: problem.ques_all,
			comp_template: problem.comp_template || "CHINA",
			format_output: problem.format_output || "Markdown",
		}),
	);

	// 添加文件
	if (files) {
		for (const file of files) {
			formData.append("files", file);
		}
	}

	return request.post<{
		task_id: string;
		status: string;
	}>("/modeling/", formData, {
		headers: {
			"Content-Type": "multipart/form-data",
		},
	});
}
