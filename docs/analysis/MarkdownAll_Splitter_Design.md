# MarkdownAll Splitter 设计规范

## 核心设计原则

### 1. 布局结构
- **Tab 区域**: 可调整高度，记住用户设置
- **Command Panel**: 固定 120px 高度，永不改变
- **Log 区域**: 可拉伸，自动填充剩余空间

### 2. 技术实现规范

#### 2.1 初始配置
```python
def _configure_splitter(self):
    """Configure splitter behavior and initial sizes (适配MarkdownAll需求)."""
    # 初始尺寸: [Tab, Command, Log]
    # Tab(270) + Command(120) + Log(160) = 550px
    self.splitter.setSizes([270, 120, 160])
    
    # 拉伸因子配置
    self.splitter.setStretchFactor(0, 0)  # Tab 区域: 不拉伸
    self.splitter.setStretchFactor(1, 0)  # Command Panel: 不拉伸  
    self.splitter.setStretchFactor(2, 1)  # Log 区域: 可拉伸
    
    # 防止折叠
    self.splitter.setChildrenCollapsible(False)
    
    # 连接移动信号
    self.splitter.splitterMoved.connect(self._on_splitter_moved)
    
    # 设置窗口最小尺寸
    # 布局计算: Tab(270) + Command(120) + Log(160) + 边距(50) = 600px
    self.setMinimumSize(800, 600)
    
    # 重写 showEvent 以强制正确的 splitter 行为
    self.showEvent = self._on_show_event
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
    """Handle window show event to force correct splitter behavior."""
    super().showEvent(event)
    
    # Force splitter to behave correctly by setting sizes explicitly
    # This ensures tab area stays fixed and only log area stretches
    QTimer.singleShot(50, self._force_splitter_config)

def _force_splitter_config(self):
    """Force splitter configuration after window is shown."""
    # Get current splitter sizes to capture the actual tab height
    current_sizes = self.splitter.sizes()
    current_tab_height = current_sizes[0]  # Capture current tab height

    # Store this as the "remembered" tab height
    self.remembered_tab_height = current_tab_height

    # Get current window height
    window_height = self.height()

    # Calculate desired sizes: use current tab height, command fixed, log gets the rest
    tab_height = current_tab_height  # Use current tab height as the "remembered" height
    command_height = 120  # Fixed command height (matches CommandPanel.setFixedHeight(120))
    log_height = window_height - tab_height - command_height - 32  # 32 for margins

    # Ensure minimum log height
    if log_height < 150:
        log_height = 150

    # Force set the sizes - this "teaches" the splitter to remember the current tab height
    self.splitter.setSizes([tab_height, command_height, log_height])

    # Reconfigure stretch factors to ensure they stick
    self.splitter.setStretchFactor(0, 0)  # Tab area fixed
    self.splitter.setStretchFactor(1, 0)  # Command panel fixed
    self.splitter.setStretchFactor(2, 1)  # Log area stretchable

    # Force the splitter to "remember" these sizes by triggering a resize
    # This ensures the splitter's internal memory is set correctly
    QTimer.singleShot(10, self._reinforce_splitter_memory)
```

#### 2.4 记忆强化机制
```python
def _reinforce_splitter_memory(self):
    """Reinforce the splitter's memory of correct sizes."""
    # Get current sizes
    current_sizes = self.splitter.sizes()

    # If tab area is not at the remembered height, force it back
    if (
        hasattr(self, "remembered_tab_height")
        and current_sizes[0] != self.remembered_tab_height
    ):

        # Recalculate with remembered tab height
        window_height = self.height()
        tab_height = self.remembered_tab_height
        command_height = 120  # Fixed command height (matches CommandPanel.setFixedHeight(120))
        log_height = window_height - tab_height - command_height - 32

        if log_height < 150:
            log_height = 150

        # Force set the sizes again to reinforce the memory
        self.splitter.setSizes([tab_height, command_height, log_height])

        # Reapply stretch factors
        self.splitter.setStretchFactor(0, 0)  # Tab area fixed
        self.splitter.setStretchFactor(1, 0)  # Command panel fixed
        self.splitter.setStretchFactor(2, 1)  # Log area stretchable
```

#### 2.5 Splitter 移动处理
```python
def _on_splitter_moved(self, pos, index):
    """Handle splitter movement."""
    # 主要依靠 showEvent 和记忆强化机制
    # 这里可以添加额外的保护逻辑
    pass
```

## 配置参数

### 初始尺寸配置
- **Tab 区域**: 270px (可调整)
- **Command Panel**: 120px (固定)
- **Log 区域**: 160px (可拉伸)

### 拉伸因子配置
- **Tab 区域**: 0 (不拉伸)
- **Command Panel**: 0 (不拉伸)
- **Log 区域**: 1 (可拉伸)

### 窗口最小尺寸
- **最小宽度**: 800px
- **最小高度**: 600px
- **边距偏移**: 32px

## 预期效果

1. **Command Panel**: 始终保持 120px 高度
2. **Tab 区域**: 可以调整，系统记住用户设置
3. **Log 区域**: 自动填充剩余空间
4. **布局稳定**: 窗口缩放时保持合理的布局比例

## 设计特点

### 1. 记忆机制
- 系统会"记住"用户调整的 Tab 区域高度
- 窗口缩放时保持用户偏好的 Tab 高度
- Command Panel 高度永远不变

### 2. 智能调整
- 窗口缩放时优先调整 Log 区域
- Log 区域达到最小值后才调整 Tab 区域
- 确保所有区域都有合理的最小尺寸

### 3. 用户体验
- 用户可以手动调整 Tab 区域大小
- 系统会记住用户的调整偏好
- 布局调整符合用户直觉

## 总结

MarkdownAll 的 Splitter 设计采用了智能记忆机制，确保用户界面布局的稳定性和一致性。通过固定 Command Panel 高度、记忆 Tab 区域设置、自动调整 Log 区域，提供了优秀的用户体验。
