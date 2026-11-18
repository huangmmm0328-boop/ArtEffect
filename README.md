# GAME ART INTELLIGENCE V2.0

免费公开数据研究平台，GitHub Pages：https://huangmmm0328-boop.github.io/ArtEffect/

已实际接入引力引擎4类Top20、MomoRank抖音2类Top10、有柴公开收录榜位。GitHub Actions每天北京时间10:30匿名获取当前榜位，保存JSON历史与变化，异常不覆盖历史。7/30/90天从真实观察逐日累计，不购买历史数据。

已接入8条巨量创意历史游戏行业案例（游戏归属未披露，单列参考），以及3份免费行业研究报告。腾讯旧创意入口要求投放账户，明确显示限制，不注册账户。用户年龄、性别和竞品广告效果不编造。

保留原10款视觉案例、95条图片和11段真实GIF。旧版页面保留archive.html。

详细口径见[数据架构](docs/DATA-ARCHITECTURE.md)。本地执行采集：node scripts/collect-intelligence.cjs；校验：node scripts/validate-intelligence.cjs；测试：node --test tests/analytics.test.mjs tests/public-rankings.test.cjs。测试数据不发布。
