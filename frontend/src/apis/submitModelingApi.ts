// ... existing code ...
import request from "@/utils/request";

export function submitModelingTask(
    problem: {
        ques_all: string;
        comp_template?: string;
        format_output?: string;
        language?: string; // 'zh' | 'en'
    },
    files?: File[],
) {
    const formData = new FormData();
    // 添加问题数据
    formData.append("ques_all", problem.ques_all);
    // 模板映射：国赛/美赛 → CHINA/AMERICAN（后端枚举）
    const tpl = (problem.comp_template || 'CHINA').toUpperCase()
    const mappedTpl = tpl.includes('美') || tpl.includes('AMERICAN') ? 'AMERICAN' : 'CHINA'
    formData.append("comp_template", mappedTpl);
    formData.append("format_output", problem.format_output || "Markdown");
    // 语言：中文/英文 → zh/en
    const lang = (problem.language || '').toLowerCase()
    const langCode = lang.startsWith('en') || problem.language === '英文' ? 'en' : 'zh'
    formData.append("language", langCode);

	if (files) {
		// file 是文件对象

		// 添加文件
		if (files) {
			for (const file of files) {
				formData.append("files", file);
			}
		}

		return request.post<{
			task_id: string;
			status: string;
		}>("/modeling", formData, {
			headers: {
				"Content-Type": "multipart/form-data",
			},
			timeout: 30000, // 添加超时设置
		});
	}
}
