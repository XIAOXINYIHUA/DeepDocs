import type { Metadata } from "next";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "DeepDocs - 文档研究工作台",
  description: "全格式、可追溯的私有文档研究工作台",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="layout-container">{children}</body>
    </html>
  );
}
