"use client";

interface MainPanelProps {
  children?: React.ReactNode;
}

export default function MainPanel({ children }: MainPanelProps) {
  return (
    <main className="main-panel">
      {/* 文档预览区域 */}
      <div className="flex-1 overflow-y-auto bg-surface-50">
        {children || (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-surface-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
              </div>
              <h3 className="text-sm font-medium text-surface-500">选择文档预览</h3>
              <p className="text-xs text-surface-400 mt-1">
                点击左侧文档或引用链接查看内容
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 底部处理状态 */}
      <div className="h-8 min-h-[32px] px-4 flex items-center bg-white border-t border-surface-200">
        <div className="flex items-center gap-3 text-xs text-surface-400">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-success-400" />
            解析完成
          </span>
          <span>42 页</span>
          <span>128 个 Block</span>
        </div>
      </div>
    </main>
  );
}
