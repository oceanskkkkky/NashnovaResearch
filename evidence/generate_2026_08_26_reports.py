from pathlib import Path

OUT = Path("E:/WS/NashnovaResearch/reports/stock-almanac")
OUT.mkdir(parents=True, exist_ok=True)

desktop = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="2026年8月26日A股盘后量价正交与拥挤度研究日报">
<title>A股选股日报｜2026-08-26</title>
<style>
:root{--paper:#f3efe6;--paper-deep:#e8e0d0;--ink:#18332d;--body:#26332f;--jade:#17705e;--red:#a83e32;--gold:#b98532;--line:rgba(24,51,45,.22);--muted:#69736d;--card:rgba(255,253,247,.9);--serif:STSong,"Songti SC",SimSun,serif;--sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}*{box-sizing:border-box}html{background:var(--paper-deep)}body{min-width:1268px;margin:0;color:var(--body);font:14px/1.65 var(--sans);background:var(--paper)}.topbar{background:var(--ink);color:#f8f2e5;border-bottom:3px solid var(--gold)}.topbar-inner{width:1220px;min-height:76px;margin:auto;display:flex;align-items:center;justify-content:space-between}.brand{display:flex;gap:12px;align-items:center}.seal{width:35px;height:35px;display:grid;place-items:center;border:1px solid #c99d55;color:#e8c887;font:700 20px var(--serif)}.brand strong{font:700 22px var(--serif)}.brand small{color:#c9d2ca}.nav a{color:#d7ddd4;text-decoration:none;border:1px solid rgba(248,242,229,.28);padding:7px 10px;margin-left:5px}.badge{color:#e6d4ad;border:1px solid rgba(232,200,135,.45);padding:6px 8px}.page{width:1220px;margin:auto;padding:36px 0}.hero{display:grid;grid-template-columns:1.45fr .72fr;gap:20px;padding-bottom:24px;border-bottom:1px solid var(--line)}.eyebrow,.kicker{color:var(--gold);font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase}.hero h1{margin:10px 0;font:700 46px/1.12 var(--serif);color:var(--ink)}.hero h1 strong,.up{color:var(--red)}.down{color:var(--jade)}.hero-copy{font-size:15px;color:#52605a}.ritual{display:flex;gap:8px;margin-top:16px}.ritual span,.tag,.pill{border:1px solid var(--line);padding:6px 9px;background:#fffaf0}.ritual b{color:var(--red)}.ritual .avoid b{color:var(--jade)}.dark-summary{background:var(--ink);color:#f8f2e5;padding:22px;border-left:5px solid var(--gold)}.dark-summary h2{color:#e8c887;font:700 26px var(--serif);margin:8px 0}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:16px}.stats div{border:1px solid rgba(248,242,229,.2);padding:9px}.stats b{display:block;color:#e8c887;font-size:22px}.stats span{font-size:11px;color:#c9d2ca}.section{margin-top:22px}.card{background:var(--card);border:1px solid var(--line);padding:22px}.card-head{display:flex;align-items:flex-start;justify-content:space-between;border-bottom:1px solid var(--line);margin-bottom:15px;padding-bottom:10px}.card h2{margin:2px 0;color:var(--ink);font:700 28px var(--serif)}.grid{display:grid;gap:12px}.g4{grid-template-columns:repeat(4,1fr)}.g3{grid-template-columns:repeat(3,1fr)}.metric,.panel{border:1px solid var(--line);background:#fffaf0;padding:12px}.metric span{display:block;color:var(--muted);font-size:12px}.metric b{display:block;margin-top:5px;color:var(--ink);font-size:17px}.lead{font-size:15px}.note{color:var(--muted);font-size:12px}.warn{color:#8b4a17}.observe{color:#80651f}table{width:100%;border-collapse:collapse;table-layout:fixed}th,td{border-bottom:1px solid var(--line);padding:9px 8px;text-align:left;vertical-align:top}th{color:var(--muted);font-size:12px}.stock{display:grid;grid-template-columns:250px 1fr;gap:18px;border-top:3px solid var(--gold);padding:16px;background:#fffaf0;margin-top:12px}.stock h3{margin:0;color:var(--ink);font:700 24px var(--serif)}.stock dl{display:grid;grid-template-columns:105px 1fr;margin:0}.stock dt,.stock dd{padding:6px 0;border-bottom:1px dashed var(--line)}.stock dt{color:var(--muted)}.stock dd{margin:0}.strategy{border-left:5px solid var(--red)}.disclaimer{background:#efe9dc;border:1px solid var(--line);padding:12px}details{margin-top:18px;background:#eee8dc;border:1px solid var(--line);padding:14px}summary{cursor:pointer;color:var(--ink);font-weight:700}.footer{width:1220px;margin:0 auto 30px;color:var(--muted);font-size:12px;text-align:center}
</style>
</head>
<body>
<header class="topbar"><div class="topbar-inner"><div class="brand"><span class="seal">历</span><div><strong>股市老黄历</strong><br><small>A-SHARE DAILY RESEARCH</small></div></div><nav class="nav" aria-label="日报章节"><a href="#macro">宏观</a><a href="#market">大盘</a><a href="#sectors">板块</a><a href="#picks">选股</a><a href="#risks">风险</a></nav><span class="badge">盘后 · V2</span></div></header>
<main class="page">
<header id="cover" class="hero"><div><div class="eyebrow">评分交易日 2026-08-26 · 北京时间盘后</div><h1>今日 <strong>缩量反弹，回调优先</strong></h1><p class="hero-copy">三大指数同步收涨，市场宽度改善，但成交只有20日均量的79.43%。29个申万二级行业完成量价正交后，工业金属是本期唯一达到65分门槛的方向；资金残差确认较强，同时拥挤度五日快速升温，操作上不宜追价。</p><div class="ritual"><span><b>宜</b>等均线支撑与资金确认</span><span class="avoid"><b>忌</b>追逐加速段与单日涨停</span></div><p class="note">老黄历仅为标题包装，正文为数据研究。</p></div><aside class="dark-summary"><div>数据截至 2026-08-26 收盘</div><h2>中性 · 两只条件观察</h2><p>环境分55.8。中性市场门槛68分，兴业银锡70.3、盛达资源69.3入榜；同属工业金属，合计不超过两只。</p><div class="stats"><div><b>1</b><span>正式板块</span></div><div><b>2</b><span>条件观察</span></div><div><b>29</b><span>横截面行业</span></div></div></aside></header>
<section id="executive-summary" class="section card"><div class="card-head"><div><div class="kicker">00 / market brief</div><h2>行情摘要</h2></div><span class="tag">结论先行</span></div><div class="grid g4"><div class="metric"><span>市场状态</span><b>中性 55.8</b></div><div class="metric"><span>市场宽度</span><b>涨2946 / 跌2448</b></div><div class="metric"><span>两市成交</span><b>18087亿元</b></div><div class="metric"><span>重点方向</span><b>工业金属 69.04</b></div></div><p class="lead">核心矛盾是“指数反弹、广度改善，但量能不足且工业金属拥挤加速”。风险暴露宜维持中性，优先选择基本面已兑现、技术位置不过热的标的，并等待回调确认。</p></section>
<section id="macro" class="section card"><div class="card-head"><div><div class="kicker">01 / macro pulse</div><h2>宏观大势</h2></div><span class="tag">流动性 · 风险</span></div><div class="grid g3"><div class="panel"><b>公开市场净投放</b><p>公开信息显示8月26日开展2395亿元7天期逆回购，当日净投放2395亿元。短端资金环境偏宽松，有利于缓冲风险偏好。</p></div><div class="panel"><b>货币活化仍偏弱</b><p>2026年7月M1同比4.0%、M2同比7.7%，剪刀差为-3.7个百分点。总量温和，但企业资金活化仍需观察。</p></div><div class="panel"><b>全球风险按中性降级</b><p>VIX、美元、美债利率与海外指数未取得同一时点可审计数据，统一按50分处理，不代表外部风险较低。</p></div></div><p class="note">来源与时点：WeStock宏观结构化数据（最新发布期2026年7月、资金利率截至2026-08-25）；公开市场操作为2026-08-26公开信息，外部检索仅作定性复核。</p></section>
<section id="market" class="section card"><div class="card-head"><div><div class="kicker">02 / broad market</div><h2>大盘判断</h2></div><span class="tag">2026-08-26 收盘</span></div><div class="grid g4"><div class="metric"><span>上证指数</span><b>3912.52 <i class="up">+0.59%</i></b></div><div class="metric"><span>深证成指</span><b>13841.33 <i class="up">+0.69%</i></b></div><div class="metric"><span>创业板指</span><b>3414.88 <i class="up">+0.51%</i></b></div><div class="metric"><span>成交相对20日均值</span><b>79.43%</b></div></div><div class="grid g3" style="margin-top:12px"><div class="panel"><b>宽度改善</b><p>上涨占比53.08%，涨停51家、跌停1家；5至250日各周期新高数均高于新低数。</p></div><div class="panel"><b>缩量修复</b><p>成交18087.23亿元，为5日均量94.14%、20日均量79.43%，尚未形成放量突破。</p></div><div class="panel"><b>长周期仍弱</b><p>上证高于MA20但低于MA60；深证与创业板60日收益仍为负，短期价值风格占优。</p></div></div><p class="note">来源：WeStock带日期市场总览与指数数据，数据日2026-08-26。涨停家数另有hithink 52只口径，主评分采用51只，不取平均。</p></section>
<section id="sectors" class="section card"><div class="card-head"><div><div class="kicker">03 / sector monitor</div><h2>板块筛选</h2></div><span class="tag">1个方向达标</span></div><table><thead><tr><th>行业</th><th>价格P</th><th>资金F</th><th>正交资金R</th><th>趋势T</th><th>拥挤C</th><th>扣分</th><th>热度</th></tr></thead><tbody><tr><td><b>工业金属</b></td><td>92.68</td><td>89.64</td><td>82.14</td><td>89.52</td><td class="warn">70.67</td><td class="warn">15.31</td><td class="up"><b>69.04</b></td></tr><tr><td>汽车零部件</td><td>49.82</td><td>78.21</td><td>100.00</td><td>64.88</td><td>23.16</td><td>3.71</td><td class="observe">63.70</td></tr><tr><td>消费电子</td><td>56.43</td><td>64.29</td><td>75.00</td><td>62.00</td><td>25.51</td><td>4.08</td><td>63.28</td></tr><tr><td>电力</td><td>39.11</td><td>45.54</td><td>57.14</td><td>44.52</td><td>32.43</td><td>5.19</td><td>61.02</td></tr><tr><td>光伏设备</td><td>62.86</td><td>45.89</td><td>17.86</td><td>49.36</td><td>20.58</td><td>3.29</td><td>59.50</td></tr></tbody></table><div class="grid g3" style="margin-top:12px"><div class="panel"><b>为什么现在</b><p>工业金属1/5/20日收益分别为+3.33%、+5.53%、+7.82%，成份股上涨广度91.53%。</p></div><div class="panel"><b>资金是否确认</b><p>正交资金R=82.14，说明资金强度高于价格表现可解释部分，未触发价格强、资金弱的背离预警。</p></div><div class="panel"><b>最大风险</b><p>拥挤度C=70.67，五日上升46.22，扣15.31分，触发“拥挤升温”和“拥挤加速”。</p></div></div><p class="note">模型在29个申万二级行业完整横截面上回归：样本29、覆盖率100%、beta=0.7010。非趋势分项缺少统一横截面证据，按50分降级。</p></section>
<section id="picks" class="section card"><div class="card-head"><div><div class="kicker">04 / stock selection</div><h2>核心选股</h2></div><span class="tag">中性市门槛 68</span></div><table><thead><tr><th>股票</th><th>方向</th><th>最终分</th><th>置信度</th><th>评分日收盘</th><th>建议</th><th>核心风险</th></tr></thead><tbody><tr><td><b>兴业银锡 000426</b></td><td>工业金属</td><td class="up"><b>70.3</b></td><td>89%</td><td>40.13元</td><td>回调确认</td><td>安全事故、并购执行</td></tr><tr><td><b>盛达资源 000603</b></td><td>工业金属</td><td class="up"><b>69.3</b></td><td>92%</td><td>37.16元</td><td>逢回调观察</td><td>涨幅较大、当日资金转弱</td></tr></tbody></table>
<div class="stock"><div><h3>兴业银锡 000426</h3><span class="pill">70.3 · 回调确认</span><p class="note">StockScore 82.8｜风险扣5分｜置信度89%</p></div><dl><dt>逻辑</dt><dd>盈利能力、银锡价格弹性和中期资金结构较强，技术位置比同方向热门股更克制。</dd><dt>关键事实</dt><dd>2026Q1营收约21.30亿元、归母净利润约13.38亿元；当日主力净流出约0.93亿元，但5/20日仍净流入约12.19亿元和7.38亿元。</dd><dt>观察条件</dt><dd>优先等待37.5—38.5元区域缩量企稳；确认应包含收盘重新站稳20日线及资金转回净流入。</dd><dt>减仓触发</dt><dd>接近布林上轨43.88元后放量滞涨，或5日资金由净流入转为持续净流出。</dd><dt>失效条件</dt><dd>收盘有效跌破MA60约35.53元，或安全事故与收购执行出现新的重大不利信息。</dd><dt>风险</dt><dd>子公司安全事故仍需跟踪，收购控制权及海外项目存在执行不确定性。</dd></dl></div>
<div class="stock"><div><h3>盛达资源 000603</h3><span class="pill">69.3 · 逢回调观察</span><p class="note">StockScore 81.2｜风险扣5分｜置信度92%</p></div><dl><dt>逻辑</dt><dd>半年报业绩、鸿林矿业投产与银都矿业技改构成硬催化，但当前价格已反映较多预期。</dd><dt>关键事实</dt><dd>2026H1营收约11.52亿元、归母净利润约3.90亿元；近20日涨48.64%，当日主力净流出约1.41亿元，5/20日仍为净流入。</dd><dt>观察条件</dt><dd>优先等待32.4—34.0元区域止跌；需要缩量回踩后收盘企稳，且后续资金重新转为净流入。</dd><dt>减仓触发</dt><dd>接近布林上轨40.86元后出现放量长上影，或连续两日资金流出并跌破短期平台。</dd><dt>失效条件</dt><dd>收盘有效跌破MA20约32.39元且5日资金转为净流出，或投产与技改进度低于公告预期。</dd><dt>风险</dt><dd>20日涨幅和换手率较高，近期多次异动公告，当日资金已出现边际转弱。</dd></dl></div>
<div class="grid g3"><div class="panel"><b>华钰矿业 601020</b><p>60.0分。技术位置和多周期资金较温和，但控制权变化、总经理离任及高管减持计划带来10分风险扣分。</p></div><div class="panel"><b>白银有色 601212</b><p>54.6分。评分日涨停、偏离MA20约27.22%，TTM归母净利润为负，资金强度不能覆盖盈利与过热风险。</p></div><div class="panel"><b>宜安科技 300328</b><p>52.7分。医疗镁材料有进展，但2026H1亏损、计提减值且收盘高于布林上轨，暂不入榜。</p></div></div><p class="note">行情、技术和资金来自WeStock，估值来自hithink-finance；财务、公告和研报为截至评分日可获得的最新披露。评分只用于同一候选池的相对排序。</p></section>
<section id="risks" class="section card strategy"><div class="kicker">05 / risk control</div><h2>风险提示</h2><ul><li>工业金属拥挤度五日上升46.22，涨幅和交易热度加速后，追价面临波动放大风险。</li><li>两只入榜股票同属一个方向，行业相关性高；若金属价格和板块资金同步回落，不能视为分散配置。</li><li>市场成交仅为20日均量79.43%，指数反弹若缺少量能跟进，主线可能快速轮动。</li><li>白银有色和宜安科技的盈利质量与短期趋势不匹配，初筛靠前不等于通过深度核验。</li><li>全球风险、目标日两融和股债风险溢价分位缺失，市场环境置信度仅74%，未将缺失解释为低风险。</li></ul><p class="disclaimer"><b>免责声明</b>：以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。任何投资决策应结合个人风险承受能力、资金状况和投资目标独立判断，必要时咨询持牌专业机构。过往表现不预示未来收益。</p></section>
<details id="methodology"><summary>方法与数据降级说明</summary><p>市场环境=30%指数与风格+25%宽度与情绪+20%成交与流动性+15%国内宏观+10%全球风险。本期55.8，状态中性。</p><p>行业P与F按1/5/20日加权；29行业横截面回归提取正交资金R，T=70%×P+30%×R；板块热度再扣最高20分拥挤惩罚。个股最终分=15%×市场环境+25%×板块热度+60%×六维个股分-风险扣分。</p><p>非趋势行业分项、全球风险、两融与股债风险溢价存在缺失，按规范降级并降低置信度。8月27日盘中截面不回填8月26日评分。</p></details>
</main>
<footer class="footer">数据来源：WeStock、hithink-finance、公司公告、公开报道复核 ｜ 评分交易日：2026-08-26 ｜ 证据台账：2026-08-26-evidence.md</footer>
</body>
</html>
'''

mobile = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="2026年8月26日A股盘后研究日报移动版">
<title>股市老黄历｜2026-08-26</title>
<style>
:root{--m-paper:#f7f3ea;--m-ink:#18332d;--m-body:#26332f;--m-jade:#17705e;--m-red:#a83e32;--m-gold:#b98532;--m-line:#e3ddcf;--m-muted:#7a7568;--m-card:#fffdf7;--serif:STSong,"Songti SC",SimSun,serif;--sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}*{box-sizing:border-box}body{margin:0;background:#e6e0d2;color:var(--m-body);font:15px/1.68 var(--sans)}.m-shell{max-width:460px;margin:0 auto;background:var(--m-paper);padding-bottom:28px}.m-top{background:var(--m-ink);color:#f8f2e5;padding:16px;border-bottom:3px solid var(--m-gold)}.m-top-row{display:flex;align-items:center;gap:10px}.m-seal{width:30px;height:30px;display:grid;place-items:center;border:1px solid #c99d55;color:#e8c887;font:700 17px var(--serif)}.m-top strong{font:700 18px var(--serif)}.m-top small{display:block;color:#c9d2ca;font-size:10px}.m-badge{margin-left:auto;color:#e6d4ad;border:1px solid rgba(232,200,135,.45);padding:3px 7px;font-size:11px}.m-cover{padding:18px 16px 14px;border-bottom:1px solid var(--m-line)}.m-date,.m-kicker{color:var(--m-gold);font-size:10px;font-weight:700;letter-spacing:.12em}.m-cover h1{margin:8px 0;font:700 30px/1.25 var(--serif);color:var(--m-ink)}.m-cover h1 strong,.up{color:var(--m-red)}.down{color:var(--m-jade)}.m-ritual{display:flex;gap:8px;font-size:13px}.m-ritual span{border:1px solid var(--m-line);padding:5px 8px;background:#fffaf0}.m-state{margin-top:12px;background:var(--m-ink);color:#f8f2e5;padding:12px;border-left:4px solid var(--m-gold)}.m-state h2{margin:0;color:#e8c887;font:700 20px var(--serif)}.m-state p{margin:4px 0 0;color:#d7ddd4;font-size:13px}.m-sec{margin:14px 12px 0;background:var(--m-card);border:1px solid var(--m-line);padding:14px}.m-sec h2{margin:3px 0 10px;color:var(--m-ink);font:700 23px var(--serif)}.m-line-item,.m-kv{display:flex;gap:10px;justify-content:space-between;padding:6px 0;border-bottom:1px dashed var(--m-line)}.m-kv{align-items:flex-start}.k{color:var(--m-muted);min-width:70px}.m-stock{border-top:3px solid var(--m-gold);padding-top:11px;margin-top:12px}.m-stock h3{margin:0 0 7px;color:var(--m-ink);font:700 20px var(--serif)}.tagline{float:right;color:var(--m-red);font:700 13px var(--sans)}.m-advice{margin:9px 0;padding:9px;background:#f1eadc;border-left:4px solid var(--m-red);font-weight:700}.m-note,.m-footer{color:var(--m-muted);font-size:12px}.m-risk{border-left:4px solid var(--m-red)}.m-list{margin:0;padding-left:20px}.m-footer{text-align:center;padding:18px 12px}details{margin:14px 12px 0;background:#eee8dc;border:1px solid var(--m-line);padding:12px}summary{font-weight:700;color:var(--m-ink)}
</style>
</head>
<body>
<div class="m-shell">
<header class="m-top"><div class="m-top-row"><span class="m-seal">历</span><div><strong>股市老黄历</strong><small>A-SHARE DAILY</small></div><span class="m-badge">盘后 · V2</span></div></header>
<header id="cover" class="m-cover"><div class="m-date">评分交易日 2026-08-26</div><h1>今日 <strong>缩量反弹，先等回调</strong></h1><div class="m-ritual"><span><b>宜</b>等均线确认</span><span><b>忌</b>追加速段</span></div><div class="m-state"><h2>中性 · 两只条件观察</h2><p>环境分55.8。29个行业中仅工业金属达到65分门槛，但拥挤正在加速。</p></div><p class="m-note">标题仅为包装，正文为数据研究。</p></header>
<section id="executive-summary" class="m-sec"><div class="m-kicker">00 / brief</div><h2>行情摘要</h2><div class="m-line-item"><span class="k">市场</span><span>中性 55.8</span></div><div class="m-line-item"><span class="k">宽度</span><span>涨2946 / 跌2448</span></div><div class="m-line-item"><span class="k">成交</span><span>18087亿元，缩量</span></div><div class="m-line-item"><span class="k">板块</span><span>工业金属 69.04</span></div><div class="m-line-item"><span class="k">入榜</span><span>2只条件观察</span></div><p><b>仅供研究参考，不构成投资建议。</b></p></section>
<section id="macro" class="m-sec"><div class="m-kicker">01 / macro</div><h2>宏观大势</h2><div class="m-kv"><span class="k">流动性</span><span>8月26日公开市场净投放2395亿元，短端资金环境偏宽松。</span></div><div class="m-kv"><span class="k">货币</span><span>7月M1同比4.0%、M2同比7.7%，企业资金活化仍需观察。</span></div><div class="m-kv"><span class="k">外部</span><span>全球风险指标缺失，按中性处理，不代表低风险。</span></div></section>
<section id="market" class="m-sec"><div class="m-kicker">02 / market</div><h2>大盘判断</h2><div class="m-line-item"><span class="k">上证</span><span>3912.52 <span class="up">+0.59%</span></span></div><div class="m-line-item"><span class="k">深证</span><span>13841.33 <span class="up">+0.69%</span></span></div><div class="m-line-item"><span class="k">创业板</span><span>3414.88 <span class="up">+0.51%</span></span></div><p>上涨占比53.08%，但成交只有20日均量79.43%。结论是缩量修复，不是全面进攻。</p></section>
<section id="sectors" class="m-sec"><div class="m-kicker">03 / sectors</div><h2>板块观察</h2><div class="m-stock"><h3>工业金属<span class="tagline">69.04 · 达标</span></h3><div class="m-kv"><span class="k">量价</span><span>价格P=92.68，独立资金R=82.14，资金确认较强。</span></div><div class="m-kv"><span class="k">广度</span><span>成份股上涨占比91.53%，1/5/20日收益均为正。</span></div><div class="m-kv"><span class="k">拥挤</span><span>C=70.67，五日上升46.22，扣15.31分。</span></div><div class="m-kv"><span class="k">结论</span><span>趋势仍强，但拥挤升温且加速，等回调不追价。</span></div></div><p class="m-note">汽车零部件63.70、消费电子63.28，均未达到65分门槛。</p></section>
<section id="picks" class="m-sec"><div class="m-kicker">04 / picks</div><h2>核心选股</h2><div class="m-stock"><h3>兴业银锡 000426<span class="tagline">70.3</span></h3><div class="m-kv"><span class="k">逻辑</span><span>盈利、银锡价格弹性和中期资金结构较强。</span></div><div class="m-kv"><span class="k">关键事实</span><span>2026Q1归母净利约13.38亿元；5日和20日资金仍为净流入。</span></div><div class="m-advice">当前建议：回调确认，不追价。</div><div class="m-kv"><span class="k">观察确认</span><span>回踩20日线附近缩量企稳，随后资金重新转入。</span></div><div class="m-kv"><span class="k">减仓触发</span><span>冲高放量滞涨，或5日资金持续转为净流出。</span></div><div class="m-kv"><span class="k">失效条件</span><span>收盘跌破60日线，或安全事故与收购出现重大不利变化。</span></div><div class="m-kv"><span class="k">风险</span><span>安全事故进展、收购与海外项目执行不确定性。</span></div></div><div class="m-stock"><h3>盛达资源 000603<span class="tagline">69.3</span></h3><div class="m-kv"><span class="k">逻辑</span><span>半年报业绩、矿山投产与技改形成硬催化。</span></div><div class="m-kv"><span class="k">关键事实</span><span>2026H1归母净利约3.90亿元；中期资金仍为净流入。</span></div><div class="m-advice">当前建议：逢回调观察。</div><div class="m-kv"><span class="k">观察确认</span><span>回踩20日线附近缩量企稳，资金重新转入。</span></div><div class="m-kv"><span class="k">减仓触发</span><span>高位放量长上影，或连续资金流出。</span></div><div class="m-kv"><span class="k">失效条件</span><span>跌破20日线且5日资金转为净流出，或项目进度低于预期。</span></div><div class="m-kv"><span class="k">风险</span><span>20日涨幅较大、异动公告较多、当日资金转弱。</span></div></div><p class="m-note">华钰矿业、白银有色、宜安科技因治理、盈利或过热风险未入榜。</p></section>
<section id="risks" class="m-sec m-risk"><div class="m-kicker">05 / risk</div><h2>风险提示</h2><ul class="m-list"><li>工业金属拥挤五日快速升温。</li><li>两只入榜股票同一方向，相关性高。</li><li>市场缩量，板块轮动可能加快。</li><li>全球风险与目标日两融数据缺失。</li></ul><p><b>免责声明</b>：以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。任何投资决策应结合个人风险承受能力、资金状况和投资目标独立判断，必要时咨询持牌专业机构。过往表现不预示未来收益。</p></section>
<details id="methodology"><summary>方法与数据说明</summary><p>29行业横截面提取正交资金R，板块热度再扣最高20分拥挤惩罚。个股最终分由市场、板块、六维个股分和风险扣分组成。8月27日盘中数据未回填8月26日评分。</p></details>
<footer class="m-footer">数据来源：WeStock、hithink-finance、公司公告<br>评分日2026-08-26｜仅供研究参考</footer>
</div>
</body>
</html>
'''

note = r'''# 8月26日A股复盘：缩量反弹，别追工业金属

今天三大指数同步收涨：上证+0.59%、深证+0.69%、创业板+0.51%。上涨2946家、下跌2448家，但两市成交18087亿元，只到20日均量的79.43%。

今日宜：等均线与资金确认。
今日忌：把缩量反弹当成全面进攻。

**重点方向：工业金属**
29个申万二级行业做量价正交后，工业金属热度69.04分，达到65分门槛。独立资金残差分位82.14，说明资金确认较强；但拥挤度升至70.67，五日增加46.22，已出现拥挤升温和加速，当前位置更适合等回调。

**兴业银锡 000426**
逻辑：盈利、银锡价格弹性和中期资金结构较强。
建议：回踩20日线附近缩量企稳，且资金重新转入后再观察。
失效：收盘跌破60日线，或安全事故与收购出现重大不利变化。

**盛达资源 000603**
逻辑：半年报业绩、矿山投产与技改形成公司公告确认的催化。
建议：等待20日线附近止跌，避免在加速段追价。
失效：跌破20日线且5日资金转为净流出，或项目进度低于预期。

**风险提醒**
1. 两只股票同属工业金属，方向相关性高。
2. 板块拥挤五日快速升温，波动可能放大。
3. 全球风险和目标日两融数据缺失，市场环境置信度为74%。

仅供研究参考，不构成投资建议。市场有风险，投资需谨慎，过往表现不预示未来收益。

#A股 #财经 #股票复盘 #每日复盘 #行业研究
'''

evidence = r'''# 2026-08-26 股市老黄历证据台账

- 评分交易日：2026-08-26，盘后。
- 时区：Asia/Shanghai。
- 产物：桌面HTML、移动HTML、小红书笔记。
- 核心原则：结构化行情和财务优先；公开检索只作定性复核；冲突并列披露；缺失不补造。

## 一、市场环境

MarketEnvironment = 55.8，状态为中性。

| 维度 | 分数 | 权重 | 加权贡献 | 关键依据 |
|---|---:|---:|---:|---|
| 指数与风格趋势 | 52.0 | 30% | 15.6 | 三大指数日内同步上涨，20日趋势仍正；60日趋势偏弱，短期价值占优 |
| 市场宽度和情绪 | 70.0 | 25% | 17.5 | 上涨2946、下跌2448、涨停51、跌停1；多周期新高数均高于新低数 |
| 成交与流动性 | 45.0 | 20% | 9.0 | 两市成交18087.23亿元，为20日均值79.43% |
| 国内宏观流动性 | 58.0 | 15% | 8.7 | 7月M1同比4.0%、M2同比7.7%；8月26日公开市场净投放2395亿元 |
| 全球风险 | 50.0 | 10% | 5.0 | 缺少同一时点可审计的VIX、美元、美债和海外指数数据，按中性降级 |

计算：0.30×52.0 + 0.25×70.0 + 0.20×45.0 + 0.15×58.0 + 0.10×50.0 = 55.8。

市场环境有效权重74.0%，置信度C。结论是“缩量反弹、宽度改善，但长周期趋势和量能仍弱”。

### 指数与宽度

- 上证指数3912.52，+0.59%；5日+0.46%、20日+2.20%、60日-3.99%，高于MA20、低于MA60。
- 深证成指13841.33，+0.69%；5日-0.35%、20日+1.34%、60日-11.22%。
- 创业板指3414.88，+0.51%；5日-1.69%、20日+1.07%、60日-15.80%。
- 主口径：上涨2946、下跌2448、平盘156、涨停51、跌停1，上涨占比53.08%。
- 新高/新低：5日2183/359，10日970/270，20日661/90，60日167/15，120日36/13，250日24/11。

## 二、V2行业横截面

- 分类体系：申万二级行业，样本29个。
- 行业日K覆盖率：100%。
- 回归：enabled=true，sample_size=29，coverage=100%，alpha=-6.8465e-17，beta=0.7009782911。

公式：

```text
P = 20%×P1 + 35%×P5 + 45%×P20
F = 20%×F1 + 35%×F5 + 45%×F20
zF = α + β×zP + ε
R = ε的横截面百分位
T = 70%×P + 30%×R
SectorHeat = CoreHeat + 20 - CrowdPenalty
```

行业催化与基本面/估值分项缺少29行业统一、可审计横截面，输入按50分降级，不代表看空。

## 三、板块结果

| 排名 | 行业 | P | F | R | T | C | ΔC5 | 拥挤扣分 | SectorHeat | 结论 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 工业金属 | 92.68 | 89.64 | 82.14 | 89.52 | 70.67 | +46.22 | 15.31 | 69.04 | 正式入选；资金确认强，但拥挤升温且加速 |
| 2 | 汽车零部件 | 49.82 | 78.21 | 100.00 | 64.88 | 23.16 | +4.06 | 3.71 | 63.70 | 资金先行，价格未确认 |
| 3 | 消费电子 | 56.43 | 64.29 | 75.00 | 62.00 | 25.51 | -7.43 | 4.08 | 63.28 | 未过线 |
| 4 | 电力 | 39.11 | 45.54 | 57.14 | 44.52 | 32.43 | -13.04 | 5.19 | 61.02 | 未过线 |
| 5 | 光伏设备 | 62.86 | 45.89 | 17.86 | 49.36 | 20.58 | +1.83 | 3.29 | 59.50 | 正交资金偏弱 |

工业金属原始周期数据：1日收益+3.333865%、5日+5.532577%、20日+7.817260%；1/5/20日资金强度分别+9.36%、+4.08%、+0.095%；成份股上涨广度91.53%。

拥挤分项：RSI历史分位61.57、换手率分位40.91、成交占比分位92.15；C=70.67，ΔC5=+46.22，水平扣分11.31、加速度扣分4.00。

## 四、工业金属候选池

- 原始成份股60只。
- 沪深A股59只；北交所1只排除。
- 硬过滤后45只。
- 候选池40只。
- 深度核验前5只：白银有色601212、盛达资源000603、兴业银锡000426、宜安科技300328、华钰矿业601020。

硬过滤：仅沪深A股；排除ST、*ST和S类；评分日有收盘且历史交易日不少于60日；20日成交额中位数不低于1亿元。

## 五、个股深度核验与评分

最终分公式：

```text
FinalScore = 15%×55.8 + 25%×69.0383 + 60%×StockScore - RiskPenalty
```

| 股票 | 基本面 | 技术 | 资金 | 相对强度 | 催化 | 流动性 | StockScore | 风险扣分 | FinalScore | 置信度 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 兴业银锡 000426 | 88 | 78 | 75 | 89 | 82 | 95 | 82.8 | 5 | 70.3 | 89% | 入榜，回调确认 |
| 盛达资源 000603 | 85 | 70 | 72 | 96 | 90 | 93 | 81.2 | 5 | 69.3 | 92% | 入榜，逢回调观察 |
| 华钰矿业 601020 | 65 | 78 | 88 | 84 | 55 | 50 | 74.0 | 10 | 60.0 | 84% | 治理风险未消化 |
| 白银有色 601212 | 35 | 55 | 92 | 98 | 60 | 68 | 65.0 | 10 | 54.6 | 84% | 过热且盈利不匹配 |
| 宜安科技 300328 | 25 | 62 | 85 | 95 | 65 | 45 | 61.8 | 10 | 52.7 | 91% | 亏损、减值与过热 |

### 兴业银锡 000426

- 2026-08-26收盘40.13元，+1.88%；近5日+11.94%、20日+24.47%。
- 2026Q1营收约21.30亿元、归母净利润约13.38亿元；PE-TTM约27.72倍、PB约6.83倍。
- 当日主力净流出约0.93亿元，5/20日分别净流入约12.19亿元和7.38亿元。
- 公司公告显示子公司安全事故仍在处理；收购控制权与海外项目存在执行风险，扣5分。

### 盛达资源 000603

- 2026-08-26收盘37.16元，+2.45%；近5日+18.76%、20日+48.64%。
- 2026H1营收约11.52亿元、归母净利润约3.90亿元；PE-TTM约31.47倍、PB约7.14倍。
- 鸿林矿业正式投产、银都矿业90万吨/年采矿技改获核准，均由公司公告确认。
- 当日主力净流出约1.41亿元，5/20日仍净流入；近期多次异动公告，扣5分。

### 华钰矿业 601020

- 2026-08-26收盘22.29元，+2.25%；高于MA20约3.86%，位置相对温和。
- TTM归母净利润约8.56亿元；PE-TTM约21.89倍、PB约4.36倍。
- 1/5/20日主力资金均净流入。
- 控制权变更、总经理离任和高管减持计划形成治理折价，扣10分。

### 白银有色 601212

- 2026-08-26收盘7.24元，涨停；近5日+34.07%、20日+47.76%。
- 收盘高于MA20约27.22%，RSI14约75并高于布林上轨。
- 1/5/20日主力资金均净流入，但TTM归母净利润约-5.61亿元；PE-TTM为负。
- 异常波动、短期偏离和盈利质量风险合计扣10分。

### 宜安科技 300328

- 2026-08-26收盘17.33元，+8.04%；近5日+22.82%、20日+40.55%。
- 2026H1营收约7.99亿元、归母净利润约-5293万元；PE-TTM为负，PB约11.40倍。
- 医疗镁材料有公告进展，但同时披露资产减值及核销。
- 半年报亏损、减值和高于布林上轨合计扣10分。

## 六、证据等级与来源

- 一手或准一手：公司财报、公司公告、交易所披露。用于确认业绩、投产、技改、收购和风险。
- 结构化第三方：WeStock行情、技术、资金、市场总览；hithink-finance估值与涨停池。数据时点为2026-08-26收盘或对应财报期。
- 非一手：券商研报摘要、财经媒体和agentic_search结果，只作定性佐证，需核实原文。
- 评分原始文件：`evidence/2026-08-26-market-score.json`、`evidence/2026-08-26-sector-score-v2.json`、`evidence/2026-08-26-stock-candidates.json`、`evidence/2026-08-26-stock-deep-summary.json`。

## 七、降级、冲突与未决限制

- 8月27日12:27附近的实时市场截面属于错时点，未回填8月26日评分。
- 涨停家数存在WeStock 51只与hithink 52只的供应商口径差异，主评分采用带日期市场总览51只。
- 全球风险、目标日两融和股债风险溢价分位缺失，按中性降级，不代表低风险。
- 行业催化和基本面统一横截面缺失，按50分处理。
- 北交所1只工业金属成份股资金接口不支持，未补造；最终候选限制为沪深A股。
- agentic_search曾返回错日或错市场混杂内容，已排除；评分数值只使用本地可审计结构化字段。

## 八、小红书发布前自检

- 移动端HTML与笔记未写个股精确买入、止盈或止损价格。
- 正文可见位置保留“仅供研究参考，不构成投资建议”。
- 未使用收益承诺、绝对化预测、指令性买卖、导流或诱导互动话术。
- 个股仍保留观察确认、减仓触发和失效条件。
- 本期仅生成与预审，不触发外部发布。
'''

(OUT / "2026-08-26-stock-almanac.html").write_text(desktop, encoding="utf-8")
(OUT / "2026-08-26-stock-almanac-mobile.html").write_text(mobile, encoding="utf-8")
(OUT / "2026-08-26-xiaohongshu-note.md").write_text(note, encoding="utf-8")
(OUT / "2026-08-26-evidence.md").write_text(evidence, encoding="utf-8")
print("generated:")
for name in ["2026-08-26-stock-almanac.html", "2026-08-26-stock-almanac-mobile.html", "2026-08-26-xiaohongshu-note.md", "2026-08-26-evidence.md"]:
    print(OUT / name)
