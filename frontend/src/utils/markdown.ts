import { marked } from 'marked'
import katex from 'katex'
import type { RendererObject, Renderer } from 'marked'

// 默认的markdown渲染配置
const defaultOptions = {
  breaks: true, // 允许换行
  gfm: true,    // 启用GitHub风格的Markdown
  headerIds: true, // 为标题添加id
  mangle: false,   // 不转义标题中的HTML
  sanitize: false, // 不净化HTML
}

// 处理数学公式
const renderMath = (tex: string, displayMode = false) => {
  try {
    return katex.renderToString(tex, {
      displayMode: displayMode,
      throwOnError: false,
      strict: false
    })
  } catch (err) {
    console.error('KaTeX rendering error:', err)
    return tex
  }
}

// 创建自定义渲染器
const renderer: Partial<RendererObject> = {
  paragraph(this: Renderer, token: { text: string }) {
    let text = token.text

    // 处理块级公式
    if (text.startsWith('\\[') && text.endsWith('\\]')) {
      const tex = text.slice(2, -2).trim()
      return `<div class="math-block">${renderMath(tex, true)}</div>`
    }

    // 处理行内公式
    text = text.replace(/\\\((.*?)\\\)/g, (_, tex) => renderMath(tex.trim(), false))
    
    // 处理带括号的公式，确保不是已经处理过的
    if (!text.includes('class="katex"')) {
      text = text.replace(/\((.*?)\)/g, (match, tex) => {
        // 检查是否是数学公式（包含数学符号）
        if (/[+\-*/=^_{}\\]/.test(tex)) {
          return renderMath(tex.trim(), false)
        }
        return match // 如果不是数学公式，保持原样
      })
    }

    return `<p>${text}</p>`
  }
}

// 配置marked
marked.use({ renderer })

/**
 * 渲染Markdown文本为HTML
 * @param content Markdown文本
 * @param options 可选的marked配置项
 * @returns 渲染后的HTML
 */
export const renderMarkdown = async (content: string, options = {}) => {
  // 预处理内容，确保数学公式正确换行
  content = content.replace(/\\\[\s*\n/g, '\\[')
                  .replace(/\n\s*\\\]/g, '\\]')
  return marked.parse(content, { ...defaultOptions, ...options })
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