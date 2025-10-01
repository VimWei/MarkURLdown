# 爬虫框架设计指南

本指南基于实际开发经验，总结了爬虫框架的设计理念、技术选择策略和实际开发经验，为爬虫技术的选择和实现提供参考。

## 目录

1. [设计原则](#设计原则)
2. [实际开发经验](#实际开发经验)
3. [技术选择策略](#技术选择策略)
4. [内联实现模式](#内联实现模式)
5. [通用类 vs 内联实现对比](#通用类-vs-内联实现对比)
6. [未来扩展策略](#未来扩展策略)

## 设计原则

### 1. 功能职责优先
- **原则**：站点处理器按功能命名（`zhihu_handler.py`），技术实现作为内部细节
- **原因**：让开发者专注于解决特定网站的问题，而不是技术实现细节
- **实现**：每个处理器文件专注于一个网站或一类网站的处理逻辑

### 2. 实用主义优先
- **原则**：优先解决实际问题，避免过度设计
- **原因**：爬虫技术变化快，过度抽象可能适得其反
- **实现**：根据实际需求选择技术方案，而不是追求完美的架构

### 3. 多策略容错
- **原则**：每个站点处理器内部实现多种技术策略，失败时自动回退
- **原因**：网站的反爬虫机制复杂多变，单一策略容易失败
- **实现**：按优先级排序多种策略，失败时自动尝试下一个

### 4. 渐进式升级
- **原则**：先实现基础功能，再逐步添加高级特性
- **原因**：爬虫开发需要不断调试和优化，渐进式开发更容易控制
- **实现**：从简单的HTTP请求开始，逐步添加浏览器自动化、反检测等功能

## 实际开发经验

### 重要发现：通用crawler类 vs 内联实现

经过实际开发发现，虽然设计了通用的crawler类（`BaseCrawler`、`PlaywrightCrawler`、`HttpxCrawler`），但在实际使用中，站点处理器都选择了内联实现。原因如下：

#### ✅ 内联实现的优势

**1. 完全定制化**
- 每个网站的反爬虫机制都不同，需要特定的参数配置
- 可以针对特定网站进行深度优化
- 避免了通用类的参数传递复杂性

**2. 性能更好**
- 减少函数调用开销
- 避免过度抽象带来的性能损失
- 直接调用底层API，效率更高

**3. 代码更直观**
- 易于理解和维护
- 调试更方便，问题定位更准确
- 减少了抽象层次，代码逻辑更清晰

**4. 灵活性更高**
- 可以随时调整策略和参数
- 不受通用类接口的限制
- 更容易适应网站的变化

#### ❌ 通用crawler类的问题

**1. 定制化需求太强**
- 每个网站需要不同的浏览器参数、请求头、地理位置等
- 通用类难以满足所有特殊需求
- 参数配置变得非常复杂

**2. 过度抽象**
- 为了支持所有特殊情况，类会变得非常复杂
- 抽象层次过多，增加了理解和维护成本
- 可能引入不必要的复杂性

**3. 参数传递繁琐**
- 失去了灵活性，反而增加了复杂性
- 参数传递链过长，容易出错
- 难以处理动态变化的参数需求

#### 🎯 推荐做法

**1. 保留crawler类**
- 作为未来扩展的基础，可能用于通用场景
- 为简单的爬虫需求提供快速解决方案
- 作为学习和参考的模板

**2. 优先使用内联实现**
- 针对特定网站的实际需求
- 在处理器内部直接实现爬虫逻辑
- 根据网站特点定制化配置

**3. 复用技术逻辑**
- 虽然内联实现，但可以复用技术思路和数据结构
- 保持统一的数据结构（如`CrawlerResult`）
- 复用通用的工具函数和辅助方法

## 技术选择策略

### 爬虫技术对比

| 技术 | 适用场景 | 优势 | 劣势 | 推荐度 |
|------|----------|------|------|--------|
| **Playwright** | 复杂反爬虫场景 | 功能强大，反检测能力强 | 资源消耗大，速度慢 | ⭐⭐⭐⭐⭐ |
| **httpx** | 现代化HTTP请求 | 支持HTTP/2，性能好 | 功能相对简单 | ⭐⭐⭐⭐ |
| **Requests** | 简单HTTP请求 | 轻量级，易用 | 功能有限，易被检测 | ⭐⭐⭐ |
| **代理池** | 避免IP封禁 | 提高成功率 | 成本高，维护复杂 | ⭐⭐⭐⭐ |
| **缓存机制** | 减少重复请求 | 优化性能 | 需要存储空间 | ⭐⭐⭐⭐ |
| **API服务** | 高可靠性需求 | 最稳定 | 成本高，依赖第三方 | ⭐⭐⭐ |

### 技术选择原则

#### 1. 按复杂度选择
```python
# 推荐的技术选择顺序
crawler_strategies = [
    # 策略1: 轻量级 - 最快，适合大多数网站
    lambda: _try_lightweight_strategy(url, session),
    
    # 策略2: 增强策略 - 功能完整，处理复杂情况
    lambda: _try_enhanced_strategy(url, session),
    
    # 策略3: 备用策略 - 最后手段，确保有结果
    lambda: _try_fallback_strategy(url, session),
]
```

#### 2. 按网站特点选择
- **简单网站**：httpx + MarkItDown
- **中等复杂度**：Playwright + 基础反检测
- **高复杂度**：Playwright + 深度反检测 + 行为模拟

#### 3. 按成功率要求选择
- **高成功率要求**：多策略 + 代理池 + 缓存
- **一般要求**：多策略容错
- **快速原型**：单一策略

## 内联实现模式

### 基本结构

```python
def fetch_site_article(session, url: str) -> FetchResult:
    """站点文章获取 - 多策略尝试"""
    
    # 定义多策略爬虫，按优先级排序
    crawler_strategies = [
        lambda: _try_lightweight_strategy(url, session),
        lambda: _try_enhanced_strategy(url, session),
        lambda: _try_fallback_strategy(url, session),
    ]
    
    # 多策略尝试，每个策略最多重试2次
    max_retries = 2
    
    for i, strategy in enumerate(crawler_strategies, 1):
        for retry in range(max_retries):
            try:
                result = strategy()
                if result.success and _is_valid_content(result.text_content, result.title):
                    return result
                # 重试逻辑...
            except Exception as e:
                # 错误处理...
                continue
    
    raise Exception("所有策略都失败")
```

### 策略实现示例

#### 1. 轻量级策略
```python
def _try_lightweight_strategy(url: str, session) -> CrawlerResult:
    """策略1: 轻量级策略 - 使用MarkItDown，速度快"""
    try:
        from markitdown import MarkItDown
        
        md = MarkItDown(enable_plugins=False, requests_session=session)
        result = md.convert(url)
        
        title = getattr(result, "title", None) or None
        text = result.text_content if getattr(result, "text_content", None) else str(result)
        
        return CrawlerResult(success=True, title=title, text_content=text)
    except Exception as e:
        return CrawlerResult(success=False, title=None, text_content="", error=str(e))
```

#### 2. 增强策略
```python
def _try_enhanced_strategy(url: str, session) -> CrawlerResult:
    """策略2: 增强策略 - 使用Playwright，处理复杂网站"""
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # 针对特定网站定制浏览器参数
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-first-run',
                    '--no-default-browser-check',
                    # 根据网站特点添加特定参数
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                # 根据网站特点添加特定配置
            )
            
            page = context.new_page()
            page.goto(url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(2000)
            
            html = page.content()
            title = page.title()
            
            browser.close()
            return CrawlerResult(success=True, title=title, text_content=html)
            
    except Exception as e:
        return CrawlerResult(success=False, title=None, text_content="", error=str(e))
```

#### 3. 备用策略
```python
def _try_fallback_strategy(url: str, session) -> CrawlerResult:
    """策略3: 备用策略 - 直接httpx，最后手段"""
    try:
        import httpx
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            # 根据网站特点添加特定请求头
        }
        
        with httpx.Client(headers=headers, timeout=30.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            
            title = extract_title_from_html(response.text)
            return CrawlerResult(success=True, title=title, text_content=response.text)
        
    except Exception as e:
        return CrawlerResult(success=False, title=None, text_content="", error=str(e))
```

## 通用类 vs 内联实现对比

### 通用类模式

#### 优势
- **代码复用**：多个处理器可以共享相同的爬虫逻辑
- **统一接口**：所有爬虫都使用相同的接口
- **易于测试**：可以独立测试爬虫类
- **文档完整**：有明确的API文档

#### 劣势
- **过度抽象**：为了支持所有场景，类变得复杂
- **参数传递繁琐**：需要传递大量参数
- **定制化困难**：难以满足特殊需求
- **维护成本高**：修改影响多个处理器

### 内联实现模式

#### 优势
- **完全定制化**：可以针对特定网站深度优化
- **性能更好**：减少函数调用开销
- **代码直观**：逻辑清晰，易于理解
- **灵活性高**：可以随时调整策略

#### 劣势
- **代码重复**：相似逻辑可能重复实现
- **维护分散**：修改需要在多个地方进行
- **测试复杂**：需要测试整个处理器
- **文档分散**：逻辑分散在多个文件中

### 推荐策略

**🎯 混合使用策略：**

1. **简单场景使用通用类**
   - 对于功能简单的爬虫需求
   - 快速原型开发
   - 学习和参考用途

2. **复杂场景使用内联实现**
   - 需要深度定制的网站
   - 性能要求高的场景
   - 特殊反爬虫机制

3. **保持统一的数据结构**
   - 使用统一的`CrawlerResult`等数据结构
   - 复用通用的工具函数
   - 保持一致的错误处理方式

## 未来扩展策略

### 1. 代理池支持

```python
def _try_enhanced_strategy_with_proxy(url: str, session) -> CrawlerResult:
    """增强策略 - 使用Playwright + 代理池"""
    try:
        from playwright.sync_api import sync_playwright
        
        # 从代理池获取代理
        proxy = get_proxy_from_pool()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                proxy=proxy,  # 使用代理
                args=[...]
            )
            # ... 其他逻辑
    except Exception as e:
        return CrawlerResult(success=False, title=None, text_content="", error=str(e))
```

### 2. 缓存机制

```python
def _try_cached_strategy(url: str, session) -> CrawlerResult:
    """缓存策略 - 减少重复请求"""
    try:
        # 检查缓存
        cached_result = get_from_cache(url)
        if cached_result:
            return cached_result
        
        # 执行爬虫逻辑
        result = _try_lightweight_strategy(url, session)
        
        # 保存到缓存
        if result.success:
            save_to_cache(url, result)
        
        return result
    except Exception as e:
        return CrawlerResult(success=False, title=None, text_content="", error=str(e))
```

### 3. 智能重试

```python
def _try_with_smart_retry(strategy_func, url: str, session, max_retries: int = 3) -> CrawlerResult:
    """智能重试策略"""
    for attempt in range(max_retries):
        try:
            result = strategy_func(url, session)
            if result.success:
                return result
            
            # 根据错误类型调整重试策略
            if "timeout" in str(result.error):
                time.sleep(2 ** attempt)  # 指数退避
            elif "403" in str(result.error):
                time.sleep(random.uniform(5, 10))  # 随机等待
            else:
                time.sleep(1)
                
        except Exception as e:
            if attempt == max_retries - 1:
                return CrawlerResult(success=False, title=None, text_content="", error=str(e))
            time.sleep(1)
    
    return CrawlerResult(success=False, title=None, text_content="", error="Max retries exceeded")
```

### 4. 性能监控

```python
def _try_with_monitoring(strategy_func, url: str, session) -> CrawlerResult:
    """带性能监控的策略"""
    start_time = time.time()
    
    try:
        result = strategy_func(url, session)
        
        # 记录性能指标
        duration = time.time() - start_time
        log_performance_metrics(url, strategy_func.__name__, duration, result.success)
        
        return result
    except Exception as e:
        duration = time.time() - start_time
        log_performance_metrics(url, strategy_func.__name__, duration, False)
        raise
```

## 最佳实践总结

### ✅ 推荐做法

1. **内联实现优先** - 针对特定需求深度优化
2. **多策略容错** - 提高成功率和稳定性
3. **渐进式开发** - 从简单策略开始，逐步增强
4. **统一数据结构** - 使用一致的接口和错误处理
5. **详细日志记录** - 便于调试和监控
6. **性能监控** - 跟踪爬虫性能和成功率

### ❌ 避免做法

1. **过度抽象** - 避免为了复用而过度设计
2. **单一策略** - 容易失败，缺乏容错能力
3. **忽略定制化** - 每个网站都有特殊需求
4. **无监控机制** - 难以发现和解决问题
5. **硬编码参数** - 应该根据网站特点动态调整

### 🎯 开发建议

1. **先分析再实现** - 深入了解目标网站的特点
2. **从简单开始** - 先实现基础功能，再添加高级特性
3. **持续优化** - 根据实际使用情况不断改进
4. **保持简洁** - 避免不必要的复杂性
5. **文档完善** - 记录设计决策和实现细节

---

本指南基于实际开发经验总结，为爬虫技术选择和实现提供实用的参考。随着技术发展，本指南将持续更新和完善。
