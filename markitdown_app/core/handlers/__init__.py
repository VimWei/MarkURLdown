"""
处理器模块 - 统一的处理器导入接口

这个模块提供了所有处理器的统一导入接口，包括：
- 特定站点处理器：微信、知乎、WordPress等
- 通用处理器：处理所有其他网站

使用方式：
    from markitdown_app.core.handlers import (
        GenericHandler,
        WeixinHandler, 
        ZhihuHandler,
        WordPressHandler
    )
"""

# 导入所有处理器
from .generic_handler import convert_url as generic_convert_url
from .weixin_handler import fetch_weixin_article
from .zhihu_handler import fetch_zhihu_article  
from .wordpress_handler import fetch_wordpress_article
from .nextjs_handler import fetch_nextjs_article
from .sspai_handler import fetch_sspai_article

# 提供统一的处理器接口
__all__ = [
    'generic_convert_url',
    'fetch_weixin_article',
    'fetch_zhihu_article', 
    'fetch_wordpress_article',
    'fetch_nextjs_article',
    'fetch_sspai_article',
]

# 处理器类型说明
HANDLER_TYPES = {
    'generic': '通用处理器 - 处理所有其他网站',
    'weixin': '微信处理器 - 专门处理微信公众号文章',
    'zhihu': '知乎处理器 - 专门处理知乎文章和回答',
    'wordpress': 'WordPress处理器 - 专门处理WordPress网站',
    'nextjs': 'Next.js处理器 - 专门处理Next.js博客网站',
    'sspai': '少数派处理器 - 专门处理少数派网站文章',
}
