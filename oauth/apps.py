from django.apps import AppConfig


class OauthConfig(AppConfig):
    """
    OAuth应用的Django配置类
    
    这个类继承自Django的AppConfig基类，用于配置和管理
    oauth应用在Django项目中的行为。
    
    功能：
    - 定义应用名称和配置
    - 可选：应用启动时的初始化操作
    - 可选：配置应用的显示名称等元数据
    """
    
    # 应用的Python路径，必须与应用的目录名一致
    # Django使用这个名称来识别和引用该应用
    name = 'oauth'
    
    # 可选：在Django管理后台中显示的友好名称
    # verbose_name = 'OAuth认证'
    
    # 可选：定义默认的主键字段类型（Django 3.2+）
    # default_auto_field = 'django.db.models.BigAutoField'
    
    # 可选：应用启动时的初始化方法
    # def ready(self):
    #     # 在这里执行应用启动时需要初始化的操作
    #     # 例如：注册信号处理器、加载配置、初始化第三方SDK等
    #     import oauth.signals  # 导入信号处理器
