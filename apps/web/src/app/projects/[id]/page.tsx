"use client";

import { useState } from "react";
import TopBar from "@/components/layout/TopBar";
import Sidebar from "@/components/layout/Sidebar";
import MainPanel from "@/components/layout/MainPanel";
import AnalysisPanel from "@/components/layout/AnalysisPanel";
import type { Document } from "@/lib/types";

// 示例数据
const MOCK_DOCUMENTS: Document[] = [
  {
    id: "1", kb_id: "kb1", filename: "合同A-采购协议.pdf",
    file_type: "pdf", file_size: 2_456_000,
    status: "ready", current_version: 2, created_at: "2026-07-20",
  },
  {
    id: "2", kb_id: "kb1", filename: "合同B-技术方案.docx",
    file_type: "docx", file_size: 1_230_000,
    status: "ready", current_version: 1, created_at: "2026-07-21",
  },
  {
    id: "3", kb_id: "kb1", filename: "附件-报价明细.xlsx",
    file_type: "xlsx", file_size: 890_000,
    status: "ready", current_version: 1, created_at: "2026-07-22",
  },
  {
    id: "4", kb_id: "kb1", filename: "会议纪要-202607.pdf",
    file_type: "pdf", file_size: 560_000,
    status: "parsing", current_version: 1, created_at: "2026-07-25",
  },
  {
    id: "5", kb_id: "kb1", filename: "需求规格说明书_v3.docx",
    file_type: "docx", file_size: 3_200_000,
    status: "error", current_version: 0, created_at: "2026-07-26",
    error_message: "文件格式异常，第12页图片解析失败",
  },
];

export default function ProjectPage() {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set(["1", "2"]));
  const [activeDoc, setActiveDoc] = useState<string | null>(null);

  const handleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleSelectAll = () => {
    setSelectedIds((prev) =>
      prev.size === MOCK_DOCUMENTS.length
        ? new Set()
        : new Set(MOCK_DOCUMENTS.map((d) => d.id))
    );
  };

  return (
    <>
      <TopBar projectName="2026 年采购项目审查" />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          documents={MOCK_DOCUMENTS}
          selectedIds={selectedIds}
          onSelect={handleSelect}
          onSelectAll={handleSelectAll}
          onUpload={() => alert("打开文件上传对话框")}
        />

        <MainPanel>
          {activeDoc ? (
            <div className="p-6">
              <div className="bg-white rounded-lg border border-surface-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-medium text-surface-800">
                    {MOCK_DOCUMENTS.find((d) => d.id === activeDoc)?.filename}
                  </h2>
                  <span className="text-xs text-surface-400">第 12 页 / 共 42 页</span>
                </div>
                {/* 模拟 PDF 内容 */}
                <div className="space-y-4 text-sm text-surface-700 leading-relaxed">
                  <div className="p-4 bg-primary-50 border-2 border-primary-400 rounded-lg citation-highlight">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium text-primary-700">引用区域</span>
                      <span className="text-xs text-primary-400">[1] 合同A 第12页 第4.2条</span>
                    </div>
                    <p>甲方应在全部货物验收合格后30个工作日内，向乙方支付合同总价的95%。</p>
                  </div>
                  <p>4.3 付款方式：银行转账。乙方应在付款前提供等额增值税专用发票。</p>
                  <p>4.4 质保金：合同总价的5%作为质保金，质保期满后15个工作日内支付。</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-surface-100 flex items-center justify-center">
                  <svg className="w-8 h-8 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </div>
                <p className="text-sm text-surface-400">点击引用链接或左侧文档查看内容</p>
              </div>
            </div>
          )}
        </MainPanel>

        <AnalysisPanel kbId="kb1" />
      </div>
    </>
  );
}
