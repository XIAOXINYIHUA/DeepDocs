"use client";

import { usePathname } from "next/navigation";

interface TopBarProps {
  projectName?: string;
}

export default function TopBar({ projectName }: TopBarProps) {
  const pathname = usePathname();

  const tabs = [
    { key: "documents", label: "文档", href: "#documents" },
    { key: "analysis", label: "分析", href: "#analysis" },
    { key: "reports", label: "报告", href: "#reports" },
  ];

  return (
    <header className="topbar">
      {/* 项目名称 */}
      <div className="flex items-center gap-3 flex-1">
        <span className="text-sm font-medium text-surface-700 truncate max-w-[240px]">
          {projectName || "DeepDocs"}
        </span>
      </div>

      {/* 标签导航 */}
      <nav className="flex items-center gap-1 mx-4">
        {tabs.map((tab) => {
          const isActive = pathname.includes(tab.key);
          return (
            <a
              key={tab.key}
              href={tab.href}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                isActive
                  ? "bg-primary-50 text-primary-700 font-medium"
                  : "text-surface-500 hover:text-surface-700 hover:bg-surface-100"
              }`}
            >
              {tab.label}
            </a>
          );
        })}
      </nav>

      {/* 右侧状态 */}
      <div className="flex items-center gap-3 text-xs text-surface-400">
        <span className="flex items-center gap-1.5 px-2 py-1 bg-surface-100 rounded-md">
          <span className="w-1.5 h-1.5 rounded-full bg-success-400" />
          混合模式
        </span>
        <span className="flex items-center gap-1.5 px-2 py-1 bg-surface-100 rounded-md">
          <span className="w-1.5 h-1.5 rounded-full bg-primary-400" />
          DeepSeek Chat
        </span>
        <button className="p-1.5 text-surface-400 hover:text-surface-600 rounded-md hover:bg-surface-100 transition-colors">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
    </header>
  );
}
