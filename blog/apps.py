from django.apps import AppConfig


# 博客应用配置类
# 这个类用于配置blog应用的元数据和行为
class BlogConfig(AppConfig):
    # 指定应用的Python路径
    # 这应该与settings.INSTALLED_APPS中使用的路径匹配
    name = 'blog'
    
    # 可以在这里添加其他配置选项，例如：
    # - verbose_name: 应用的人类可读名称
    # - default_auto_field: 默认主键字段类型
    # - ready()方法: 应用启动时执行的代码
    
    # 示例：
    # verbose_name = "博客系统"
    # 
    # def ready(self):
    #     # 应用启动时执行信号注册等初始化操作
    #     import blog.signals
