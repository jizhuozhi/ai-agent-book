# 第十一章 · 个人 Agent 的安全沙盒与本地执行

← [返回正文](../book/chapter11.md) · [返回主目录](../README.md)

| 实验 | 目录 | 类型 | 验收内容 |
| --- | --- | --- | --- |
| 11-1 | [local-spreadsheet-sandbox](local-spreadsheet-sandbox/) | ✅ | 在 Bubblewrap 和 Landlock 下编辑测试表格，检查允许的读写、被拒绝的访问和宿主另存结果 |

想从头搭一遍，可以先看[从空目录搭建 Bubblewrap 沙盒](local-spreadsheet-sandbox/README.md#从空目录搭建-bubblewrap-沙盒)。再跑完整实验，观察同一份访问要求怎样用 Landlock 实现，以及候选结果怎样交回宿主。
