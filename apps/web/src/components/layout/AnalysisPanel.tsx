"use client";

import { useState, useRef, useEffect } from "react";
import type { CitationData, AnalysisMode } from "@/lib/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: CitationData[];
}

interface AnalysisPanelProps {
  kbId?: string;
}

export default function AnalysisPanel({ kbId }: AnalysisPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<AnalysisMode>("qa");
  const [isStreaming, setIsStreaming] = useState(false);
  const [evidenceStats, setEvidenceStats] = useState({
    direct: 0,
    partial: 0,
    none: 0,
    general: 0,
  });
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const modes: { key: AnalysisMode; label: string }[] = [
    { key: "qa", label: "问答" },
    { key: "summary", label: "总结" },
    { key: "compare", label: "比较" },
    { key: "extract", label: "抽取" },
  ];

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMsg: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);

    // 模拟流式响应（实际调用 API）
    const assistantMsg: Message = {
      role: "assistant",
      content: "",
      citations: [],
    };
    setMessages((prev) => [...prev, assistantMsg]);

    // 模拟 SSE 流式
    const demoText =
      mode === "qa"
        ? "## 结论\n\n根据文档分析，付款周期为验收后 30 日。\n\n## 主要差异\n\n两个版本对逾期责任的定义不同。\n\n## 证据\n\n[1] 合同A，第12页，第4.2条\n[2] 合同B，第8页，第3.6条\n\n## 信息限制\n\n附件中没有找到验收标准的明确定义。"
        : mode === "summary"
        ? "## 文档摘要\n\n### 第一章 概述\n本文档介绍了项目背景和目标。\n\n### 第二章 技术方案\n提出了三套技术实施方案。\n\n### 第三章 预算\n总预算为 500 万元。"
        : mode === "compare"
        ? "## 比较结果\n\n| 项目 | 文档 A | 文档 B |\n|------|--------|--------|\n| 金额 | 120 万 | 135 万 |\n| 周期 | 30 日 | 15 日 |"
        : "## 抽取结果\n\n| 字段 | 值 | 置信度 |\n|------|----|--------|\n| 合同编号 | CT-2026-001 | 高 |\n| 甲方 | 某某有限公司 | 高 |\n| 金额 | 500,000 元 | 高 |";

    // 逐字流式输出
    for (let i = 0; i < demoText.length; i++) {
      await new Promise((r) => setTimeout(r, 10));
      setMessages((prev) => {
        const last = [...prev];
        const idx = last.length - 1;
        if (idx >= 0) {
          last[idx] = {
            ...last[idx],
            content: demoText.slice(0, i + 1),
          };
        }
        return last;
      });
    }

    // 模拟引用
    const fakeCitations: CitationData[] = [
      { file_name: "合同A.pdf", page_number: 12, heading_path: "4.2 付款条款", excerpt: "甲方应在验收后30日内支付全部款项..." },
      { file_name: "合同B.docx", page_number: 8, heading_path: "3.6 违约责任", excerpt: "逾期支付每日按0.1%收取违约金..." },
    ];

    setMessages((prev) => {
      const last = [...prev];
      const idx = last.length - 1;
      if (idx >= 0) {
        last[idx] = { ...last[idx], citations: fakeCitations };
      }
      return last;
    });

    setEvidenceStats({ direct: 2, partial: 0, none: 1, general: 0 });
    setIsStreaming(false);
  };

  return (
    <aside className="analysis-panel">
      {/* 分析模式选择 */}
      <div className="px-4 py-3 border-b border-surface-200">
        <div className="flex gap-1">
          {modes.map((m) => (
            <button
              key={m.key}
              onClick={() => setMode(m.key)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                mode === m.key
                  ? "bg-primary-600 text-white"
                  : "text-surface-500 hover:text-surface-700 hover:bg-surface-100"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* 分析范围指示 */}
      <div className="px-4 py-2 bg-surface-50 border-b border-surface-200 text-xs text-surface-500 flex items-center gap-2">
        <span>分析范围：</span>
        <span className="font-medium text-surface-700">全部已选文档</span>
        <span className="text-surface-400">·</span>
        <span>模式：严格依据文档</span>
        <span className="text-surface-400">·</span>
        <span className="text-surface-500">DeepSeek Chat</span>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {messages.length === 0 && (
          <div className="mt-8 text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-surface-100 flex items-center justify-center">
              <svg className="w-6 h-6 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </div>
            <p className="text-sm text-surface-400 mb-1">在右侧输入问题开始分析</p>
            <p className="text-xs text-surface-300">
              选择文档后切换到问答、总结、比较或抽取模式
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`${msg.role === "user" ? "text-right" : ""}`}
          >
            <div
              className={`inline-block max-w-[90%] rounded-lg px-4 py-3 text-sm ${
                msg.role === "user"
                  ? "bg-primary-600 text-white"
                  : "bg-surface-100 text-surface-800"
              }`}
            >
              <div className="whitespace-pre-wrap">{msg.content}</div>

              {/* 引用 */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-surface-200">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-medium text-surface-500">证据</span>
                  </div>
                  <div className="space-y-1.5">
                    {msg.citations.map((c, ci) => (
                      <button
                        key={ci}
                        className="w-full text-left px-2.5 py-2 rounded-md bg-white border border-surface-200
                                   hover:border-primary-300 transition-colors group"
                      >
                        <div className="flex items-center gap-1.5 text-xs text-surface-500">
                          <span className="w-1.5 h-1.5 rounded-full bg-success-400" />
                          <span className="font-medium text-primary-600">[{ci + 1}]</span>
                          <span>{c.file_name}</span>
                          {c.page_number && <span>· 第{c.page_number}页</span>}
                          {c.heading_path && <span>· {c.heading_path}</span>}
                        </div>
                        <p className="text-xs text-surface-400 mt-0.5 line-clamp-2 group-hover:text-surface-600">
                          {c.excerpt}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {/* 处理过程状态 */}
      {messages.length > 0 && (
        <div className="px-4 py-2 bg-surface-50 border-t border-surface-200">
          <div className="flex items-center gap-1.5 text-xs text-surface-400">
            <span className="w-1.5 h-1.5 rounded-full bg-success-400" />
            <span>检索 46 候选</span>
            <span className="text-surface-300">→</span>
            <span>混合 28</span>
            <span className="text-surface-300">→</span>
            <span>重排 8</span>
            <span className="text-surface-300">→</span>
            <span>引用 5</span>
          </div>
          <div className="flex items-center gap-3 mt-1.5 text-xs text-surface-400">
            <span className="flex items-center gap-1">
              <span className="evidence-dot evidence-dot--direct" />
              直接证据 {evidenceStats.direct}
            </span>
            <span className="flex items-center gap-1">
              <span className="evidence-dot evidence-dot--partial" />
              部分推断 {evidenceStats.partial}
            </span>
            <span className="flex items-center gap-1">
              <span className="evidence-dot evidence-dot--none" />
              证据不足 {evidenceStats.none}
            </span>
          </div>
        </div>
      )}

      {/* 输入框 */}
      <div className="p-4 border-t border-surface-200">
        <div className="flex gap-2">
          <input
            className="flex-1 px-3 py-2 text-sm border border-surface-200 rounded-lg bg-surface-50
                       placeholder:text-surface-400 focus:outline-none focus:ring-1 focus:ring-primary-400 focus:border-primary-400"
            placeholder="输入问题..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            disabled={isStreaming}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700
                       disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  );
}
