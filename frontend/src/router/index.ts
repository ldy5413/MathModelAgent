// 封转路由
import { createRouter, createWebHashHistory } from "vue-router";
// 路由配置
// meau 需要登录后才能访问

const routes = [
	{
		path: "/",
		redirect: "/session",
	},
	{
		path: "/login",
		component: () => import("@/pages/login/index.vue"),
	},
	{
		path: "/chat",
		component: () => import("@/pages/chat/index.vue"),
	},
	{
		path: "/session",
		component: () => import("@/pages/session/index.vue"),
	},
	{
		path: "/test",
		component: () => import("@/pages/test/index.vue"),
	},
	{
		path: "/test-jupyter",
		component: () => import("@/pages/test/testJupyter.vue"),
	},
];

// 创建路由
const router = createRouter({
	history: createWebHashHistory(),
	routes,
});

// 路由守卫
// router.beforeEach((to, from, next) => {})

export default router;
