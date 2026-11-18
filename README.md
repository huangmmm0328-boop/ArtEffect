# GAME ART INTELLIGENCE V2.0

免费小游戏市场与美术研究平台：https://huangmmm0328-boop.github.io/ArtEffect/

## 当前页面

市场雷达、游戏资料库、用户画像、未来预测（月度美术观察）。竞品广告页面已移除，原入口跳转到月度报告；旧广告资料保留归档且停止采集。现有10款视觉案例、95条图片及11段真实GIF继续保留。

## 月度美术观察

引力引擎匿名公开月榜按来源月份保存，当前月尚无月榜时使用月内实际日榜观察，不把上月数据改标为当月。画面风格按已核验实录人工标注，再由每日流程自动统计与生成报告；无实录的游戏保持未分类，商店宣传海报不进入实录分布。样本比例不代表市场份额，同名资料不自动证明平台版本一致。

未来方向按“样本事实—推导逻辑—下一阶段判断—限制与验证”组织，不再逐个列出热门游戏链接。页面内提供三种风格的构图生成器，可调整强调色与密度、换构图并下载1600×900 PNG；这是浏览器内生成的风格示意，不是实际游戏或完整原画，没有接入付费或AI生成API。

## 自动更新

GitHub Actions每日北京时间10:30采集日榜及月榜、保存JSON并重新生成月度报告。行业报告与原有素材保持来源信息。校验：node scripts/validate-intelligence.cjs；测试：node --test tests/analytics.test.mjs tests/public-rankings.test.cjs tests/monthly-analysis.test.mjs。

详细口径见[数据架构](docs/DATA-ARCHITECTURE.md)。
