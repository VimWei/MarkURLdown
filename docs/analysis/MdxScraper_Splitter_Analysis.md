# MdxScraper Splitter 运作机制分析

## 概述

MdxScraper 使用了一个复杂的 Splitter 系统来管理三个主要区域的布局：
1. **Tab 区域** (顶部) - 包含所有功能页面
2. **Command Panel** (中间) - 固定高度的控制面板
3. **Log Panel** (底部) - 可拉伸的日志区域

## 核心设计原则

### 1. 固定高度原则
- **Command Panel**: 始终固定 120px 高度，永不改变
- **Tab 区域**: 初始固定，但允许用户调整
- **Log 区域**: 可拉伸，填充剩余空间

### 2. 记忆机制
- 系统会"记住"用户调整的 Tab 区域高度
- 窗口缩放时保持用户偏好的 Tab 高度
- Command Panel 高度永远不变

## 技术实现

### 1. 初始配置
```python
# 创建垂直 Splitter
self.splitter = QSplitter(Qt.Vertical, self)

# 添加三个组件
self.splitter.addWidget(self.tabs)           # Tab 区域 (index 0)
self.splitter.addWidget(self.command_panel)  # Command Panel (index 1)  
self.splitter.addWidget(self.log_panel)      # Log 区域 (index 2)

# 初始尺寸配置
self.splitter.setSizes([220, 120, 260])  # [Tab, Command, Log]

# 拉伸因子配置
self.splitter.setStretchFactor(0, 0)  # Tab 区域: 不拉伸
self.splitter.setStretchFactor(1, 0)  # Command Panel: 不拉伸
self.splitter.setStretchFactor(2, 1)  # Log 区域: 可拉伸

# 防止折叠
self.splitter.setChildrenCollapsible(False)

# 连接移动信号
self.splitter.splitterMoved.connect(self.on_splitter_moved)
```

### 2. Command Panel 固定高度
```python
# CommandPanel 构造函数中设置
self.setFixedHeight(120)  # 固定高度
self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 垂直方向固定
```

### 3. ShowEvent 处理机制
```python
def _on_show_event(self, event):
    """窗口显示时强制配置 Splitter"""
    super().showEvent(event)
    QTimer.singleShot(50, self._force_splitter_config)

def _force_splitter_config(self):
    """强制配置 Splitter 行为"""
    # 获取当前尺寸
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

### 4. 记忆强化机制
```python
def _reinforce_splitter_memory(self):
    """强化 Splitter 的记忆"""
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

### 5. Splitter 移动处理
```python
def on_splitter_moved(self, pos, index):
    """处理 Splitter 移动事件"""
    # 这个方法在 MdxScraper 中似乎没有具体实现
    # 主要依靠 showEvent 和记忆强化机制来维持布局
```

## 关键特性

### 1. 三层保护机制
1. **初始配置**: 设置正确的拉伸因子和尺寸
2. **ShowEvent 强制**: 窗口显示时强制重新配置
3. **记忆强化**: 持续监控和纠正布局

### 2. 智能尺寸计算
- **Tab 高度**: 记住用户调整的值
- **Command 高度**: 固定 120px
- **Log 高度**: 自动计算剩余空间，最小 150px

### 3. 防折叠保护
- `setChildrenCollapsible(False)`: 防止组件被完全隐藏
- `setFixedHeight(120)`: Command Panel 固定高度
- `QSizePolicy.Fixed`: 垂直方向不拉伸

## 布局行为

### 1. 初始状态
- Tab: 220px
- Command: 120px (固定)
- Log: 260px

### 2. 用户调整后
- Tab: 用户调整的高度 (被记住)
- Command: 120px (永远不变)
- Log: 剩余空间 (最小 150px)

### 3. 窗口缩放时
- Tab: 保持记忆的高度
- Command: 120px (永远不变)
- Log: 自动调整填充剩余空间

## 设计优势

1. **用户体验**: Command Panel 始终在固定位置，操作一致
2. **布局稳定**: Tab 区域高度被记住，不会意外改变
3. **空间利用**: Log 区域自动填充剩余空间
4. **防误操作**: 多层保护机制防止布局被破坏

## 总结

MdxScraper 的 Splitter 系统是一个精心设计的布局管理机制，通过多层保护、记忆机制和智能计算，实现了稳定可靠的用户界面布局。其核心思想是保持 Command Panel 的固定性，同时允许用户自定义 Tab 区域高度，并让 Log 区域自动适应剩余空间。
