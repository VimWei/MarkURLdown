# Splitter 联动机制设计（模仿 MdxScraper）

## 概述

模仿 MdxScraper 的成功设计，实现 Tab 区域、Command 面板和 Log 区域的智能联动机制，提供优秀的用户体验。

## 核心设计理念

1. **Command 面板固定**：始终保持 120px 高度，位置不变
2. **Log 区域优先**：窗口缩放时优先调整 Log 区域
3. **Tab 区域跟随**：Log 区域达到最小值后才调整 Tab 区域
4. **手动调整支持**：用户可以手动调整 Tab 区域大小

## 技术实现

### Splitter 配置

```python
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QSplitter

class MainWindow(QMainWindow):
    def __init__(self, project_root: Path):
        # ... 其他初始化代码 ...
        
        # Create splitter for tabs, command panel and log areas
        self.splitter = QSplitter(Qt.Vertical, self)
        
        # Add widgets to splitter
        self.splitter.addWidget(self.tabs)           # Tab area (index 0)
        self.splitter.addWidget(self.command_panel)  # Command panel (index 1)
        self.splitter.addWidget(self.log_panel)      # Log area (index 2)
        
        # Configure splitter behavior (模仿 MdxScraper)
        self.splitter.setSizes([300, 120, 150])  # Initial proportions
        self.splitter.setStretchFactor(0, 0)    # Tab area: not stretchable
        self.splitter.setStretchFactor(1, 0)    # Command panel: fixed
        self.splitter.setStretchFactor(2, 1)    # Log area: stretchable
        self.splitter.setChildrenCollapsible(False)  # Prevent collapse
        
        # Connect splitter moved signal
        self.splitter.splitterMoved.connect(self.on_splitter_moved)
        
        # Override showEvent to force correct splitter behavior
        self.showEvent = self._on_show_event
```

### 最小尺寸限制（基于实际代码数据）

```python
def on_splitter_moved(self, pos: int, index: int):
    """Enforce minimum sizes when splitter is moved (模仿 MdxScraper)"""
    sizes = self.splitter.sizes()
    min_sizes = [300, 120, 150]  # Tab, Command, Log minimum heights
    
    # Check if any area needs adjustment
    if any(sizes[i] < min_sizes[i] for i in range(3)):
        # Temporarily disconnect to avoid recursion
        self.splitter.splitterMoved.disconnect(self.on_splitter_moved)
        
        # Apply minimum sizes
        adjusted_sizes = [max(sizes[i], min_sizes[i]) for i in range(3)]
        self.splitter.setSizes(adjusted_sizes)
        
        # Reconnect signal
        self.splitter.splitterMoved.connect(self.on_splitter_moved)
```

### 窗口显示时的强制配置

```python
def _on_show_event(self, event):
    """Handle window show event to force correct splitter behavior"""
    super().showEvent(event)
    
    # Force splitter to behave correctly by setting sizes explicitly
    # This ensures tab area stays fixed and only log area stretches
    QTimer.singleShot(50, self._force_splitter_config)

def _force_splitter_config(self):
    """Force splitter configuration after window is shown"""
    # Get current splitter sizes to capture the actual tab height
    current_sizes = self.splitter.sizes()
    current_tab_height = current_sizes[0]  # Capture current tab height
    
    # Store this as the "remembered" tab height
    self.remembered_tab_height = current_tab_height
    
    # Get current window height
    window_height = self.height()
    
    # Calculate desired sizes: use current tab height, command fixed, log gets the rest
    tab_height = current_tab_height  # Use current tab height as the "remembered" height
    command_height = 120  # Fixed command height
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
    QTimer.singleShot(10, self._reinforce_splitter_memory)

def _reinforce_splitter_memory(self):
    """Reinforce the splitter's memory of correct sizes"""
    # Get current sizes
    current_sizes = self.splitter.sizes()
    
    # If tab area is not at the remembered height, force it back
    if (hasattr(self, "remembered_tab_height") 
        and current_sizes[0] != self.remembered_tab_height):
        
        # Recalculate with remembered tab height
        window_height = self.height()
        tab_height = self.remembered_tab_height
        command_height = 120  # Fixed command height
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

## 联动机制详解

### 1. 窗口放大时的行为

```
初始状态: Tab(220px) + Command(120px) + Log(260px) = 600px
窗口放大到: 800px

调整顺序:
1. Log 区域优先扩展: 260px → 460px (增加200px)
2. Tab 区域保持不变: 220px
3. Command 面板固定: 120px

结果: Tab(220px) + Command(120px) + Log(460px) = 800px
```

### 2. 窗口缩小时的行为

```
初始状态: Tab(220px) + Command(120px) + Log(460px) = 800px
窗口缩小到: 600px

调整顺序:
1. Log 区域优先压缩: 460px → 260px (减少200px)
2. Tab 区域保持不变: 220px
3. Command 面板固定: 120px

结果: Tab(220px) + Command(120px) + Log(260px) = 600px
```

### 3. 达到最小值时的行为

```
当前状态: Tab(220px) + Command(120px) + Log(260px) = 600px
窗口缩小到: 500px (小于最小值 470px)

调整顺序:
1. Log 区域压缩到最小值: 260px → 150px (减少110px)
2. Tab 区域开始压缩: 220px → 200px (减少20px)
3. Command 面板保持固定: 120px

结果: Tab(200px) + Command(120px) + Log(150px) = 470px
```

### 4. 手动调整 Tab 区域时的行为

```
用户拖拽 Tab 区域分隔条:
- Tab 区域: 220px → 300px (增加80px)
- Command 面板: 120px (不变)
- Log 区域: 260px → 180px (减少80px)

如果 Log 区域 < 150px (最小值):
- 自动调整到 150px
- Tab 区域相应减少到 250px
```

## 用户体验优势

### 1. 智能调整
- **优先保护重要区域**：Log 区域优先调整，保证信息显示
- **保持操作区域稳定**：Command 面板始终固定，操作不受影响
- **灵活配置**：用户可以手动调整 Tab 区域大小

### 2. 响应式设计
- **窗口缩放友好**：无论窗口如何变化，界面都保持合理布局
- **最小尺寸保护**：防止界面元素过小影响使用
- **记忆用户偏好**：记住用户调整的 Tab 区域大小

### 3. 操作一致性
- **与 MdxScraper 一致**：用户在不同项目间切换时体验一致
- **符合直觉**：调整行为符合用户预期
- **稳定可靠**：经过 MdxScraper 验证的成熟方案

## 配置参数

```python
# Splitter 配置参数
SPLITTER_CONFIG = {
    "initial_sizes": [220, 120, 260],  # Tab, Command, Log 初始大小
    "min_sizes": [200, 120, 150],     # Tab, Command, Log 最小大小
    "stretch_factors": [0, 0, 1],      # Tab, Command, Log 拉伸因子
    "command_height": 120,            # Command 面板固定高度
    "margin_offset": 32,               # 边距偏移
}

# 窗口配置参数
WINDOW_CONFIG = {
    "min_width": 800,                  # 最小窗口宽度
    "min_height": 520,                 # 最小窗口高度
    "default_width": 1000,            # 默认窗口宽度
    "default_height": 700,             # 默认窗口高度
}
```

## 测试场景

### 1. 窗口缩放测试
- 窗口从最小尺寸逐步放大到最大尺寸
- 窗口从最大尺寸逐步缩小到最小尺寸
- 验证各区域大小变化是否符合预期

### 2. 手动调整测试
- 拖拽 Tab 区域分隔条调整大小
- 验证 Log 区域相应调整
- 验证最小尺寸限制是否生效

### 3. 边界条件测试
- 窗口尺寸接近最小尺寸时的行为
- 快速连续调整窗口大小时的行为
- 多显示器环境下的行为

## 总结

这个 Splitter 联动机制设计完全模仿了 MdxScraper 的成功经验，提供了：

1. **智能的自动调整**：优先调整 Log 区域，保护重要信息显示
2. **稳定的操作区域**：Command 面板固定，保证操作一致性
3. **灵活的用户控制**：支持手动调整 Tab 区域大小
4. **完善的边界保护**：最小尺寸限制，防止界面元素过小
5. **优秀的用户体验**：响应式设计，适应各种窗口尺寸

这是一个经过验证的成熟方案，直接应用到 MarkdownAll 中可以确保用户获得与 MdxScraper 一致的高质量体验。
