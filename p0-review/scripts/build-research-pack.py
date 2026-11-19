"""Compile manually verified public research. Never fetches market data."""
from pathlib import Path
import json,hashlib,sys,shutil
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def write(p,d):(ROOT/p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
date='2026-11-19';cases=[]
old_ids={'748248':'store-748248','790816':'store-790816'}
families={'521534':'volume-survival','748248':'volume-survival','759692':'volume-survival','790816':'comic-operations','472491':'story-merge','835993':'story-merge','747820':'story-merge','739104':'oriental-life'}
for group in ['strategy','cozy']:
 for g in read(f'data/research-expansion/{group}/research.json')['games']:
  external=str(g.get('taptapId') or g['id']);ident=old_ids.get(external,'public-'+external);assets=[]
  for i,a in enumerate(g['assets']):
   path=a['localPath'].replace('\\','/');path=path.removeprefix('p0-review/')
   p=ROOT/path;assert p.is_file(),p;assert hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256']
   assets.append({'id':ident+'-public-'+str(i+1),'localPath':path,'remoteUrl':a['remoteUrl'],'sourceUrl':a['sourceUrl'],'title':a['title'],'evidenceType':'publisher_publicity','label':'官方商店展示图 · 含宣传排版','rightsStatus':'public_viewing_republication_unconfirmed','width':a['width'],'height':a['height'],'sha256':a['sha256'],'reviewed':True})
  observations=[]
  for key,text in g['visualObservations'].items():
   if isinstance(text,dict):text=text.get('text','')
   observations.append({'title':{'color':'色彩','shape':'造型','character':'角色','scene':'场景','ui':'界面','skills':'反馈','cost':'制作考量（人工推断）','productionCostInference':'制作考量（人工推断）'}.get(key,key),'text':text})
  cases.append({'id':ident,'externalId':external,'name':g['name'],'publisher':g['publisher'],'sourceUrl':g['sourceUrl'],'familyId':families[external],'style':g['familySuggested'],'type':'合成／经营' if group=='cozy' else '生存／策略／经营','platformIdentityEvidence':g['platformIdentityEvidence'],'visualVersionConfirmed':False,'scope':'APP官方展示，小游戏画面版本未逐帧确认','observations':observations,'assets':assets,'reviewedAt':date})
official_url='https://developer.open-douyin.com/forum/bulletin/post/698d9852a9441abeb0d4c8e0'
downloads={d['id']:d for d in read('data/research-expansion/official/downloads.json')}
# These images were visually checked: they contain actual mini-game UI, not title posters.
official=[('cook','我来掌勺','tactile-creative','食物质感与轻量界面','食谱页以暖色纸张和食物大图组织选择，视觉中心是可辨认的食材与制作目标。'),('folk','噩梦守护战','dark-folk','暗调民俗＋弹球塔防','医院暗场景、灯光、符纸与明亮入口形成对比，界面可见小游戏胶囊与关卡入口。'),('bead','方块猫','tactile-creative','拼豆颗粒与图案完成感','密集彩色颗粒形成可识别图案，白底留出操作区；底部圆形道具与倒计时清楚分层。')]
from PIL import Image
for key,name,family,style,observation in official:
 d=downloads[key];p=ROOT/f'data/research-expansion/official/{key}.jpg';w,h=Image.open(p).size;ident='douyin-case-'+key
 cases.append({'id':ident,'name':name,'publisher':None,'sourceUrl':official_url,'familyId':family,'style':style,'type':'抖音IAA官方案例','platformIdentityEvidence':{'status':'platform_official_case','platforms':['抖音小游戏'],'sourceUrl':official_url,'summary':'抖音开放平台团队在2026年2月发布的已上线案例；并非2026年11月热榜。'},'visualVersionConfirmed':True,'scope':'抖音平台发布的当期案例画面；不是本站实时录屏或当前版本核验','observations':[{'title':'可见画面','text':observation},{'title':'制作考量（人工推断）','text':'以单屏核心物件与反馈为主要投入，仍需验证关卡、动画和交互；没有预算或工期数据。'}],'assets':[{'id':ident+'-official-1','localPath':p.relative_to(ROOT).as_posix(),'remoteUrl':d['url'],'sourceUrl':official_url,'title':name+' · 抖音官方案例画面','evidenceType':'official_case_capture','label':'平台公开案例画面 · 2026年2月','rightsStatus':'public_viewing_republication_unconfirmed','width':w,'height':h,'sha256':d['sha256'],'reviewed':True}],'reviewedAt':date})
market=read('data/research-expansion/market/research.json');monthly=market['monthlyObservations'];accepted={m['sourceId'] for m in monthly}
for m in monthly:
 m['coverageDepthDescription']=m['coverageDepth'];m['coverageDepth']=m['coverage']['sourceChartDepth']
sources=[s for s in market['sources'] if s['id'] in accepted]
reports=[
 {'id':'cgigc-2026-h1','title':'2026年1—6月中国游戏产业报告摘要','publisher':'中国音数协游戏工委','sourceUrl':'https://www.cgigc.com.cn/details.html?id=08df1552-7845-4315-8ecf-cc5e05727e5c&tp=news','publicationDate':'2026-09-18','period':'2026-01—2026-06','kind':'industry_report','primary':True,'findings':['小程序移动游戏市场收入316.57亿元，同比增长36.01%。','内购收入占66.8%，广告变现占33.2%。这是行业统计，不是单游戏收入或美术贡献。'],'method':'协会公开报告摘要，事件发布于2026-07-30，官网页面发布时间2026-09-18；未提供游戏美术分类占比。','supports':['market-context']},
 {'id':'ocean-audience-2026','title':'抖音九大游戏行业特色人群白皮书','publisher':'巨量引擎游戏行业／伽马数据','sourceUrl':'https://pdf.dfcfw.com/pdf/H3_AP202606101823409425_1.pdf?1781077433000.pdf=','publicationDate':'2026-06','period':'2026年公开报告；用户兴趣分群','kind':'audience_report','primary':True,'findings':['报告将低压力体验与庭院、装扮、商店经营等内容关联。','轻量小游戏分群中，消除／合成兴趣相对整体高28%，无双／割草高24.7%；是相对偏好差异，不是所有玩家占比。'],'method':'核对PDF第30、32、33页（印刷页码31、33、34）；特定兴趣人群不能替代本项目或单游戏实际用户画像，摘取页未披露样本量。','supports':['story-merge','oriental-life','bright-cartoon','tactile-creative']},
 {'id':'douyin-iaa-2026-01','title':'抖音IAA小游戏内容创意玩法风向标2026年第1期','publisher':'抖音开放平台团队','sourceUrl':official_url,'publicationDate':'2026-02-12','updatedAt':'2026-03-20','period':'2026年初平台经营案例','kind':'platform_cases','primary':True,'findings':['公开案例包含烹饪、拼豆图案与民俗弹球塔防等视觉与玩法组合。','这些案例证明平台已有相关产品；不代表当前畅销榜、长期留存或本项目广告回报。'],'method':'平台公开发布的案例分析，页面明确供创意参考并反对同质化与侵权。没有复制其全部营销数据。','supports':['dark-folk','tactile-creative']}
]
directions=[
 {'id':'story-merge','title':'合成与装饰：把“完成感”画出来','action':'轻中度项目优先做小样验证','caseNames':['浪漫餐厅','肥鹅美食街','梦幻消除战'],'previewStyle':None,'observation':'可辨认的食物或道具、角色表情与装修前后对照，比复杂背景更直接地交代目标。','logic':'用月榜连续出现验证玩法与题材存在商业样本，再用官方画面观察物件和场景怎样组织；两层证据不能推成美术因果。','next':'未来3个月先比较物件图标、完成反馈与装修目标；6个月再验证主题内容能否持续更新。','cost':'中等，持续资产量是重点：多级物件、家具和剧情头像；相对判断，不含预算。','risk':'成熟产品已有大量内容积累；只更换棋盘皮肤难形成差异。不能把兴趣分群直接当实际玩家。','test':'同一合成循环制作两套物件辨识度与装修反馈，记录目标理解、首局完成和回访。','reportIds':['ocean-audience-2026']},
 {'id':'volume-survival','title':'体积化城建：题材锚点统一整个世界','action':'有3D与长线内容能力再投入','caseNames':['无尽冬日','三国：冰河时代','奔奔王国'],'previewStyle':None,'observation':'熔炉、冰雪或中世纪建筑形成第一眼题材锚点，体块化英雄与重复建筑单元保持小屏轮廓。','logic':'多月头部存在只说明该方向已有验证；不意味着3D本身带来增长，更不意味着这是低成本空白赛道。','next':'3个月先测单场景与建筑升级的辨识度；6—12个月机会取决于内容生产与设备适配能力。','cost':'较高，建筑升级、英雄、动画、光照与特效需要多套资源；这是制作结构推断。','risk':'素材与内容投入高，不能用一张商店图推断实际性能；小游戏与APP画面版本仍需对照。','test':'同一场景在低端设备测试角色辨认、建筑层级、加载时长与升级反馈。','reportIds':['cgigc-2026-h1']},
 {'id':'oriental-life','title':'国风生活化：从战斗走向经营与养成','action':'保留文化符号，降低画面阅读负担','caseNames':['造化仙府','灵画师','我的花园世界'],'previewStyle':'oriental','observation':'山水、花园、传统建筑与Q版角色形成多种轻国风表达；不必全部依赖浓重水墨或密集法术。','logic':'同题材在经营、养成与战斗中有不同视觉任务；机会是明确服务玩法的风格，而非仅贴上“国风”标签。','next':'3—6个月先验证园艺、宗门或装备养成中的空间层级、物件收集与角色反馈。','cost':'中等；需要区分建筑、花卉、人物与UI的持续更新量。','risk':'国风题材成功案例不能证明所有国风美术都有效；不同项目的用户动机不能混用。','test':'保持玩法与数值一致，比较场景明度、文化符号密度和奖励可读性。','reportIds':['ocean-audience-2026']},
 {'id':'bright-cartoon','title':'卡通战斗：技能轮廓比粒子数量重要','action':'优先投入反馈层次与小屏可读性','caseNames':['向僵尸开炮','永远的蔚蓝星球','保卫向日葵'],'previewStyle':'cartoon','observation':'大体块敌人、明确弹道和范围轮廓承担战斗叙事；高亮特效也容易遮住敌我与数值。','logic':'重复在榜案例和已归档GIF支持把反馈作为设计重点；榜位不能证明增加特效密度会改善留存。','next':'未来3个月更值得验证有限强调色、命中节奏和层次分工，而非全面提高粒子密度。','cost':'中等，复用弹道、命中、范围和升级模块可以减少重复制作；不是已测成本。','risk':'割草兴趣偏好是特定人群结论；不能代替本项目实际测试。','test':'同一战斗录制三档特效密度，比较敌人辨识、目标追踪与主观疲劳。','reportIds':['ocean-audience-2026']},
 {'id':'dark-folk','title':'民俗微恐：用氛围形成差异，不凭单例下结论','action':'小规模探索，先保证可读性','caseNames':['镇邪人','噩梦守护战'],'previewStyle':'folk','observation':'冷暗背景、暖光入口、符纸与局部法术形成稳定情绪线索；平台案例还展示了民俗与弹球塔防的组合。','logic':'跨玩法已有案例，值得研究视觉辨识；一个游戏某日回落不足以判断整个题材上升或衰退。','next':'3个月制作路线、人物与光照原型；6个月是否扩大取决于实测和更多同期市场证据。','cost':'中等，氛围音画、灯光和场景叙事是额外投入。','risk':'暗场景影响小屏辨认，题材与平台合规要求需另行核验；旧期平台案例不是本月热度。','test':'固定路线与人物亮度，单独比较灯光、雾与符号密度。','reportIds':['douyin-iaa-2026-01']},
 {'id':'tactile-creative','title':'单屏创意：食物质感与颗粒完成感','action':'低成本机制原型，追求一眼看懂','caseNames':['我来掌勺','方块猫'],'previewStyle':None,'observation':'食谱的食物大图、拼豆颗粒和目标图案都能在单屏交代操作对象与完成状态。','logic':'官方案例提供已上线的机制与画面组合，但不能把2026年初的内容表现延长为11月持续趋势。','next':'未来3个月用少量物件或图案快速测试；长期机会依赖关卡变化和内容更新，而不是追热点照搬。','cost':'相对较低的原型投入；正式关卡、动画和运营仍有成本，未取得实际工期。','risk':'热点寿命与玩法新鲜度不确定；原图与主题不可直接挪用。','test':'用自有原创物件测试首次看懂率、完成反馈与重复游玩意愿。','reportIds':['douyin-iaa-2026-01']}
]
for index,d in enumerate(directions):d['order']=index
for case in cases:
 directory=ROOT/'data/research-expansion/archive'/case['id'];directory.mkdir(parents=True,exist_ok=True)
 for a in case['assets']:
  original=ROOT/a['localPath'];target=directory/(a['id']+original.suffix);shutil.copy2(original,target);a['originalArchivePath']=a['localPath'];a['localPath']=target.relative_to(ROOT).as_posix()
 (directory/'manifest.json').write_text(json.dumps(case,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
pack={'schemaVersion':1,'reviewedAt':date,'usageScope':'local_internal_review_only','sources':sources,'monthly':monthly,'cases':cases,'reports':reports,'directions':directions,'excludedSources':[s for s in market['sources'] if s['id'] not in accepted],'candidateDatasets':market['candidateDatasets'],'method':'人工核对公开文章月平均排名图、官方产品页和平台案例；不伪造日历史，不以榜位推算收入，不将商店宣传当作实录。'}
write('config/research-pack.json',pack);print(json.dumps({'new_cases':len(cases),'new_images':sum(len(g['assets']) for g in cases),'monthly_boards':len(monthly),'monthly_rows':sum(len(m['rows']) for m in monthly),'reports':len(reports)},ensure_ascii=False))
