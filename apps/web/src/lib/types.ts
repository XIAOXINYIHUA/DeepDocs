/* ─── DeepDocs 前端类型定义（与后端模型对齐） ─── */

// ─── 项目 / 工作区 ───
export interface Project {
  id: string;
  name: string;
  description?: string;
  is_active: boolean;
  kb_count?: number;
  doc_count?: number;
  created_at: string;
}

// ─── 知识库 ───
export interface KnowledgeBase {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  language: string;
  document_count: number;
  is_active: boolean;
  created_at: string;
}

// ─── 文档 ───
export type DocumentStatus =
  | "pending" | "uploading" | "parsing" | "ready" | "error" | "deleted";

export interface Document {
  id: string;
  kb_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: DocumentStatus;
  error_message?: string;
  current_version: number;
  page_count?: number;
  created_at: string;
}

// ─── 解析步骤 ───
export interface ParseProgress {
  step: "uploading" | "format_check" | "parsing" | "ocr" | "indexing" | "done" | "error";
  progress: number; // 0-100
  message: string;
  details?: ParseStepDetail[];
}

export interface ParseStepDetail {
  step: string;
  status: "pending" | "running" | "done" | "warning" | "error";
  message: string;
}

// ─── 问答 ───
export type AnalysisMode = "qa" | "summary" | "compare" | "extract" | "direct";

export interface ChatRequest {
  question: string;
  mode: AnalysisMode;
  model?: string;
  top_k?: number;
  rerank_top_k?: number;
  similarity_threshold?: number;
  temperature?: number;
  stream?: boolean;
}

export interface CitationData {
  file_name: string;
  page_number?: number;
  heading_path?: string;
  excerpt: string;
}

export interface ChatResponse {
  answer: string;
  citations: CitationData[];
  mode: string;
  model: string;
}

// ─── SSE 流式 Chunk ───
export type StreamChunkType = "text" | "citation" | "done" | "error";

export interface StreamChunk {
  type: StreamChunkType;
  content?: string;
  citation?: CitationData;
}

// ─── 文档预览 ───
export interface CitationHighlight {
  document_id: string;
  page_number: number;
  bbox?: { x0: number; y0: number; x1: number; y1: number };
  excerpt: string;
}

// ─── 比较矩阵 ───
export interface CompareCell {
  value: string;
  citation?: CitationData;
  highlight?: "normal" | "diff" | "risk" | "missing";
}

export interface CompareRow {
  dimension: string;
  cells: CompareCell[];
  risk_level?: "low" | "medium" | "high";
}

// ─── 抽取字段 ───
export interface ExtractField {
  name: string;
  type: "text" | "number" | "date" | "money" | "entity" | "list";
  required: boolean;
  description?: string;
}

export interface ExtractResult {
  field: string;
  value: string;
  confidence: number;
  citation?: CitationData;
  verified: boolean;
}

// ─── 报告块 ───
export type ReportBlockType =
  | "heading" | "ai_paragraph" | "citation" | "compare_table"
  | "extract_table" | "risk_card" | "quote" | "user_note" | "todo";

export interface ReportBlock {
  id: string;
  type: ReportBlockType;
  content: string;
  citations?: CitationData[];
  verified: boolean;
  editable: boolean;
}

// ─── 用户 ───
export interface User {
  id: string;
  email: string;
  username: string;
  display_name?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}
