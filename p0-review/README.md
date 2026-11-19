# GAME ART INTELLIGENCE V2.0 · P0 独立验收

只执行用户正式任务书的P0：审计、备份、SQLite、真实榜单历史、来源状态和基础页面。**尚待用户阶段验收；不进入P1，不替换生产。**

## 打开本机预览

双击 `启动P0预览.cmd`，保持窗口打开，再访问 http://127.0.0.1:4190/ 。当前本地环境已经安装所需免费依赖并导入真实样本。关闭服务窗口即可停止。

其他设备／新检出环境，使用Python3.12：

```text
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python manage.py init --seed
.venv\Scripts\python manage.py serve --port 4190
```

Linux/macOS将解释器改为 `.venv/bin/python`。本地完整备份解包到baseline/时优先读取baseline；GitHub完整仓库检出时读取父目录已有真实JSON历史。

GitHub代码不新增公开上传本轮内部观测文件、数据库或媒体副本。故全新代码检出 `init --seed` 只导入旧仓库原有的抖音两天历史；本机完整验收数据库另有本轮微信／抖音人工记录，共3批30条榜位。没有微信文件时页面明确为空，不用其他平台代替。

## 已有页面

- 市场总览：微信／抖音独立，免费Top10、日期、采集时间、覆盖范围和真实变化。
- 单游戏历史：真实记录曲线、前后原始行、来源与修订。
- 数据与同步：权限、最近尝试／成功时间、错误与导入条数。
- 文件导入：核对后上传真实CSV／JSON，幂等与失败保护。
- 审计与备份：原10案例、95图片、11GIF、117条素材引用及校验；验收报告入口。

## 验证与同步

```text
.venv\Scripts\python tests/run_checks.py
.venv\Scripts\python manage.py import <真实文件路径>
.venv\Scripts\python manage.py sync --inbox data/inbox
```

同步入口只读取本地核验文件，未启用网页自动采集。测试使用已有真实历史文件；异常输入仅在独立临时数据库中做校验，不进入交付数据库。

## 交付报告

- docs/P0_ACCEPTANCE.md：逐条阶段验收、未完成项。
- docs/AUDIT.md、asset-inventory.json：生产审计与逐文件清点。
- docs/DATABASE.md：表结构、字段、时间、缺失与导入契约。
- docs/SOURCE_VERIFICATION.md、source-catalog.json：实际来源、权限、范围与限制。
- docs/MIGRATION.md：旧页面迁移计划及阶段隔离。
- docs/TEST_RESULTS.json、test-run.txt：实际执行测试输出。
- docs/CHANGE_MANIFEST.json：本轮新增或修改的文件清单。
- requirements/：正式任务书副本；原文件未改。

当前仅本机内部预览。免费可见不等于授权再发布；自动采集及对外发布许可未确认，故新增原始观测与SQLite保留在本机。GitHub Pages不能直接运行此后端。P0预览不是新的生产网址。
