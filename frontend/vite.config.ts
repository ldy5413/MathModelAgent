import path from "node:path";
import vue from "@vitejs/plugin-vue";
import autoprefixer from "autoprefixer";
import tailwind from "tailwindcss";
import { defineConfig, loadEnv } from "vite";

// Use a function config to access mode/env and allow custom hosts
export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, process.cwd(), "");
    // Comma-separated list of allowed hosts, e.g. "example.com,foo.bar"
    const allowedHosts = (env.VITE_ALLOWED_HOSTS || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    // Bind dev server externally when needed
    const devHost = env.VITE_DEV_HOST || true; // true -> 0.0.0.0

    return {
        css: {
            postcss: {
                plugins: [tailwind(), autoprefixer()],
            },
        },
        plugins: [vue()],
        resolve: {
            alias: {
                "@": path.resolve(__dirname, "./src"),
            },
        },
        server: {
            host: devHost === "false" ? false : devHost === "true" ? true : devHost,
            // Only set allowedHosts if provided; otherwise keep Vite defaults
            ...(allowedHosts.length ? { allowedHosts } : {}),
            cors: true,
            // Dev proxy so frontend can call same-origin /api and forward to backend
            proxy: {
                "/api": {
                    target: env.VITE_BACKEND_URL || env.VITE_API_PROXY_TARGET || "http://localhost:8000",
                    changeOrigin: true,
                    ws: true,
                    rewrite: (p) => p.replace(/^\/api/, ""),
                },
            },
        },
    };
});
