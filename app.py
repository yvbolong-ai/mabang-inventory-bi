import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ============ 页面配置 ============
st.set_page_config(
page_title="马帮库存智能分析",
page_icon="📊",
layout="wide",
initial_sidebar_state="expanded"
)

# ============ 自定义样式 ============
st.markdown("""
<style>
.main-header { font-size: 2rem; font-weight: bold; color: #1f77b4; }
</style>
""", unsafe_allow_html=True)

# ============ 数据处理函数 ============
def process_excel(uploaded_file):
"""处理上传的Excel文件"""
# 读取文件
if uploaded_file.name.endswith('.csv'):
for enc in ['utf-8', 'gbk', 'gb2312']:
try:
df = pd.read_csv(uploaded_file, encoding=enc)
break
except:
continue
else:
df = pd.read_excel(uploaded_file)

# 自动识别列名映射
col_mapping = {}
for col in df.columns:
c = str(col).lower().replace(' ', '').replace('_', '')

if any(x in c for x in ['sku', '编码', '编号', '货号']):
col_mapping[col] = 'sku'
elif any(x in c for x in ['名称', '品名', '中文', '商品名']):
col_mapping[col] = 'sku_name'
elif any(x in c for x in ['仓库', '仓', '库房']):
col_mapping[col] = 'warehouse'
elif any(x in c for x in ['当前库存', '库存数量', '可用库存', '现货']):
col_mapping[col] = 'current_stock'
elif any(x in c for x in ['在途', '途中', '采购在途']):
col_mapping[col] = 'in_transit'
elif any(x in c for x in ['7天销量', '7日销量', 'sales7', '7天']):
col_mapping[col] = 'sales_7d'
elif any(x in c for x in ['14天销量', '14日销量', 'sales14', '14天']):
col_mapping[col] = 'sales_14d'
elif any(x in c for x in ['28天销量', '30天销量', 'sales28', 'sales30', '28天', '30天']):
col_mapping[col] = 'sales_28d'

# 重命名列
df = df.rename(columns=col_mapping)

# 确保数值类型
for col in ['current_stock', 'in_transit', 'sales_7d', 'sales_14d', 'sales_28d']:
if col in df.columns:
if df[col].dtype == 'object':
df[col] = df[col].astype(str).str.replace(',', '').str.replace('，', '')
df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# 填充缺失列
if 'in_transit' not in df.columns:
df['in_transit'] = 0
if 'sku_name' not in df.columns:
df['sku_name'] = df['sku']
if 'warehouse' not in df.columns:
df['warehouse'] = '默认仓库'

# 计算衍生字段
df['total_available'] = df['current_stock'] + df['in_transit']
df['avg_daily'] = df['sales_7d'] / 7
df['stock_days'] = df.apply(
lambda x: x['total_available'] / x['avg_daily'] if x['avg_daily'] > 0 else 999,
axis=1
)

return df

# ============ 主程序 ============
def main():
# 头部
st.markdown('<p class="main-header">📦 马帮库存智能分析系统</p>', unsafe_allow_html=True)
st.caption(f"数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ============ 侧边栏配置 ============
with st.sidebar:
st.markdown("## ⚙️ 分析配置")

logistics_days = st.number_input(
"⏱️ 物流天数",
min_value=1, max_value=180, value=50,
help="从下单到入库的平均天数"
)

safety_days = st.number_input(
"🛡️ 安全库存天数",
min_value=1, max_value=30, value=7,
help="缓冲天数，应对销量波动"
)

urgent_threshold = st.number_input(
"🔴 紧急预警阈值(天)",
min_value=1, max_value=30, value=7
)

warning_threshold = st.number_input(
"🟡 警告阈值(天)",
min_value=1, max_value=60, value=15
)

config = {
'logistics': logistics_days,
'safety': safety_days,
'urgent': urgent_threshold,
'warning': warning_threshold
}

# ============ 文件上传 ============
st.markdown("### 📤 上传马帮库存Excel")

uploaded_file = st.file_uploader(
"拖拽文件到此处，或点击选择",
type=['xlsx', 'xls', 'csv'],
help="支持 .xlsx, .xls, .csv 格式"
)

if uploaded_file is None:
st.info("👆 请先上传马帮导出的库存Excel文件")

with st.expander("📖 查看支持的Excel格式"):
st.markdown("""
**系统会自动识别以下列名（包含关键词即可）：**

| 必需列 | 可选列 |
|-------|-------|
| SKU/商品编码/货号 | 商品名称/中文名称 |
| 仓库/仓库名称 | 在途量/在途库存 |
| 当前库存/库存数量 | 可售天数（会自动计算） |
| 7天销量/近7天 | 14天销量/近14天 |
| | 28天销量/近30天 |
""")
return

# ============ 数据处理 ============
try:
with st.spinner("正在解析数据..."):
df = process_excel(uploaded_file)

st.success(f"✅ 成功加载 **{len(df)}** 个SKU数据")

# 数据预览
with st.expander("🔍 查看原始数据预览"):
st.dataframe(df.head(20), use_container_width=True)

except Exception as e:
st.error(f"❌ 文件解析失败: {str(e)}")
st.info("请确保Excel文件包含SKU、仓库、库存数量等基本信息")
return

# ============ KPI指标卡 ============
st.markdown("---")

# 计算KPI
total_sku = len(df)
total_stock = df['current_stock'].sum()
total_intransit = df['in_transit'].sum()
urgent_count = len(df[df['stock_days'] < config['urgent']])
warning_count = len(df[(df['stock_days'] >= config['urgent']) & (df['stock_days'] < config['warning'])])

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
st.metric("📦 总SKU数", f"{total_sku:,}")
with col2:
st.metric("📊 总库存量", f"{total_stock:,.0f}")
with col3:
st.metric("🚚 在途量", f"{total_intransit:,.0f}")
with col4:
st.metric("🔴 紧急补货", f"{urgent_count}",
delta=f"{urgent_count/total_sku*100:.1f}%" if total_sku > 0 else "0%")
with col5:
st.metric("🟡 需关注", f"{warning_count}")

# ============ 标签页内容 ============
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📈 销量分析", "📊 库存分布", "🚨 补货清单"])

# ===== Tab 1: 销量分析 =====
with tab1:
st.markdown("### 📈 销量趋势分析")

col1, col2 = st.columns(2)

with col1:
# TOP20 SKU销量对比
top_df = df.nlargest(20, 'sales_7d')

fig = go.Figure()
fig.add_trace(go.Bar(
name='7天销量',
x=top_df['sku'],
y=top_df['sales_7d'],
marker_color='#3498db'
))
fig.add_trace(go.Bar(
name='14天销量',
x=top_df['sku'],
y=top_df['sales_14d'],
marker_color='#2ecc71'
))
fig.add_trace(go.Bar(
name='28天销量',
x=top_df['sku'],
y=top_df['sales_28d'],
marker_color='#9b59b6'
))

fig.update_layout(
title="TOP20 SKU 销量对比",
barmode='group',
height=400,
xaxis_tickangle=-45
)
st.plotly_chart(fig, use_container_width=True)

with col2:
# 销量速度散点图
fig = px.scatter(
df.head(100),
x='avg_daily',
y='stock_days',
size='total_available',
color='sales_7d',
hover_data=['sku', 'sku_name', 'warehouse'],
title="销量速度 vs 可售天数（气泡=库存量）",
color_continuous_scale='Viridis'
)
fig.update_layout(height=400)
st.plotly_chart(fig, use_container_width=True)

# 销量明细表
with st.expander("📋 查看销量明细"):
display_df = df[['sku', 'sku_name', 'warehouse', 'sales_7d', 'sales_14d', 'sales_28d', 'avg_daily']].copy()
display_df['avg_daily'] = display_df['avg_daily'].round(2)
display_df = display_df.sort_values('sales_7d', ascending=False)
st.dataframe(display_df, use_container_width=True)

# ===== Tab 2: 库存分布 =====
with tab2:
st.markdown("### 📊 库存分布分析")

col1, col2 = st.columns(2)

with col1:
# 仓库分布饼图
wh_dist = df.groupby('warehouse')['current_stock'].sum().reset_index()
wh_dist = wh_dist[wh_dist['current_stock'] > 0]

fig = px.pie(
wh_dist,
values='current_stock',
names='warehouse',
title="库存仓库分布",
hole=0.4
)
fig.update_layout(height=350)
st.plotly_chart(fig, use_container_width=True)

with col2:
# 可售天数分布
def categorize(days):
if days < config['urgent']:
return '🔴 紧急(<7天)'
elif days < config['warning']:
return '🟡 警告(7-15天)'
elif days < 30:
return '🟢 正常(15-30天)'
else:
return '💎 充足(>30天)'

df['stock_category'] = df['stock_days'].apply(categorize)
dist = df.groupby('stock_category').size().reset_index(name='sku_count')

# 按顺序排序
order = ['🔴 紧急(<7天)', '🟡 警告(7-15天)', '🟢 正常(15-30天)', '💎 充足(>30天)']
dist['sort_key'] = dist['stock_category'].map({k: i for i, k in enumerate(order)})
dist = dist.sort_values('sort_key')

colors = {'🔴 紧急(<7天)': '#ff6b6b', '🟡 警告(7-15天)': '#ffd93d',
'🟢 正常(15-30天)': '#6bcf7f', '💎 充足(>30天)': '#4ecdc4'}

fig = px.bar(
dist,
x='stock_category',
y='sku_count',
color='stock_category',
color_discrete_map=colors,
title="可售天数分布"
)
fig.update_layout(height=350, showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# 库存健康度指标
col3, col4, col5 = st.columns(3)

healthy_rate = len(df[df['stock_days'] >= config['warning']]) / len(df) * 100
stockout_risk = len(df[df['stock_days'] < 7]) / len(df) * 100
avg_days = df['stock_days'].mean()

with col3:
st.metric("✅ 健康库存占比", f"{healthy_rate:.1f}%")
with col4:
st.metric("⚠️ 断货风险SKU", f"{stockout_risk:.1f}%")
with col5:
st.metric("📊 平均可售天数", f"{avg_days:.1f}天")

# ===== Tab 3: 补货清单 =====
with tab3:
st.markdown("### 🚨 智能补货建议")

# 计算建议补货量
df['suggested_qty'] = df.apply(
lambda x: max(0, int((config['logistics'] + config['safety']) * x['avg_daily'] - x['total_available'])),
axis=1
)

# 优先级
df['priority'] = df['stock_days'].apply(
lambda x: 'P0-紧急' if x < config['urgent'] else ('P1-高' if x < config['warning'] else 'P2-中')
)

# 筛选需要补货的
replenish_df = df[df['suggested_qty'] > 0].copy()

if replenish_df.empty:
st.success("✅ 恭喜！所有SKU库存充足，暂无补货需求！")
else:
# 统计
total_to_replenish = replenish_df['suggested_qty'].sum()
urgent_replenish = replenish_df[replenish_df['priority'] == 'P0-紧急']['suggested_qty'].sum()

col1, col2, col3 = st.columns(3)
with col1:
st.metric("需补货SKU数", len(replenish_df))
with col2:
st.metric("建议补货总量", f"{total_to_replenish:,.0f} 件")
with col3:
st.metric("其中紧急补货", f"{urgent_replenish:,.0f} 件")

st.markdown("---")

# 导出按钮
export_df = replenish_df[[
'priority', 'sku', 'sku_name', 'warehouse',
'current_stock', 'in_transit', 'total_available',
'avg_daily', 'stock_days', 'suggested_qty'
]].copy()

export_df['avg_daily'] = export_df['avg_daily'].round(2)
export_df['stock_days'] = export_df['stock_days'].round(1)

csv = export_df.to_csv(index=False, encoding='utf-8-sig')

col_dl1, col_dl2 = st.columns([1, 3])
with col_dl1:
st.download_button(
label="📥 导出补货清单(CSV)",
data=csv,
file_name=f"补货清单_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
mime="text/csv",
use_container_width=True
)

# 按优先级筛选显示
priority_filter = st.multiselect(
"筛选优先级",
options=['P0-紧急', 'P1-高', 'P2-中'],
default=['P0-紧急', 'P1-高', 'P2-中']
)

filtered = replenish_df[replenish_df['priority'].isin(priority_filter)]

# 显示表格
display_cols = ['priority', 'sku', 'sku_name', 'warehouse',
'current_stock', 'avg_daily', 'stock_days', 'suggested_qty']

st.dataframe(
filtered[display_cols].sort_values(['priority', 'stock_days']),
use_container_width=True,
height=500
)

# 按仓库汇总
st.markdown("### 📊 按仓库汇总")
wh_summary = replenish_df.groupby('warehouse').agg({
'sku': 'count',
'suggested_qty': 'sum'
}).reset_index()
wh_summary.columns = ['仓库', '需补货SKU数', '建议补货总量']
st.dataframe(wh_summary, use_container_width=True)

# ============ 运行 ============
if __name__ == "__main__":
main()
