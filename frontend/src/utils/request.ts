// src/utils/request.js
import axios from "axios";
// import { message } from 'antd' // 或其他UI库的消息提示组件

// 创建axios实例
const service = axios.create({
	// 默认走 Vite 代理到 /api，这样 localhost 和外网域名都可用
	baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
	timeout: 10000, // 请求超时时间
});

// 请求拦截器
service.interceptors.request.use(
	(config) => {
		// 在发送请求之前做些什么
		// 例如：如果有token，添加到请求头
		// const token = localStorage.getItem('token')
		// if (token) {
		//   config.headers['Authorization'] = `Bearer ${token}`
		// }
		return config;
	},
	(error) => {
		// 对请求错误做些什么
		console.log(error); // for debug
		return Promise.reject(error);
	},
);

// 响应拦截器
service.interceptors.response.use(
	(response) => {
		// 对响应数据做点什么
		return response;
	},
	(error) => {
		// 对响应错误做点什么
		// console.log('err' + error) // for debug
		// message.error(error.message)
		return Promise.reject(error);
	},
);

export default service;
