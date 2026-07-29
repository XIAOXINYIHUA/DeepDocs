"use client";

import { useState } from "react";
import type { Document } from "@/lib/types";

interface SidebarProps {
  documents: Document[];
  selectedIds: Set<string>;
  onSelect: (id: string) => void;
  onSelectAll: () => void;
  onUpload: () => void;
}

export default function Sidebar({
  documents,
  selectedIds,
  onSelect,
  onSelectAll,
  onUpload,
}: SidebarProps) {
  const [search, setSearch] = useState("");

  const filtered = documents.filter((d) =>
    d.filename.toLowerCase().includes(search.toLowerCase())
  );

  const statusIcon = (status: string) => {
    switch (status) {
      case "ready":
        return <span className="evidence-dot evidence-dot--direct" />;
      case "parsing":
        return <span className="evidence-dot evidence-dot--partial" />;
      case "error":
        return <span className="evidence-dot evidence-dot--none" />;
      default:
        return <span className="evidence-dot evidence-dot--general" />;
    }
  };

  return (
    <aside className="sidebar-panel">
      {/* 标题 */}
      <div className="px-4 py-3 border-b border-surface-200">
        <h2 className="text-sm font-semibold text-surface-700">文档与目录</h2>
      </div>

      {/* 搜索 */}
      <div className="px-3 py-2">
        <input
          className="w-full px-2.5 py-1.5 text-sm border border-surface-200 rounded-md bg-surface-50
                     placeholder:text-surface-400 focus:outline-none focus:ring-1 focus:ring-primary-400 focus:border-primary-400"
          placeholder="搜索文档..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* 操作栏 */}
      <div className="flex items-center gap-2 px-3 py-1.5">
        <label className="flex items-center gap-1.5 text-xs text-surface-500 cursor-pointer hover:text-surface-700">
          <input
            type="checkbox"
            className="rounded border-surface-300"
            checked={selectedIds.size === documents.length && documents.length > 0}
            onChange={onSelectAll}
          />
          全选
        </label>
        <span className="text-xs text-surface-400 ml-auto">
          {documents.length} 个文件
        </span>
      </div>

      {/* 文档列表 */}
      <div className="flex-1 overflow-y-auto px-2">
        {filtered.length === 0 ? (
          <div className="px-3 py-8 text-center">
            <p className="text-xs text-surface-400">暂无文档</p>
            <p className="text-xs text-surface-300 mt-1">拖拽文件到此处上传</p>
          </div>
        ) : (
          <div className="space-y-0.5">
            {filtered.map((doc) => (
              <label
                key={doc.id}
                className={`flex items-start gap-2 px-2.5 py-2 rounded-md cursor-pointer transition-colors
                  hover:bg-surface-100 ${
                  selectedIds.has(doc.id) ? "bg-primary-50" : ""
                }`}
              >
                <input
                  type="checkbox"
                  className="mt-0.5 rounded border-surface-300"
                  checked={selectedIds.has(doc.id)}
                  onChange={() => onSelect(doc.id)}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    {statusIcon(doc.status)}
                    <span className="text-sm text-surface-700 truncate">
                      {doc.filename}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5 text-xs text-surface-400">
                    <span>{doc.file_type?.toUpperCase()}</span>
                    <span>{formatSize(doc.file_size)}</span>
                    {doc.status === "ready" && <span className="text-success-500">可用</span>}
                    {doc.status === "parsing" && <span className="text-warning-500">解析中</span>}
                    {doc.status === "error" && (
                      <span className="text-danger-500" title={doc.error_message}>
                        失败
                      </span>
                    )}
                  </div>
                </div>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* 上传按钮 */}
      <div className="p-3 border-t border-surface-200">
        <button
          onClick={onUpload}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium
            text-primary-700 bg-primary-50 rounded-lg hover:bg-primary-100 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 4v16m8-8H4" />
          </svg>
          上传文档
        </button>
      </div>
    </aside>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
