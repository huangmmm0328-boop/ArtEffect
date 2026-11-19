# P0 数据库与导入契约

一个 SQLite 文件：data/p0.sqlite；原始文件在相邻 raw/ 目录按完整 SHA256 归档。结构定义在 app/schema.sql；单入口为 manage.py。

## 表与关系

| 表 | 用途与约束 |
|---|---|
| games | 平台独立身份、来源稳定ID、名称、发行商和可选资料；来源＋平台＋ID唯一 |
| game_source_ids | 来源身份到游戏档案的映射及证据；不做名称自动合并 |
| data_sources | 访问方式、权限、覆盖深度、粒度、最后尝试／成功／来源更新时间、成本与异常状态 |
| raw_documents | 原始文件SHA256、文件名、相对归档路径、字节数、导入时间、访问方法、内部用途 |
| snapshot_batches | 平台／来源／榜单／数据日期／采集时间／导入时间／源更新时间、范围、完整性、口径版本、修订和原文件外键 |
| ranking_snapshots | 每个批次每款游戏的真实榜位、平台、日期、状态、来源URL与原始行引用 |
| sync_logs | 成功、无变化、失败、受权限阻止；收到及保存条数、错误、文件、批次、起止时间 |
| archived_assets | 旧站117条素材引用、游戏关系、路径、SHA256、字节数、原来源、授权与证据类型 |

启用外键与事务。榜单和批次禁止 UPDATE/DELETE；同日修订追加版本，保留前一版本。页面只选每日期的最新修订，但旧行仍可通过原始记录 URL 查询。

## 时间与缺失值

- data_date：来源页面明确显示的榜单日期，不从抓取时间补出。
- fetched_at：实际观测时间，带时区；页面转换为北京时间。
- imported_at：本地写入时间。
- source_updated_at：来源没有披露时为 NULL，不能用采集时间替代。
- 覆盖深度：本轮只验证免费 Top10，绝不称覆盖11—200名。
- 发行商未提供：NULL；本期免费范围没有观测到：rank=NULL、独立状态；文件失败：日志失败，原有效榜单仍展示。
- 榜位0不是缺失值；rank_position 必须为正整数。没有把“未观测到”推成第11名或已下榜。

## CSV／JSON

正式 JSON 字段：schemaVersion=1、source、platform、rank_type、data_date、fetched_at、source_updated_at、coverage_depth、coverage_complete、definition_version、source_url、access_method、usage_scope、rows。

每行：source_game_id、name、rank_position、publisher（可空）、source_url。榜单URL和游戏URL必须与平台及稳定ID相符。

CSV 使用 UTF-8（支持BOM），首行字段为：

```text
source,platform,rank_type,data_date,fetched_at,source_updated_at,coverage_depth,coverage_complete,definition_version,source_url,access_method,usage_scope,source_game_id,name,rank_position,publisher,game_source_url
```

元数据必须在每行重复且一致，一个 CSV 只能含同源、同平台、同榜、同日期。布尔值只接受 true/false/1/0。文件限5MB。只允许已核验的 MomoRank 微信／抖音畅销榜人工记录或审核后的历史文件，usage_scope 必须为 local_internal_review_only。更换来源需先验证并开发适配器，不可只改来源名称绕过。

本地真实样本：data/evidence/momorank-wechat-2026-11-19.json、momorank-douyin-2026-11-19.json；对应 manual-recording-*.csv 是本项目依据真实人工记录转换的文件，**不是供应商官方导出**。公开代码不附这两份新增观测数据。旧站已有抖音历史 JSON 的原地址与文件位置见来源报告。

## 幂等、修订与失败

文件 SHA256 用于原文件去重，语义 SHA256 对平台／来源／榜单／日期／口径／范围及标准化事实去重；仅采集时间或 CSV/JSON 格式改变不新增榜位。同日期内容修订追加批次版本。单文件事务失败不留下部分游戏或部分榜位，旧快照不清空；错误记录在 sync_logs，最近成功时间保留。

变化仅比较相邻自然日、同源同榜同平台、相同口径与完整覆盖范围，且两天都真实观测到的游戏。正数=前一天榜位减当天榜位；曲线在缺测或口径／范围改变处断开。每个变化链接到前后两条原始行及原文件SHA256。

## 同步入口

```text
python manage.py init --seed
python manage.py import <已核验文件.csv或.json>
python manage.py sync --inbox data/inbox
python manage.py serve --port 4190
```

sync 只读取本地 inbox 文件，不访问榜单网页，不调用任何付费服务。它可在许可明确后被单个系统定时任务调用；本P0没有安装定时抓取或额外后台任务。网页上传需本地会话校验与人工核对复选框，不提供公网写接口。
