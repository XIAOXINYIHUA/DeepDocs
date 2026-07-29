export default function ProjectListPage() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-surface-50 p-8">
      <div className="max-w-2xl w-full">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-surface-900 mb-2">DeepDocs</h1>
          <p className="text-surface-500">
            全格式、可追溯的私有文档研究工作台
          </p>
        </div>

        <div className="bg-white rounded-lg border border-surface-200 p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary-50 flex items-center justify-center">
            <svg className="w-8 h-8 text-primary-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <h2 className="text-lg font-medium text-surface-700 mb-2">暂无项目</h2>
          <p className="text-surface-400 mb-6 text-sm">
            创建一个项目开始文档分析工作
          </p>
          <button className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium">
            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            新建项目
          </button>
        </div>

        <div className="mt-6 flex justify-center gap-4 text-sm text-surface-400">
          <span>混合模式 · DeepSeek</span>
          <span>本地解析 · BGE-M3 嵌入</span>
        </div>
      </div>
    </div>
  );
}
