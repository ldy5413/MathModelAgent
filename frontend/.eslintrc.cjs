module.exports = {
  root: true,
  env: {
    es2021: true,
    node: true
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:prettier/recommended',
    'plugin:vite/recommended'
  ],
  parser: 'vue-eslint-parser',
  parserOptions: {
    parser: '@typescript-eslint/parser',
    ecmaVersion: 'latest',
    sourceType: 'module'
  },
  rules: {
    'no-console': 'off', // 允许 console.log
    'prettier/prettier': 'error', // 将 Prettier 规则作为 ESLint 错误
    '@typescript-eslint/no-explicit-any': 'off', // 允许使用 any
    'vue/multi-word-component-names': 'off' // 允许单单词组件名
  }
}
