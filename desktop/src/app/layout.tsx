import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "企业知识管理",
  description: "企业知识管理平台 - 个人知识库 + 企业知识库",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body style={{ margin: 0, fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
