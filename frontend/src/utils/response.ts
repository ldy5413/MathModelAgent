// 对应 response.py 的结构
export type SystemMessageType = 'info' | 'warning' | 'success' | 'error';
export type AgentType = 'CoderAgent' | 'WriterAgent';

export interface BaseMessage {
  id: string;
  msg_type: 'system' | 'agent' | 'user';
  content?: string;
}

export interface SystemMessage extends BaseMessage {
  msg_type: 'system';
  type: SystemMessageType;
}

export interface AgentMessage extends BaseMessage {
  msg_type: 'agent';
  agent_type: AgentType;
}

export interface CodeExecutionResult {
  res_type: string;
  msg: string;
}

export interface CoderMessage extends AgentMessage {
  agent_type: 'CoderAgent';
  code?: string;
  code_result?: CodeExecutionResult;
}

export interface WriterMessage extends AgentMessage {
  agent_type: 'WriterAgent';
}

export interface UserMessage extends BaseMessage {
  msg_type: 'user';
  content: string;
}

export type Message = SystemMessage | CoderMessage | WriterMessage | UserMessage