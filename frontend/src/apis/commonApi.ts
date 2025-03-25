import request from "@/utils/request";

export function getHelloWorld() {
	return request.get<{ message: string }>("/");
}
