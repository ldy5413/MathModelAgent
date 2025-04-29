import { marked } from 'marked'

// 默认的markdown渲染配置
const defaultOptions = {
  breaks: true, // 允许换行
  gfm: true,    // 启用GitHub风格的Markdown
  headerIds: true, // 为标题添加id
  mangle: false,   // 不转义标题中的HTML
  sanitize: false, // 不净化HTML
}

/**
 * 渲染Markdown文本为HTML
 * @param content Markdown文本
 * @param options 可选的marked配置项
 * @returns 渲染后的HTML
 */
export const renderMarkdown = async (content: string, options = {}) => {
  return marked(content, { ...defaultOptions, ...options })
}

/**
 * 计算Markdown文本的行数
 * @param content Markdown文本
 * @returns 行数
 */
export const getMarkdownLines = (content: string) => {
  return content.split('\n').length
}

// 导出marked以备需要直接使用
export { marked }