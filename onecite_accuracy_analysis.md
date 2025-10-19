# OneCite 文本查询 vs DOI查询准确率分析报告

## 📊 测试结果对比

| 查询方式 | 准确率 | 测试样本数 | 错误数 |
|---------|--------|-----------|--------|
| **文本查询** | ~40% (13/33) | 33条 | 20条 |
| **DOI查询** | 100% (21/21) | 21条 | 0条 |

---

## 🔍 错误原因深度分析

### 1. 模糊匹配评分算法的权重问题

**位置**: `pipeline.py` 第1200-1500行 `_score_candidates()` 函数

#### 当前权重分配（期刊文章）：
```python
match_score = (
    scores['title'] * 0.40 +      # 标题: 40%
    scores['author'] * 0.30 +     # 作者: 30%
    scores['year'] * 0.10 +       # 年份: 10% ⚠️ 太低！
    scores['venue'] * 0.10 +      # 期刊: 10%
    scores['source'] * 0.05 +     # 数据源: 5%
    scores['citations'] * 0.03 +  # 引用数: 3%
    scores['domain'] * 0.02       # 领域加分: 2%
)
```

#### 问题：
- **年份权重只有10%**，即使年份完全不对，只要标题和作者相似，总分仍然很高
- 例如：查询"AbouZahr 2005"，找到"AbouZahr 2010"
  - title匹配: 65分 × 40% = 26分
  - author匹配: 80分 × 30% = 24分
  - year不匹配: 0分 × 10% = 0分
  - **总分**: 50+ 分，仍然被选中 ❌

---

### 2. 年份容差过大

**代码位置**: `pipeline.py` 第1750行左右

```python
if candidate.get('year') and query_year:
    year_diff = abs(candidate_year - query_year)
    if year_diff == 0:
        year_score = 100  # 完全匹配
    elif year_diff <= 2:
        year_score = 70   # ⚠️ 差2年还给70分！
    elif year_diff <= 5:
        year_score = 30   # ⚠️ 差5年还给30分！
```

#### 实际案例：
- **Aqil 2016** → 实际是2009年，差7年，但仍被匹配（因其他字段相似）
- **Hellerstein 2012** → 找到2004年版，差8年
- **Oppenheimer 2003** → 找到2002年文章，差1年但给了70分

---

### 3. 书籍版本识别问题更严重

**代码位置**: `pipeline.py` 第1820行左右

```python
if is_candidate_book:
    # 书籍特定权重
    match_score = (
        scores['title'] * 0.45 +
        scores['author'] * 0.30 +
        scores['year'] * 0.02 +    # ⚠️ 年份权重只有2%！
        scores['venue'] * 0.05 +
        scores['source'] * 0.08 +
        scores['citations'] * 0.02 +
        scores['domain'] * 0.08
    )
```

#### 问题：
代码认为**书籍有多个版本和重印**，所以几乎忽略年份：
- 年份权重只有**2%** ❌
- 没有单独的"版本号"匹配逻辑
- 结果：找错版本

#### 实际案例：
- **Kurose 2021 (8th ed)** → 找到2017年版
- **Ramalho 2022 (2nd ed)** → 找到2015年第1版
- **Little & Rubin 2019 (3rd ed)** → 找到2014年版

---

### 4. 多数据源混合查询导致误匹配

**代码位置**: `pipeline.py` 第1400-1500行 `_fuzzy_search()` 函数

```python
if is_medical:
    # 医学路径：查询多个数据库
    pubmed_results = self._search_pubmed(query_string)      # 返回5-15条
    crossref_results = self._search_crossref(query_string)  # 返回15条
    semantic_results = self._search_semantic_scholar(...)   # 返回5条
    
    candidates.extend(pubmed_results)
    candidates.extend(crossref_results)
    candidates.extend(semantic_results)
    # 总共可能有30-40个候选！
```

#### 问题：
1. 多个API返回**几十个候选结果**
2. 只要有一个候选与查询"足够相似"，就可能被错误选中
3. 相似作者名的文章特别容易混淆

#### 灾难性案例：
**Sterne 2009 BMJ "Multiple imputation for missing data"**
- 目标：J.A.C. Sterne 的流行病学文章
- 实际找到：**Laurence Sterne** 的18世纪信件集！
- 原因：作者姓氏完全匹配（Sterne），其他字段模糊匹配给了分数

---

### 5. CrossRef查询策略的广撒网问题

**代码位置**: `pipeline.py` 第1734行 `_search_crossref()` 函数

```python
# 尝试多个查询策略
search_strategies = [
    params,  # 标准查询
    {**params, 'query.author': query.split('.')[0]},  # 重点查作者
    {**params, 'filter': 'type:journal-article,proceedings-article,book-chapter,book,monograph'}
]

for i, strategy_params in enumerate(search_strategies):
    # 每个策略返回15条
    response = requests.get(url, params=strategy_params, timeout=15)
    # ...
```

#### 问题：
- 使用3种不同策略查询
- 每种策略返回15条结果
- 总共可能获得**45个候选**
- 然后只靠模糊评分从45个中选1个 → 容易选错

---

### 6. WHO文档识别失败

#### 案例：
- **WHO 2017 DQR: A modular approach** → 找成2022年儿童药物清单
- **WHO 2018 DQR Toolkit** → 找成2022年儿童药物清单

#### 原因：
1. WHO文档可能没有标准DOI
2. CrossRef中WHO条目混杂，容易匹配到其他WHO出版物
3. 标题相似度不够高时，算法"瞎猜"最高分的

---

## ✅ DOI查询为什么100%准确？

**代码位置**: `pipeline.py` 第226-265行

```python
def _identify_single_entry(self, raw_entry, interactive_callback):
    # 如果有DOI，优先验证
    if raw_entry.get('doi'):
        if self._validate_doi(raw_entry['doi']):
            # 直接调用CrossRef API验证DOI
            real_metadata = self._verify_doi_and_get_metadata(raw_entry['doi'])
            if real_metadata:
                # ✅ 直接返回，不走模糊匹配！
                identified_entry['doi'] = raw_entry['doi']
                identified_entry['metadata'] = real_metadata
                identified_entry['status'] = 'identified'
                return identified_entry
    
    # 只有没有DOI时，才走模糊搜索
    return self._fuzzy_search(raw_entry, interactive_callback)
```

### DOI查询流程：
1. 验证DOI格式（正则表达式）
2. 直接调用 `https://api.crossref.org/works/{DOI}`
3. 返回该DOI的**唯一、精确元数据**
4. **完全跳过模糊匹配和评分算法**
5. 结果：100%准确！

### 与文本查询的对比：

| 步骤 | DOI查询 | 文本查询 |
|------|---------|----------|
| 1. 查询范围 | 1个精确DOI | 30-45个模糊候选 |
| 2. 匹配方式 | 精确匹配 | 模糊评分 |
| 3. 结果数量 | 1条（唯一） | 选最高分的1条 |
| 4. 准确率 | 100% | ~40% |

---

## 📋 错误案例汇总

### 找错的20条引用：

| # | 原始引用 | 找到的结果 | 错误类型 |
|---|---------|-----------|---------|
| 1 | AbouZahr 2005, WHO Bulletin | AbouZahr 2010, 其他期刊 | 年份错误 |
| 2 | Aqil 2016, PRISM | Bawo 2016 | 完全错误的文章 |
| 3 | Baker 2016, 1500 scientists | Baker 2016, Digital badges | 同年同作者但不同文章 |
| 4 | Gimbel 2017, Sofala | Wagenaar 2015 | 年份+作者都错 |
| 5 | Hellerstein 2012 | 2004年版 | 书籍版本错误 |
| 6 | Hong 2017, digital divide | Hong Kong老年护理 | 主题完全不对 |
| 7 | IETF RFC 9110 | RFC 9245 | 文档编号错误 |
| 8 | Kurose 2021 8th ed | 2017年版 | 书籍版本错误 |
| 9 | Kyomba 2022, 10th Ebola | Akilimali 2024 | 年份+主题偏差 |
| 10 | Little 2019 3rd ed | 2014年版 | 书籍版本错误 |
| 11 | Maina 2019 DHIS2 | 疟疾RDT文章 | 主题完全不对 |
| 12 | Mars 2013 Telemedicine | 心血管疾病 | 主题完全不对 |
| 13 | Moucheraud 2017 Malawi | Pimmer 2017 mobile | 年份对但主题不对 |
| 14 | Mutale 2013 | Hirschhorn 2013 | 年份对但作者不对 |
| 15 | Oppenheimer 2003 | 2002年文章 | 年份差1年 |
| 16 | Ramalho 2022 2nd ed | 2015年第1版 | 书籍版本错误 |
| 17 | Sterne 2009 BMJ | 18世纪信件集！ | ⚠️ 灾难性错误 |
| 18 | Wilkinson 2016 FAIR | Dumontier 2022 | 年份+作者都错 |
| 19 | WHO 2017 DQR | 2022儿童药物清单 | 完全不相关 |
| 20 | WHO 2018 DQR Toolkit | 2022儿童药物清单 | 完全不相关 |

---

## 💡 改进建议

### 1. 增加年份权重（关键）
```python
# 现在
scores['year'] * 0.10  # 期刊文章

# 建议
scores['year'] * 0.25  # 提高到25%
```

### 2. 缩小年份容差
```python
# 现在
if year_diff == 0: year_score = 100
elif year_diff <= 2: year_score = 70   # 太宽松
elif year_diff <= 5: year_score = 30   # 太宽松

# 建议
if year_diff == 0: year_score = 100
elif year_diff == 1: year_score = 30   # 严格
else: year_score = 0                    # 差2年以上直接0分
```

### 3. 书籍版本识别
```python
# 添加版本号提取和匹配
def extract_edition(text):
    match = re.search(r'(\d+)(?:st|nd|rd|th)?\s*ed', text, re.I)
    return int(match.group(1)) if match else None

# 在评分时增加版本号权重
if query_edition and candidate_edition:
    if query_edition == candidate_edition:
        edition_score = 100
    else:
        edition_score = 0  # 版本号不对直接0分
```

### 4. 减少候选数量
```python
# 现在：每个策略15条，3个策略 = 45条
'rows': limit  # limit = 15

# 建议：减少到每个策略5条
'rows': 5
```

### 5. 提高匹配阈值
```python
# 现在
if best_candidate['match_score'] >= 80:  # 自动采纳
    ...
elif 70 <= best_candidate['match_score'] < 80:  # 交互模式
    ...

# 建议
if best_candidate['match_score'] >= 90:  # 提高到90
    ...
elif 80 <= best_candidate['match_score'] < 90:  # 交互阈值提高
    ...
```

### 6. 优先使用DOI！
**最佳实践**：
- 在文献列表中尽可能提供DOI
- DOI查询准确率100%，远超文本查询
- 对于书籍和WHO文档等无DOI的，需要手动验证

---

## 🎯 结论

### 核心问题：
OneCite的模糊匹配算法在以下场景容易失败：
1. **年份不精确**的查询（权重太低）
2. **书籍版本**查询（几乎忽略年份）
3. **同名作者**的不同文献（如Sterne案例）
4. **相似主题**的文献（如DHIS2相关文章互相混淆）

### 解决方案：
- **短期**：使用DOI进行查询（准确率100%）
- **长期**：改进算法（提高年份权重、增加版本号匹配、减少候选数量）

### 测试数据：
- 文本查询准确率：**39% (13/33)**
- DOI查询准确率：**100% (21/21)**
- **建议优先使用DOI！**

---

**报告生成时间**: 2025-10-18  
**测试版本**: OneCite 0.0.11  
**分析人**: automation Assistant

