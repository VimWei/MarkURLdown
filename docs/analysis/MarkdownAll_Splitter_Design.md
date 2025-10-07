# MarkdownAll Splitter 设计规范

## 基于 MdxScraper 分析的设计原则

### 1. 核心设计原则
- **Command Panel**: 固定 120px 高度，永不改变
- **Tab 区域**: 可调整，记住用户设置
- **Log 区域**: 可拉伸，自动填充剩余空间

### 2. 技术实现规范

#### 2.1 初始配置
```python
def _configure_splitter(self):
    """Configure splitter behavior (完全模仿MdxScraper)."""
    # 初始尺寸: [Tab, Command, Log]
    self.splitter.setSizes([220, 120, 260])
    
    # 拉伸因子配置
    self.splitter.setStretchFactor(0, 0)  # Tab 区域: 不拉伸
    self.splitter.setStretchFactor(1, 0)  # Command Panel: 不拉伸  
    self.splitter.setStretchFactor(2, 1)  # Log 区域: 可拉伸
    
    # 防止折叠
    self.splitter.setChildrenCollapsible(False)
    
    # 连接移动信号
    self.splitter.splitterMoved.connect(self._on_splitter_moved)
```

#### 2.2 Command Panel 固定高度
```python
# 在 CommandPanel 构造函数中
self.setFixedHeight(120)  # 固定高度
self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 垂直固定
```

#### 2.3 ShowEvent 处理
```python
def _on_show_event(self, event):
    """窗口显示时强制配置 Splitter (模仿MdxScraper)."""
    super().showEvent(event)
    QTimer.singleShot(50, self._force_splitter_config)

def _force_splitter_config(self):
    """强制配置 Splitter 行为 (模仿MdxScraper)."""
    current_sizes = self.splitter.sizes()
    current_tab_height = current_sizes[0]
    
    # 记住 Tab 高度
    self.remembered_tab_height = current_tab_height
    
    # 计算新尺寸
    window_height = self.height()
    tab_height = current_tab_height
    command_height = 120  # 固定
    log_height = window_height - tab_height - command_height - 32
    
    # 确保最小 Log 高度
    if log_height < 150:
        log_height = 150
    
    # 强制设置尺寸
    self.splitter.setSizes([tab_height, command_height, log_height])
    
    # 重新配置拉伸因子
    self.splitter.setStretchFactor(0, 0)  # Tab 固定
    self.splitter.setStretchFactor(1, 0)  # Command 固定
    self.splitter.setStretchFactor(2, 1)  # Log 可拉伸
    
    # 强化记忆
    QTimer.singleShot(10, self._reinforce_splitter_memory)
```

#### 2.4 记忆强化机制
```python
def _reinforce_splitter_memory(self):
    """强化 Splitter 的记忆 (模仿MdxScraper)."""
    current_sizes = self.splitter.sizes()
    
    # 如果 Tab 高度偏离记忆值，强制恢复
    if (hasattr(self, "remembered_tab_height") and 
        current_sizes[0] != self.remembered_tab_height):
        
        window_height = self.height()
        tab_height = self.remembered_tab_height
        command_height = 120  # 固定
        log_height = window_height - tab_height - command_height - 32
        
        if log_height < 150:
            log_height = 150
        
        # 强制设置尺寸
        self.splitter.setSizes([tab_height, command_height, log_height])
        
        # 重新应用拉伸因子
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setStretchFactor(2, 1)
```

#### 2.5 Splitter 移动处理
```python
def _on_splitter_moved(self, pos, index):
    """处理 Splitter 移动事件 (模仿MdxScraper)."""
    # 主要依靠 showEvent 和记忆强化机制
    # 这里可以添加额外的保护逻辑
    pass
```

## 实现步骤

### 1. 移除所有自定义设置
- 移除复杂的尺寸限制
- 移除额外的保护机制
- 使用 MdxScraper 的精确配置

### 2. 实现 MdxScraper 的精确逻辑
- 复制 `_on_show_event` 方法
- 复制 `_force_splitter_config` 方法  
- 复制 `_reinforce_splitter_memory` 方法

### 3. 确保 Command Panel 设置正确
- 构造函数中设置 `setFixedHeight(120)`
- 设置 `QSizePolicy.Fixed` 垂直策略

### 4. 连接必要信号
- `splitterMoved` 信号连接
- `showEvent` 重写

## 预期效果

1. **Command Panel**: 始终保持 120px 高度
2. **Tab 区域**: 可以调整，系统记住用户设置
3. **Log 区域**: 自动填充剩余空间
4. **布局稳定**: 与 MdxScraper 完全一致的行为

## 关键差异

### MdxScraper 的成功要素
1. **简单配置**: 只使用必要的设置
2. **记忆机制**: 记住用户调整的 Tab 高度
3. **强制配置**: 窗口显示时重新配置
4. **持续监控**: 通过记忆强化保持布局

### 避免的错误
1. **过度配置**: 不要添加不必要的设置
2. **复杂逻辑**: 不要发明新的保护机制
3. **尺寸限制**: 不要设置过多的最小尺寸
4. **信号处理**: 不要过度处理 splitter 移动事件

## 总结

MarkdownAll 的 Splitter 设计应该完全模仿 MdxScraper 的成功模式，使用相同的配置、相同的处理逻辑、相同的行为模式。这样可以确保布局的稳定性和用户体验的一致性。
