# GAME ART INTELLIGENCE V2.0

小游戏市场、竞品广告与用户需求研究平台。仅使用免费公开数据，继续由GitHub Pages发布。

网站：https://huangmmm0328-boop.github.io/ArtEffect/

## 当前阶段

已完成第一阶段数据架构与页面重构：市场趋势雷达、统一游戏资料库、竞品广告／吸量研究、用户画像及未来预测。已有10款游戏、95条图片记录和11段真实GIF继续保留；旧版页面在`archive.html`单独归档。

微信畅销／畅玩、抖音畅销／热门四类榜单的来源注册、7/30/90日统计、历史快照与差分模型已建立，但采集器尚未启用。没有伪造排名、趋势曲线、广告消耗、CTR、CPA、ROI、年龄或性别调查。现有画像和3/6/12个月方向是带证据与风险的低置信度研究假设。

GitHub Actions每天北京时间10:30记录JSON状态并发布。来源成功时间、失败状态、页面构建时间分别保存。未接入来源的上次尝试和成功时间保持空值。后续逐个验证免费公开入口，再接入真实快照；不使用MomoRank付费历史，不要求广告账户。

## 数据与维护

- [完整数据架构与口径](docs/DATA-ARCHITECTURE.md)
- 数据契约：`intelligence/schemas/contracts.schema.json`
- 统一资料：`intelligence/data/`
- 校验：`node scripts/validate-intelligence.cjs`
- 统计测试：`node --test tests/analytics.test.mjs`
- 导入经人工核验的榜单：`node scripts/import-ranking-snapshot.cjs <JSON文件>`
- 旧素材包的解包、来源和校验记录继续保留；不重复上传或改写真实图片和GIF。

公开素材可查看不自动等于允许转载。所有图片保留原始来源与待确认授权状态。测试中的合成数据仅限tests目录，不进入网站。
