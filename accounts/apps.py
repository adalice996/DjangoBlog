# 导入Django的应用配置基类
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """
    账户应用的配置类
    继承自Django的AppConfig，用于配置accounts应用的各种设置
    
    # 指定应用的Python路径（必需字段）
    # 这个名称必须与包含该应用的目录名一致
    name = 'accounts'
    
    # 通常情况下，还可以配置其他属性，例如：
    
    # verbose_name = _('Accounts')  
    # 用于在Django管理后台显示的应用名称（人类可读的名称）
    
    # default_auto_field = 'django.db.models.BigAutoField'
    # 指定默认的主键字段类型
    
    # def ready(self):
    #     # 应用启动时执行的初始化代码
    #     # 例如：注册信号处理器、加载配置等
    #     import accounts.signals
